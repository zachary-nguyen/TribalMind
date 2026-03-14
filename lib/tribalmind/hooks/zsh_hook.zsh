#!/bin/zsh
# TribalMind shell hook for Zsh
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

_TRIBAL_DAEMON_HOST="127.0.0.1"
_TRIBAL_DAEMON_PORT="7483"

_tribalmind_preexec() {
    export _TRIBAL_CMD="$1"
}

_tribalmind_precmd() {
    local exit_code=$?
    if [[ -n "$_TRIBAL_CMD" ]]; then
        # Send event to daemon via TCP (fire-and-forget, non-blocking)
        {
            printf '{"type":"shell_event","payload":{"command":"%s","exit_code":%d,"cwd":"%s","timestamp":%d,"shell":"zsh"}}\n' \
                "${_TRIBAL_CMD//\"/\\\"}" \
                "$exit_code" \
                "${PWD//\"/\\\"}" \
                "$(date +%s)" \
                | nc -w 1 "$_TRIBAL_DAEMON_HOST" "$_TRIBAL_DAEMON_PORT" 2>/dev/null
        } &!
        unset _TRIBAL_CMD
    fi
}

# Install hooks using zsh native hook arrays
autoload -Uz add-zsh-hook
add-zsh-hook preexec _tribalmind_preexec
add-zsh-hook precmd _tribalmind_precmd
