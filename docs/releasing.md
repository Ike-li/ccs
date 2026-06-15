# Releasing

This project is a single POSIX shell script plus completions and docs. Releases should make the install path boring: tag, GitHub Release assets, checksum, then Homebrew tap update.

## Version checklist

1. Update `CCS_VERSION` in `bin/ccs`.
2. Update README examples and the `install.sh` default `ref` / `expected_sha256` for the new tag.
3. Run:

```bash
sh -n bin/ccs install.sh
shellcheck -s sh bin/ccs install.sh
uv run --no-project --with pytest pytest tests/test_cli.py
ruff check tests
ruff format --check tests
test "$(./bin/ccs --version)" = "ccs 0.8.0"
```

4. Confirm tracked docs do not contain unsafe permission-bypass examples:

```bash
unsafe='--danger'"ously-skip-permissions"
! git grep -n -- "$unsafe" README.md docs CONTRIBUTING.md SECURITY.md CHANGELOG.md
```

5. Create and push a signed or annotated tag:

```bash
git tag -a v0.8.0 -m "ccs v0.8.0"
git push origin main v0.8.0
```

The release workflow validates the tag against `CCS_VERSION`, checks that the `install.sh` pinned `ref`/`expected_sha256` defaults match the tag's `bin/ccs`, reruns syntax checks (including both completion scripts), ShellCheck, pytest, and tracked-doc safety validation before it creates the archive from git-tracked project files:

- `ccs-vX.Y.Z.tar.gz`
- `ccs-vX.Y.Z.sha256`
- `bin-ccs-vX.Y.Z.sha256`
- GitHub release notes generated from commits

## Install script

The README one-liner downloads `install.sh` from `main`, but the script itself installs a pinned release tag and verifies the downloaded `bin/ccs` sha256:

```bash
curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh | sh
```

Users can override the ref only when they also provide the matching checksum:

```bash
CCS_INSTALL_REF=v0.8.0 \
CCS_INSTALL_SHA256=<sha256 from bin-ccs-v0.8.0.sha256> \
sh -c "$(curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh)"
```

## Homebrew tap

After a release exists, update `Ike-li/homebrew-tap` with the release tarball URL and sha256.

Example formula:

```ruby
class Ccs < Formula
  desc "Tiny Claude Code provider switcher"
  homepage "https://github.com/Ike-li/ccs"
  url "https://github.com/Ike-li/ccs/releases/download/v0.8.0/ccs-v0.8.0.tar.gz"
  sha256 "<sha256 from ccs-v0.8.0.sha256>"
  license "GPL-3.0-only"

  def install
    bin.install "ccs"
    bash_completion.install "completions/ccs.bash" => "ccs"
    zsh_completion.install "completions/_ccs"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/ccs --version")
  end
end
```

Recommended tap flow:

```bash
git clone https://github.com/Ike-li/homebrew-tap.git
cd homebrew-tap
"${EDITOR:-vi}" Formula/ccs.rb
brew audit --strict --online Ike-li/tap/ccs
brew test Ike-li/tap/ccs
```

User install command:

```bash
brew install Ike-li/tap/ccs
```
