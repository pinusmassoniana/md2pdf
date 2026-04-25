# Security policy

## Supported versions

This project is in active development and does not yet have versioned releases. Security fixes are applied to the `main` branch.

| Branch | Supported |
|--------|-----------|
| `main` | Yes |
| Anything else | No |

## Reporting a vulnerability

**Please do not file a public GitHub issue for security vulnerabilities.** Public issues alert attackers before a fix is in place.

Instead, use one of the following private channels:

1. **GitHub Security Advisory** (preferred): open a private advisory at <https://github.com/pinusmassoniana/md2pdf/security/advisories/new>. This keeps the report private and gives the maintainer a working space to coordinate a fix.
2. **Email**: contact the maintainer through the GitHub profile at <https://github.com/pinusmassoniana>.

When reporting, please include:

- A description of the vulnerability and its impact (e.g., arbitrary file read, code execution, denial of service).
- Steps to reproduce, including a minimal `.md` / `.pdf` / `.docx` / `.pptx` file if relevant.
- The exact CLI command or GUI interaction that triggers the issue.
- Your environment: OS, Python version, dependency versions.
- Whether the vulnerability is already public or known to anyone else.

## What to expect

- **Acknowledgment** within 7 days. If you don't hear back, please ping me publicly with no details — only "I sent a security report on date X".
- **Triage and impact assessment** within 14 days.
- **Fix and disclosure timeline** discussed once severity is understood. We aim for a fix within 30 days for high-severity issues, and we will keep you updated on slipping deadlines.
- **Credit** in the release notes for the fix, if you want it.

## Scope — what counts as a security issue

In scope:

- Arbitrary file read / write outside the input file's directory triggered by crafted Markdown / DOCX / PPTX / PDF input.
- Arbitrary code execution triggered by crafted input or by a malicious YAML front matter / theme JSON.
- Path traversal in `--font-dir`, `--cover-image`, `--image-dir`, `--custom-theme`.
- Authorship-protection bypass: a way to forge a passing `--verify` against a different source `.md`, or to remove the embedded fingerprint / steganography without detection that the document was tampered with.
- Resource exhaustion that takes down a system (e.g., an exponentially nested directive that allocates unbounded memory).

Out of scope:

- Issues requiring the user to supply a malicious file from a source they already chose to trust (e.g., a hostile theme JSON they downloaded and explicitly passed via `--custom-theme`). Document the risk in the README, but it is not a vulnerability.
- Cosmetic glitches in PDF rendering.
- Vulnerabilities in upstream dependencies (`reportlab`, `matplotlib`, `PyMuPDF`, etc.) — please report those upstream first; we'll bump the pinned version when a fixed release is available.
- Anything that requires modifying `md2pdf.py` itself.

## Our commitments

- We will not retaliate against good-faith security researchers.
- We will not pursue legal action against researchers who follow this policy.
- We will keep you informed throughout the process and credit you on disclosure.
