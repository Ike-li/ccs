#!/bin/sh

set -eu

repo=${CCS_INSTALL_REPO:-Ike-li/ccs}
ref=${CCS_INSTALL_REF:-v0.7.0}
expected_sha256=${CCS_INSTALL_SHA256:-1cde59f528709bada3428c1e07f21cf84fc14f5d2b237d5290a5b051d0334cdb}
install_dir=${CCS_INSTALL_DIR:-"$HOME/.local/bin"}
raw_base=${CCS_INSTALL_RAW_BASE:-"https://raw.githubusercontent.com/$repo/$ref"}

need() {
    command -v "$1" >/dev/null 2>&1 || {
        printf 'Error: %s is required\n' "$1" >&2
        exit 1
    }
}

need curl

# Trust boundary: this installer resolves curl, the hashing tool, and install/cp
# through $PATH, so it can only be as trustworthy as $PATH itself. A poisoned
# PATH defeats any POSIX-sh installer (even printf/test could be shadowed). Run
# it with a trusted PATH, or prefer `brew install Ike-li/tap/ccs`. The checksum
# step below is mandatory: if no hashing tool is found it aborts rather than
# installing unverified bytes.
sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif command -v openssl >/dev/null 2>&1; then
        openssl dgst -sha256 "$1" | awk '{print $NF}'
    else
        printf 'Error: sha256sum, shasum, or openssl is required for checksum verification\n' >&2
        exit 1
    fi
}

mkdir -p "$install_dir"
tmp=$(mktemp "${TMPDIR:-/tmp}/ccs-install.XXXXXX") || exit 1
trap 'rm -f "$tmp"' HUP INT TERM EXIT

# A set-but-empty CCS_INSTALL_SHA256 still falls back to the pinned default via
# :- above, so the checksum can never be silently blanked. Guard only the
# computed side: a hasher that returns nothing must abort, not compare ""=="".
curl -fsSL "$raw_base/bin/ccs" -o "$tmp"
actual_sha256=$(sha256_file "$tmp")
if [ -z "$actual_sha256" ]; then
    printf 'Error: could not compute checksum of downloaded bin/ccs\n' >&2
    exit 1
fi
if [ "$actual_sha256" != "$expected_sha256" ]; then
    printf 'Error: checksum mismatch for %s/bin/ccs\n' "$raw_base" >&2
    printf 'Expected: %s\n' "$expected_sha256" >&2
    printf 'Actual:   %s\n' "$actual_sha256" >&2
    exit 1
fi

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
