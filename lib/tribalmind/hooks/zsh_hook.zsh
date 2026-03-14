#!/bin/zsh
# TribalMind shell hook for Zsh
# Captures command execution and sends events to the TribalMind daemon.
# Installed by: tribal install

_TRIBAL_DAEMON_HOST="127.0.0.1"
_TRIBAL_DAEMON_PORT="7483"
_TRIBAL_IGNORE_CMDS=(cd ls pwd clear cls echo cat less more dir type pushd popd)

_tribalmind_preexec() {
    export _TRIBAL_CMD="$1"
}

_tribalmind_precmd() {
    local exit_code=$?
    if [[ -n "$_TRIBAL_CMD" ]]; then
        # Client-side ignore filter
        local base_cmd="${_TRIBAL_CMD%% *}"
        base_cmd="${base_cmd:t}"  # strip path prefix (zsh modifier)
        if (( ${_TRIBAL_IGNORE_CMDS[(Ie)$base_cmd]} )); then
            unset _TRIBAL_CMD
            return
        fi

        # Skip Ctrl+C / signal exits (130=SIGINT, 137=SIGKILL, 143=SIGTERM)
        if (( exit_code == 130 || exit_code == 137 || exit_code == 143 )); then
            unset _TRIBAL_CMD
            return
        fi

        local json
        json=$(printf '{"type":"shell_event","payload":{"command":"%s","exit_code":%d,"cwd":"%s","timestamp":%d,"shell":"zsh"}}\n' \
            "${_TRIBAL_CMD//\"/\\\"}" \
            "$exit_code" \
            "${PWD//\"/\\\"}" \
            "$(date +%s)")

        if [[ "$exit_code" -ne 0 ]]; then
            # Failed command: show spinner and wait for insight response
            local tmpfile="/tmp/.tribalmind_insight_$$"
            echo "$json" | nc -w 15 "$_TRIBAL_DAEMON_HOST" "$_TRIBAL_DAEMON_PORT" > "$tmpfile" 2>/dev/null &
            local nc_pid=$!

            local -a frames=($'\xe2\xa3\xb7' $'\xe2\xa3\xaf' $'\xe2\xa3\x9f' $'\xe2\xa1\xbf' $'\xe2\xa2\xbf' $'\xe2\xa3\xbb' $'\xe2\xa3\xbd' $'\xe2\xa3\xbe')
            local i=1
            printf '\n  \033[36m%s TribalMind analyzing...\033[0m' "${frames[1]}"
            while kill -0 "$nc_pid" 2>/dev/null; do
                i=$(( (i % 8) + 1 ))
                printf '\r  \033[36m%s TribalMind analyzing...\033[0m' "${frames[$i]}"
                sleep 0.08
            done
            printf '\r%40s\r' ""

            wait "$nc_pid" 2>/dev/null
            if [[ -s "$tmpfile" ]]; then
                local text
                text=$(python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('payload',{}).get('text',''); print(t)" < "$tmpfile" 2>/dev/null)
                if [[ -n "$text" ]]; then
                    echo "$text"
                fi
            fi
            rm -f "$tmpfile"
        else
            # Successful command: fire-and-forget
            {
                echo "$json" | nc -w 1 "$_TRIBAL_DAEMON_HOST" "$_TRIBAL_DAEMON_PORT" 2>/dev/null
            } &!
        fi
        unset _TRIBAL_CMD
    fi
}

# Install hooks using zsh native hook arrays
autoload -Uz add-zsh-hook
add-zsh-hook preexec _tribalmind_preexec
add-zsh-hook precmd _tribalmind_precmd
