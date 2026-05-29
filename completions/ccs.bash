# ccs bash completion
#
# Install (system-wide):
#   sudo cp completions/ccs.bash /etc/bash_completion.d/ccs
#
# Or load in ~/.bashrc:
#   . /path/to/ccs/completions/ccs.bash

_ccs() {
    local cur prev words cword
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion || return
    else
        cur=${COMP_WORDS[COMP_CWORD]}
        prev=${COMP_WORDS[COMP_CWORD-1]}
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    local commands="init set preset use verify doctor ls list current show rm remove help --help --version -h -v"
    local providers_dir="${CCS_DIR:-$HOME/.config/ccs}/providers"
    local -a providers=()
    if [ -d "$providers_dir" ]; then
        local f name
        for f in "$providers_dir"/*.conf; do
            [ -e "$f" ] || continue
            name=${f##*/}
            providers+=("${name%.conf}")
        done
    fi
    local providers_str="${providers[*]}"

    if [ "$cword" -le 1 ]; then
        # shellcheck disable=SC2207
        COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
        return
    fi

    local subcmd="${words[1]}"
    case "$subcmd" in
        use)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$providers_str" -- "$cur") )
            else
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "--no-verify --shell" -- "$cur") )
            fi
            ;;
        verify|rm|remove)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$providers_str" -- "$cur") )
            fi
            ;;
        show)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$providers_str" -- "$cur") )
            else
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "--show-key" -- "$cur") )
            fi
            ;;
        set)
            local managed_envs="ANTHROPIC_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL"
            case "$prev" in
                --base-url|--key|--model|--opus-model|--sonnet-model|--haiku-model|-e|--env)
                    ;;
                --unset-env)
                    # shellcheck disable=SC2207
                    COMPREPLY=( $(compgen -W "$managed_envs" -- "$cur") )
                    ;;
                *)
                    # shellcheck disable=SC2207
                    COMPREPLY=( $(compgen -W "--base-url --key --use-api-key --use-auth-token --model --opus-model --sonnet-model --haiku-model --unset-model -e --env --unset-env --help $providers_str" -- "$cur") )
                    ;;
            esac
            ;;
        preset)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "deepseek openrouter" -- "$cur") )
            else
                case "$prev" in
                    --key|--name) ;;
                    *)
                        # shellcheck disable=SC2207
                        COMPREPLY=( $(compgen -W "--key --name --help" -- "$cur") )
                        ;;
                esac
            fi
            ;;
    esac
}

complete -F _ccs ccs
