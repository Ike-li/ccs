# Releasing

This project is a single POSIX shell script plus completions and docs. Releases should make the install path boring: tag, GitHub Release assets, checksum, then Homebrew tap update.

## Version checklist

1. Update `CCS_VERSION` in `bin/ccs`.
2. Update README examples that mention the new tag.
3. Run:

```bash
sh -n bin/ccs install.sh
uv run --no-project --with pytest pytest tests/test_cli.py
```

4. Create and push a signed or annotated tag:

```bash
git tag -a v0.6.0 -m "ccs v0.6.0"
git push origin main v0.6.0
```

The release workflow creates:

- `ccs-vX.Y.Z.tar.gz`
- `ccs-vX.Y.Z.sha256`
- GitHub release notes generated from commits

## Install script

The README one-liner installs from `main` by default:

```bash
curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh | sh
```

Users can pin a tag:

```bash
CCS_INSTALL_REF=v0.6.0 sh -c "$(curl -fsSL https://raw.githubusercontent.com/Ike-li/ccs/main/install.sh)"
```

## Homebrew tap

After a release exists, update `Ike-li/homebrew-tap` with the release tarball URL and sha256.

Example formula:

```ruby
class Ccs < Formula
  desc "Tiny Claude Code provider switcher"
  homepage "https://github.com/Ike-li/ccs"
  url "https://github.com/Ike-li/ccs/releases/download/v0.6.0/ccs-v0.6.0.tar.gz"
  sha256 "<sha256 from ccs-v0.6.0.sha256>"
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
