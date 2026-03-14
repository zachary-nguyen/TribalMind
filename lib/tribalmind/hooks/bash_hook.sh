#!/bin/bash
# TribalMind shell hook for Bash
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

_TRIBAL_DAEMON_HOST="127.0.0.1"
_TRIBAL_DAEMON_PORT="7483"

_tribalmind_preexec() {
    export _TRIBAL_CMD="$1"
}

_tribalmind_precmd() {
    local exit_code=$?
    if [ -n "$_TRIBAL_CMD" ]; then
        # Send event to daemon via TCP (fire-and-forget, non-blocking)
        {
            printf '{"type":"shell_event","payload":{"command":"%s","exit_code":%d,"cwd":"%s","timestamp":%d,"shell":"bash"}}\n' \
                "$(echo "$_TRIBAL_CMD" | sed 's/"/\\"/g' | head -c 500)" \
                "$exit_code" \
                "$(echo "$PWD" | sed 's/"/\\"/g')" \
                "$(date +%s)" \
                > /dev/tcp/$_TRIBAL_DAEMON_HOST/$_TRIBAL_DAEMON_PORT 2>/dev/null
        } &
        disown 2>/dev/null
        unset _TRIBAL_CMD
    fi
}

# Install hooks
trap '_tribalmind_preexec "$BASH_COMMAND"' DEBUG
PROMPT_COMMAND="_tribalmind_precmd${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
