# TribalMind shell hook for PowerShell
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

$Global:_TribalDaemonHost = "127.0.0.1"
$Global:_TribalDaemonPort = 7483
$Global:_TribalLastHistoryId = 0

function _TribalMind_SendEvent {
    param(
        [string]$Command,
        [int]$ExitCode,
        [string]$Cwd
    )

    # Synchronous fire-and-forget — localhost TCP is sub-millisecond
    try {
        $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $escapedCmd = $Command -replace '\\', '\\' -replace '"', '\"'
        $escapedDir = $Cwd -replace '\\', '\\' -replace '"', '\"'
        $json = "{""type"":""shell_event"",""payload"":{""command"":""$escapedCmd"",""exit_code"":$ExitCode,""cwd"":""$escapedDir"",""timestamp"":$timestamp,""shell"":""powershell""}}`n"

        $client = [System.Net.Sockets.TcpClient]::new()
        $client.Connect($Global:_TribalDaemonHost, $Global:_TribalDaemonPort)
        $stream = $client.GetStream()
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush()
        $client.Close()
    } catch {
        # Silently ignore — daemon may not be running
    }
}

# Override prompt to capture post-execution state.
# Uses Get-History instead of PSReadLine key handlers — works in all terminals
# including VS Code integrated terminal.
$Global:_TribalOriginalPrompt = $function:prompt

function prompt {
    $lastExitCode = $LASTEXITCODE
    $lastSuccess = $?

    # Check if a new command was executed since last prompt
    $lastHist = Get-History -Count 1 -ErrorAction SilentlyContinue
    if ($lastHist -and $lastHist.Id -ne $Global:_TribalLastHistoryId) {
        $Global:_TribalLastHistoryId = $lastHist.Id
        $exitCode = if ($lastSuccess) { 0 } else { if ($lastExitCode) { $lastExitCode } else { 1 } }
        _TribalMind_SendEvent -Command $lastHist.CommandLine -ExitCode $exitCode -Cwd $PWD.Path
    }

    # Restore LASTEXITCODE so we don't interfere with user's scripts
    $Global:LASTEXITCODE = $lastExitCode

    # Call original prompt
    & $Global:_TribalOriginalPrompt
}

# Initialize history ID so we don't re-send old commands on shell startup
$_initHist = Get-History -Count 1 -ErrorAction SilentlyContinue
if ($_initHist) { $Global:_TribalLastHistoryId = $_initHist.Id }
Remove-Variable _initHist -ErrorAction SilentlyContinue
