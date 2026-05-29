## Summary

<!-- What changed, and why? -->

## Scope

- [ ] CLI behavior
- [ ] Provider recipe
- [ ] Documentation
- [ ] Install/release
- [ ] Tests only

## Verification

<!-- Paste the commands you ran. Use "Not run" with a reason if something does not apply. -->

```text
sh -n bin/ccs install.sh
shellcheck -s sh bin/ccs install.sh
uv run --no-project --with pytest pytest tests/test_cli.py
```

## Checklist

- [ ] I did not include real provider keys, tokens, or private settings.
- [ ] I updated README/docs for user-visible behavior changes.
- [ ] I added or updated tests for CLI behavior changes.
- [ ] I kept `ccs` inside its boundary: provider switching, not protocol translation or proxying.
- [ ] I checked POSIX `sh` compatibility for shell changes.
