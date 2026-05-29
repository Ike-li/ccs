#!/bin/sh

set -eu

repo=${CCS_INSTALL_REPO:-Ike-li/ccs}
ref=${CCS_INSTALL_REF:-main}
install_dir=${CCS_INSTALL_DIR:-"$HOME/.local/bin"}
raw_base=${CCS_INSTALL_RAW_BASE:-"https://raw.githubusercontent.com/$repo/$ref"}

need() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Error: %s is required\n' "$1" >&2
        exit 1
    }
}

need curl

mkdir -p "$install_dir"
tmp=$(mktemp "${TMPDIR:-/tmp}/ccs-install.XXXXXX") || exit 1
trap 'rm -f "$tmp"' HUP INT TERM EXIT

curl -fsSL "$raw_base/bin/ccs" -o "$tmp"

if command -v install >/dev/null 2>&1; then
    install -m 755 "$tmp" "$install_dir/ccs"
else
    cp "$tmp" "$install_dir/ccs"
    chmod 755 "$install_dir/ccs"
fi

printf 'installed: %s/ccs\n' "$install_dir"
case ":${PATH:-}:" in
    *":$install_dir:"*) ;;
    *) printf 'note: add %s to PATH before running ccs\n' "$install_dir" ;;
esac
