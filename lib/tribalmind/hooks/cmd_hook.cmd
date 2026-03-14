@echo off
:: TribalMind CMD hook - sets up command monitoring via DOSKEY macros.
:: Loaded automatically via the AutoRun registry key.
:: Installed by: tribal install

set "_TRIBAL_HOOK_DIR=%~dp0"

:: Generic wrapper - use "tm <command>" to monitor any command
doskey tm=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" $*

:: Auto-wrap common error-producing commands
doskey python=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" python $*
doskey python3=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" python3 $*
doskey pip=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" pip $*
doskey pip3=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" pip3 $*
doskey node=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" node $*
doskey npm=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" npm $*
doskey npx=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" npx $*
doskey cargo=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" cargo $*
doskey go=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" go $*
doskey dotnet=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" dotnet $*
doskey javac=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" javac $*
doskey gcc=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" gcc $*
doskey make=call "%_TRIBAL_HOOK_DIR%cmd_wrapper.cmd" make $*
