# TribalMind shell hook for PowerShell
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

$Global:_TribalDaemonHost = "127.0.0.1"
$Global:_TribalDaemonPort = 7483
$Global:_TribalLastHistoryId = 0
$Global:_TribalIgnoreCommands = @("cd", "ls", "pwd", "clear", "clear-host", "cls", "echo", "cat", "less", "more", "dir", "type", "set-location", "push-location", "pop-location", "get-location", "get-childitem", "write-host", "write-output", "history", "get-history")

function _TribalMind_SendEvent {
    param(
        [string]$Command,
        [int]$ExitCode,
        [string]$Cwd,
        [string]$Stderr
    )

    try {
        $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        # Escape for JSON
        $escapedCmd = $Command -replace '\\', '\\\\' -replace '"', '\"' -replace "`n", '\n' -replace "`r", ''
        $escapedDir = $Cwd -replace '\\', '\\\\' -replace '"', '\"'
        $escapedStderr = $Stderr -replace '\\', '\\\\' -replace '"', '\"' -replace "`n", '\n' -replace "`r", ''
        $json = "{""type"":""shell_event"",""payload"":{""command"":""$escapedCmd"",""exit_code"":$ExitCode,""cwd"":""$escapedDir"",""timestamp"":$timestamp,""stderr"":""$escapedStderr"",""shell"":""powershell""}}`n"

        $client = [System.Net.Sockets.TcpClient]::new()
        $client.Connect($Global:_TribalDaemonHost, $Global:_TribalDaemonPort)
        $stream = $client.GetStream()
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush()

        # For failed commands, show spinner and wait for insight response
        if ($ExitCode -ne 0) {
            $stream.ReadTimeout = 15000
            try {
                # Braille spinner animation (compatible with PS 5.1+)
                $frames = @(
                    [char]::ConvertFromUtf32(0x28F7),
                    [char]::ConvertFromUtf32(0x28EF),
                    [char]::ConvertFromUtf32(0x28DF),
                    [char]::ConvertFromUtf32(0x287F),
                    [char]::ConvertFromUtf32(0x28BF),
                    [char]::ConvertFromUtf32(0x28FB),
                    [char]::ConvertFromUtf32(0x28FD),
                    [char]::ConvertFromUtf32(0x28FE)
                )
                $spinIdx = 0
                [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
                Write-Host ""
                Write-Host -NoNewline "  $($frames[0]) TribalMind analyzing..." -ForegroundColor DarkCyan

                while (-not $stream.DataAvailable) {
                    Start-Sleep -Milliseconds 80
                    $spinIdx = ($spinIdx + 1) % $frames.Count
                    Write-Host -NoNewline "`r  $($frames[$spinIdx]) TribalMind analyzing..." -ForegroundColor DarkCyan
                }

                # Clear the spinner line
                Write-Host -NoNewline "`r$(' ' * 40)`r"

                $reader = New-Object System.IO.StreamReader($stream, [System.Text.Encoding]::UTF8)
                $line = $reader.ReadLine()
                if ($line) {
                    $parsed = $line | ConvertFrom-Json -ErrorAction SilentlyContinue
                    if ($parsed -and $parsed.type -eq "insight_response" -and $parsed.payload.text) {
                        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
                        Write-Host $parsed.payload.text
                    }
                }
            } catch {
                # Timeout or read error — clear spinner and move on
                Write-Host -NoNewline "`r$(' ' * 40)`r"
            }
        }

        $client.Close()
    } catch {
        # Silently ignore — daemon may not be running
    }
}

# Capture stderr for failed native commands by re-running them.
# This avoids mutating the command line (which breaks interactive prompts,
# pollutes history, and is visible to the user).
function _TribalMind_CaptureStderr {
    param([string]$Command)

    $tmpFile = Join-Path ([System.IO.Path]::GetTempPath()) "tribalmind_stderr_$PID.tmp"
    try {
        # Use cmd.exe to replay the command with stderr redirected.
        # This is best-effort — some commands have side effects on re-run.
        # Only capture the first line of stderr as a signature.
        $firstWord = ($Command.Trim() -split '\s+')[0].ToLower()

        # Only re-run for known-safe error producers (compilers, interpreters, package managers)
        $safeToRerun = @('python', 'python3', 'node', 'npm', 'npx', 'cargo', 'rustc', 'go', 'pip', 'pip3', 'dotnet', 'javac', 'gcc', 'g++', 'make', 'cmake')
        if ($safeToRerun -notcontains $firstWord) {
            return ""
        }

        # Re-run with --help-style flags that reproduce errors without side effects
        # Actually, just run the same command — most error-producing commands are idempotent
        # (import errors, compile errors, etc.) and the daemon already saw it succeed/fail.
        # Skip re-run for now — return empty. The error type/package is usually parseable
        # from the exit code + command alone.
        return ""
    } finally {
        if (Test-Path $tmpFile -ErrorAction SilentlyContinue) {
            Remove-Item $tmpFile -Force -ErrorAction SilentlyContinue
        }
    }
}

$Global:_TribalOriginalPrompt = $function:prompt

function prompt {
    # Capture exit state IMMEDIATELY — before anything else can reset it
    $nativeExit = $LASTEXITCODE
    $cmdSuccess = $?

    # Check if a new command was executed since last prompt
    $lastHist = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($lastHist -and $lastHist.Id -ne $Global:_TribalLastHistoryId) {
        $Global:_TribalLastHistoryId = $lastHist.Id

        # Determine exit code
        $exitCode = 0
        if ($null -ne $nativeExit -and $nativeExit -ne 0) {
            $exitCode = $nativeExit
        } elseif (-not $cmdSuccess) {
            $exitCode = 1
        }

        # Skip Ctrl+C / interrupt signals — not real errors
        # Windows: -1073741510 (0xC000013A STATUS_CONTROL_C_EXIT), Unix: 130 (128+SIGINT)
        if ($exitCode -eq -1073741510 -or $exitCode -eq 130 -or $exitCode -eq 137 -or $exitCode -eq 143) {
            & $Global:_TribalOriginalPrompt
            return
        }

        $cmd = $lastHist.CommandLine

        # Client-side ignore filter — skip trivial commands before contacting daemon
        $firstWord = ($cmd.Trim() -split '\s+')[0].ToLower()
        # Strip common path prefixes and extensions (e.g. C:\...\python.exe -> python)
        $firstWord = [System.IO.Path]::GetFileNameWithoutExtension($firstWord)
        if ($Global:_TribalIgnoreCommands -contains $firstWord) {
            # Still call original prompt
            & $Global:_TribalOriginalPrompt
            return
        }

        $stderr = ""

        # For failed commands, try to get stderr from PowerShell's error stream
        if ($exitCode -ne 0) {
            # $Error[0] often contains the last error record
            if ($Error.Count -gt 0 -and $Error[0]) {
                $lastErr = $Error[0]
                if ($lastErr -is [System.Management.Automation.ErrorRecord]) {
                    $stderr = $lastErr.Exception.Message
                } else {
                    $stderr = "$lastErr"
                }
            }
        }

        _TribalMind_SendEvent -Command $cmd -ExitCode $exitCode -Cwd $PWD.Path -Stderr $stderr
    }

    # Restore LASTEXITCODE so we don't interfere with user's scripts
    $Global:LASTEXITCODE = $nativeExit

    # Call original prompt
    & $Global:_TribalOriginalPrompt
}

# Initialize history ID so we don't re-send old commands on shell startup
$_initHist = Get-History -Count 1 -ErrorAction SilentlyContinue
if ($_initHist) { $Global:_TribalLastHistoryId = $_initHist.Id }
Remove-Variable _initHist -ErrorAction SilentlyContinue
