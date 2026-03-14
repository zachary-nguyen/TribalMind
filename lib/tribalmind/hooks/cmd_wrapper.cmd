@echo off
:: TribalMind CMD wrapper - runs a command and sends the result to the daemon.
:: Called by DOSKEY macros defined in cmd_hook.cmd.
:: Usage: cmd_wrapper.cmd <command> [args...]

:: Run the actual command
%*
set "_TM_EC=%ERRORLEVEL%"

:: Send event to daemon (Python handles spinner + insight display)
python -m tribalmind.hooks.cmd_send "%*" %_TM_EC% "%CD%" 2>nul

:: Return the original exit code
exit /b %_TM_EC%
