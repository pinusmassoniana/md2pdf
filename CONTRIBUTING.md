# Contributing to md2pdf

Thanks for your interest in improving md2pdf, doc2md, or md2pdf-validator. This document explains how to get a working development environment, how to test your changes, and what conventions the project follows.

---

## Quick links

- **Issues** — bug reports and feature requests: <https://github.com/pinusmassoniana/md2pdf/issues>
- **Discussions** — questions and ideas: open an issue with the "question" label until Discussions is enabled
- **Format reference** — [`md2pdf_format.md`](md2pdf_format.md)
- **Examples** — [`examples/`](examples/)

---

## Development setup

### Prerequisites

- **Python 3.9+**
- **`reportlab>=4.0`** — required
- **`matplotlib>=3.5`** — required if you change anything related to charts
- **`qrcode[pil]`, `python-docx`, `python-pptx`, `PyMuPDF`** — install if you touch the corresponding code paths
- **macOS only**: Xcode Command Line Tools (`xcode-select --install`) for `swiftc`, if you change the native settings dialogs

### Setup

```bash
git clone https://github.com/pinusmassoniana/md2pdf.git
cd md2pdf
pip install -r requirements.txt
```

The DejaVu fonts are bundled in `fonts/` so you can run the converter immediately.

### Smoke test your environment

```bash
python3 md2pdf.py examples/quickstart.md --font-dir fonts -o /tmp/check.pdf
file /tmp/check.pdf   # should print: PDF document, version 1.4, ... pages
```

If that works, you're ready.

---

## Making a change

### Branching

- Fork the repository.
- Create a branch from `main` named after the change: `fix/cover-overflow`, `feat/landscape-tables`, `docs/cli-table`, etc.
- Keep one logical change per PR. Smaller PRs are easier to review and faster to merge.

### Coding conventions

- **Python**: follow PEP 8 with reasonable line length. The codebase uses no formatter at the moment, but please keep style consistent with the surrounding code.
- **No new dependencies** unless they're optional and gated behind an `import` check (like `matplotlib` is for `chart` blocks). Heavy mandatory deps will be rejected.
- **English everywhere** — comments, docstrings, error messages, identifiers, commit messages. The repository was translated to English on purpose.
- **Stay focused** — don't sneak in unrelated refactoring. If you spot something while making your change, file a separate issue or PR.

### When you add a new Markdown feature

You must do all three:

1. **Implement** it in `md2pdf.py` (and in `doc2md.py` if it should round-trip).
2. **Document** the syntax in [`md2pdf_format.md`](md2pdf_format.md).
3. **Demo** it in [`examples/`](examples/) — either extend `features-showcase.md` or add a focused new example. The example must produce a valid PDF.

### Testing

There is no formal unit-test suite yet. The project relies on **example-based regression testing**:

- Run every example in `examples/` and confirm each one renders to a non-empty PDF without warnings:

  ```bash
  for f in examples/*.md; do
      python3 md2pdf.py "$f" --font-dir fonts -o "/tmp/$(basename "$f" .md).pdf" || echo "FAILED: $f"
  done
  ```

- For changes to merge mode, verify with `examples/merge-chapter-1.md` + `examples/merge-chapter-2.md`.
- For doc2md changes, run a round-trip:

  ```bash
  python3 doc2md.py examples/sample.docx -o /tmp/rt.md
  python3 md2pdf.py /tmp/rt.md --font-dir fonts -o /tmp/rt.pdf
  ```

If you're comfortable adding `pytest` tests for parsing logic in a new `tests/` directory, even better.

### macOS app changes

If you edit a `.swift` file in any `*.app/Contents/Resources/`:

1. Run `./build.sh` (or `./build.sh md2pdf` / `doc2md` / `validator`) to recompile the binary.
2. Commit both the source `.swift` and the rebuilt binary so users can run the app without compiling.

If you add a new option to the GUI, also wire it up in:

- the `osascript` AppleScript fallback (`settings_dialog.applescript`)
- the bash launcher (the `IFS='|' read -r ...` line and the `ARGS+=(...)` block)
- the corresponding `--cli-flag` in `md2pdf.py`

---

## Submitting a pull request

1. Make sure your branch is up to date with `main` (rebase, don't merge).
2. Run the smoke tests above.
3. Push to your fork and open a PR against `main`.
4. Fill in the PR template — describe what changed and why, link related issues, list tested examples.
5. A maintainer will review. Expect feedback; treat it as a conversation, not a blocker.

### Commit messages

- Use the imperative mood: "Add X", "Fix Y", not "Added", "Fixes".
- First line ≤ 72 characters; explain the *why* in the body if needed.
- One logical change per commit. Squash WIP commits before opening the PR.

### What we look for in review

- Does the change do exactly what the PR says?
- Is the code consistent with the surrounding style?
- Is there an example or test that would catch a regression?
- Are docs updated?
- No personal data, no Cyrillic in code, no broken absolute paths.

---

## Reporting bugs and requesting features

Open an issue using the appropriate template:

- **Bug report** — include the input `.md` (or a minimal reproducer), the exact CLI command, the OS, the Python version, and the relevant CLI/GUI output.
- **Feature request** — describe the use case first, then the proposed syntax/behavior.

If you can also provide a fix, even better — open an issue first so we can agree on the approach before you spend time on it.

---

## Security issues

Please **do not open a public issue** for security problems. See [`SECURITY.md`](SECURITY.md) for the disclosure process.

---

## License

By contributing, you agree that your contribution will be licensed under the MIT License (see [`LICENSE`](LICENSE)).
