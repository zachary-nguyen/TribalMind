# TribalMind shell hook for PowerShell
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

$Global:_TribalDaemonHost = "127.0.0.1"
$Global:_TribalDaemonPort = 7483
$Global:_TribalLastCmd = $null

function _TribalMind_SendEvent {
    param(
        [string]$Command,
        [int]$ExitCode,
        [string]$Cwd
    )

    # Fire-and-forget via background job to avoid blocking the prompt
    Start-Job -ScriptBlock {
        param($Host_, $Port, $Cmd, $Exit, $Dir)
        try {
            $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            $escapedCmd = $Cmd -replace '"', '\"'
            $escapedDir = $Dir -replace '"', '\"'
            $json = "{""type"":""shell_event"",""payload"":{""command"":""$escapedCmd"",""exit_code"":$Exit,""cwd"":""$escapedDir"",""timestamp"":$timestamp,""shell"":""powershell""}}`n"

            $client = [System.Net.Sockets.TcpClient]::new()
            $client.Connect($Host_, $Port)
            $stream = $client.GetStream()
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
            $stream.Write($bytes, 0, $bytes.Length)
            $stream.Flush()
            $client.Close()
        } catch {
            # Silently ignore connection errors
        }
    } -ArgumentList $Global:_TribalDaemonHost, $Global:_TribalDaemonPort, $Command, $ExitCode, $Cwd | Out-Null

    # Clean up completed background jobs periodically
    Get-Job -State Completed | Remove-Job -Force -ErrorAction SilentlyContinue
}

# Override prompt to capture post-execution state
$Global:_TribalOriginalPrompt = $function:prompt

function prompt {
    $lastExitCode = $LASTEXITCODE
    $lastSuccess = $?

    if ($Global:_TribalLastCmd) {
        $exitCode = if ($lastSuccess) { 0 } else { if ($lastExitCode) { $lastExitCode } else { 1 } }
        _TribalMind_SendEvent -Command $Global:_TribalLastCmd -ExitCode $exitCode -Cwd $PWD.Path
        $Global:_TribalLastCmd = $null
    }

    # Restore LASTEXITCODE so we don't interfere with user's scripts
    $Global:LASTEXITCODE = $lastExitCode

    # Call original prompt
    & $Global:_TribalOriginalPrompt
}

# Capture command before execution via PSReadLine
if (Get-Module PSReadLine) {
    Set-PSReadLineKeyHandler -Key Enter -ScriptBlock {
        $line = $null
        $cursor = $null
        [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState([ref]$line, [ref]$cursor)
        if ($line.Trim()) {
            $Global:_TribalLastCmd = $line.Trim()
        }
        [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
    }
}
