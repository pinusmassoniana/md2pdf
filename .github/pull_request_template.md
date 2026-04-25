<!--
  Thanks for opening a PR. Please fill in the sections below — it speeds up review.
  If a section doesn't apply, write "n/a" rather than deleting it.
-->

## Summary

<!-- One or two sentences: what does this PR change, and why? -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (a fix or feature that changes existing behavior in an incompatible way)
- [ ] Documentation only
- [ ] Build / tooling / CI

## Linked issues

<!-- "Closes #123", "Fixes #456", "Refs #789". If there's no issue, briefly justify why this needs to land directly. -->

## What changed

<!-- Bullet list of the actual edits, file by file or area by area. -->

-
-

## How to verify

<!-- Exact commands a reviewer can run to confirm the change works. -->

```bash
python3 md2pdf.py examples/<file>.md --font-dir fonts -o /tmp/check.pdf
```

## Tested examples

- [ ] `examples/quickstart.md`
- [ ] `examples/features-showcase.md`
- [ ] `examples/charts.md`
- [ ] `examples/merge-chapter-1.md` + `merge-chapter-2.md` (with `--merge`)
- [ ] `examples/sample-document.md` (`doc2md.py examples/sample.docx`)
- [ ] `examples/sample-presentation.md` (`doc2md.py examples/sample.pptx`)
- [ ] N/A — explain why:

## Documentation

- [ ] Updated `md2pdf_format.md` for any new syntax / flag.
- [ ] Updated `README.md` if user-facing behavior changed.
- [ ] Updated or added an example in `examples/` for any new Markdown construct.
- [ ] N/A — pure refactor / internal change.

## macOS app changes (delete if not applicable)

- [ ] Edited `.swift` source.
- [ ] Ran `./build.sh` and committed the rebuilt binaries.
- [ ] Wired the new option into the AppleScript fallback (`settings_dialog.applescript`).
- [ ] Wired the new option into the bash launcher.

## Pre-flight checklist

- [ ] No personal data, no Cyrillic in code, no absolute paths to my home directory.
- [ ] Commit messages are in the imperative mood ("Add X", "Fix Y").
- [ ] One logical change per PR (no unrelated refactoring).
- [ ] I followed [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- [ ] I agree to license my contribution under the MIT License.
