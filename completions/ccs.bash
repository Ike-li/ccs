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

    local commands="init set preset use pin unpin slim verify doctor ls list current show rm remove help version --help --version -h -v"
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
    # `official` is the built-in claude.ai subscription pseudo provider: valid
    # for use/show, never for set/verify/rm.
    local use_targets_str="official ${providers[*]}"

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
                COMPREPLY=( $(compgen -W "$use_targets_str --global" -- "$cur") )
            else
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "--no-verify --shell --project --global" -- "$cur") )
            fi
            ;;
        pin)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$use_targets_str" -- "$cur") )
            else
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "--no-verify --shell" -- "$cur") )
            fi
            ;;
        unpin)
            # shellcheck disable=SC2207
            COMPREPLY=( $(compgen -W "--shell" -- "$cur") )
            ;;
        verify|rm|remove)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$providers_str" -- "$cur") )
            fi
            ;;
        slim)
            # shellcheck disable=SC2207
            COMPREPLY=( $(compgen -W "--apply" -- "$cur") )
            ;;
        show)
            if [ "$cword" -eq 2 ]; then
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "$use_targets_str" -- "$cur") )
            else
                # shellcheck disable=SC2207
                COMPREPLY=( $(compgen -W "--show-key" -- "$cur") )
            fi
            ;;
        set)
            # Keep in sync with PROVIDER_ENV_KEYS in bin/ccs.
            local managed_envs="ANTHROPIC_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL_NAME ANTHROPIC_DEFAULT_OPUS_MODEL_DESCRIPTION ANTHROPIC_DEFAULT_OPUS_MODEL_SUPPORTED_CAPABILITIES ANTHROPIC_DEFAULT_SONNET_MODEL_NAME ANTHROPIC_DEFAULT_SONNET_MODEL_DESCRIPTION ANTHROPIC_DEFAULT_SONNET_MODEL_SUPPORTED_CAPABILITIES ANTHROPIC_DEFAULT_HAIKU_MODEL_NAME ANTHROPIC_DEFAULT_HAIKU_MODEL_DESCRIPTION ANTHROPIC_DEFAULT_HAIKU_MODEL_SUPPORTED_CAPABILITIES ANTHROPIC_CUSTOM_MODEL_OPTION ANTHROPIC_CUSTOM_MODEL_OPTION_NAME ANTHROPIC_CUSTOM_MODEL_OPTION_DESCRIPTION ANTHROPIC_CUSTOM_MODEL_OPTION_SUPPORTED_CAPABILITIES CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_EFFORT_LEVEL"
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
                COMPREPLY=( $(compgen -W "deepseek openrouter kimi hf gateway litellm" -- "$cur") )
            else
                case "$prev" in
                    --key|--name|--base-url) ;;
                    *)
                        # shellcheck disable=SC2207
                        COMPREPLY=( $(compgen -W "--key --name --base-url --help" -- "$cur") )
                        ;;
                esac
            fi
            ;;
    esac
}

complete -F _ccs ccs
