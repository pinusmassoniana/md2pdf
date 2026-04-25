---
name: Bug report
about: Something doesn't work the way it should
title: "[Bug] "
labels: bug
assignees: ''
---

## What happened

<!-- A clear and concise description of what went wrong. -->

## Expected behavior

<!-- What you expected to happen instead. -->

## Reproduction

**Tool affected** (delete the others):
- [ ] `md2pdf.py`
- [ ] `doc2md.py`
- [ ] `md2pdf-validator`
- [ ] `md2pdf.app` / `doc2md.app` / `md2pdf-validator.app`

**Exact command** (CLI users):
```bash
python3 md2pdf.py ... 
```

**Minimal input file** that reproduces the issue (paste the `.md` content, or attach the `.docx` / `.pptx` / `.pdf` if it's small):

```markdown
# Heading

Paragraph that triggers the bug.
```

**Output / error** (full stderr, including the traceback if there is one):

```
paste here
```

## Environment

- **OS** (e.g. macOS 14.5, Ubuntu 22.04, Windows 11):
- **Python version** (`python3 --version`):
- **md2pdf commit** (`git rev-parse --short HEAD` if cloned, otherwise version / date downloaded):
- **Dependency versions** (paste the relevant lines from `pip list`):
  - reportlab:
  - matplotlib (if relevant):
  - PyMuPDF / python-docx / python-pptx (if doc2md):

## Additional context

<!-- Screenshots of the broken PDF, related issues, anything that helps. -->

## Checklist

- [ ] I searched existing issues and didn't find a duplicate.
- [ ] I included a minimal reproducer (input file + command).
- [ ] I'm running the latest `main` branch (or noted the version above).
