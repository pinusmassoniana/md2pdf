# md2pdf

A Markdown → PDF converter focused on producing **tutorial-style booklets, lecture notes, and study guides**: cover page, table of contents with page numbers, syntax-highlighted code, charts, math formulas, multi-column and landscape layouts, and authorship-protection features (SHA-256, UUID, optional QR code, steganography in charts).

The repository ships three tools:

| Tool | Purpose |
|------|---------|
| **`md2pdf.py`** | Markdown → PDF (the main converter) |
| **`doc2md.py`** | `.docx` / `.pptx` / `.pdf` → Markdown (round-trip-friendly with md2pdf) |
| **`md2pdf-validator.app`** | Verify SHA-256 / UUID / fingerprints in a generated PDF |

On macOS each tool is also available as a drag-and-drop **`.app` bundle** with a native settings dialog.

---

## Quick start

```bash
# 1. Install dependencies (reportlab is required; the rest are optional, see below)
pip install -r requirements.txt

# 2. Convert a Markdown file
python3 md2pdf.py examples/quickstart.md --font-dir fonts

# 3. Try the feature showcase with a theme
python3 md2pdf.py examples/features-showcase.md --font-dir fonts --theme blue

# 4. Merge two chapters into one book PDF
python3 md2pdf.py examples/merge-chapter-1.md examples/merge-chapter-2.md \
    --merge -o book.pdf --font-dir fonts --renumber
```

See [`examples/README.md`](examples/README.md) for a full tour, and [`md2pdf_format.md`](md2pdf_format.md) for the complete Markdown format reference.

---

## Requirements

- **Python 3.9+**
- **`reportlab>=4.0`** — required (PDF rendering)
- **`matplotlib>=3.5`** — optional (`` ```chart `` blocks; without it charts become placeholders)
- **`qrcode[pil]>=7.4`** — optional (`--qr`)
- **`python-docx`, `python-pptx`, `PyMuPDF`** — optional (`doc2md` only, one per format)

The fonts in [`fonts/`](fonts/) are **DejaVu Sans / Mono / Condensed** and are distributed under their own permissive license — see [`fonts/LICENSE.md`](fonts/LICENSE.md). On Linux they are typically already installed at `/usr/share/fonts/truetype/dejavu`; on macOS / Windows the bundled copies in `fonts/` are used by default.

---

## Features

- **Cover page** — auto-generated from the first `# H1`, with theme colors, author, optional background image, optional QR code with metadata
- **Table of contents** — auto-generated, with page numbers, configurable depth (`--toc-depth 2/3/4`)
- **10 themes** — `teal` (default), `blue`, `purple`, `red`, `green`, `orange`, `navy`, `rose`, `brown`, `dark`; or load your own from a JSON file
- **Document templates** — predefined preset bundles for lectures / notes / study guides / reports / cheat sheets (template keys are Russian; see the format doc)
- **Syntax highlighting** — Python, JavaScript / TypeScript, SQL, Bash, Java, Go, C / C++, HTML / CSS / XML, Kotlin
- **Line highlighting** in code blocks — `{highlight="2-5,8"}`
- **Charts** — `pie`, `bar`, `line`, `area` via matplotlib, with custom colors and sizes
- **Math** — inline `$E=mc^2$` and block `$$...$$` formulas (subset of LaTeX)
- **Tables** — alignment markers, captions, auto column widths, `|` escaping
- **Callouts** — GitHub-style `> [!NOTE]`, `WARNING`, `TIP`, `IMPORTANT`, `CAUTION`
- **Footnotes** — `[^key]` references with multi-line definitions
- **Block directives** — `:::landscape` (rotate individual pages), `:::fit-page` (auto-shrink to one page), `:::columns N` (multi-column layout); nestable
- **Merge mode** — `--merge` joins multiple files into a single PDF with a shared cover, TOC, continuous page numbers, and optional global H2 renumbering
- **HTML preview** — `--html` produces a standalone HTML file alongside the PDF, with embedded CSS, code highlighting, and `page-break-inside: avoid` for printing
- **Authorship protection** — automatic SHA-256 of the source `.md`, copy UUID, invisible per-page fingerprint with `--author`, steganography in chart PNGs (`--extract-stego`), optional QR code (`--qr`) and footer copy ID (`--copy-id`); verify with `--verify`

---

## Usage

### Common patterns

```bash
# Default: input.md → input.pdf
python3 md2pdf.py input.md --font-dir fonts

# Specify output path
python3 md2pdf.py input.md -o report.pdf --font-dir fonts

# Theme + custom watermark
python3 md2pdf.py input.md --theme blue --watermark "DRAFT" --font-dir fonts

# Wide margins, A4 landscape, with HTML preview
python3 md2pdf.py input.md --margins wide --page-size a4-landscape --html --font-dir fonts

# Batch processing
python3 md2pdf.py *.md --font-dir fonts

# Watch a file and rebuild on changes
python3 md2pdf.py input.md --watch --font-dir fonts

# Merge chapters into one PDF, with chapter separator pages
python3 md2pdf.py chapter_*.md --merge -o book.pdf \
    --renumber --chapter-page --font-dir fonts

# Authorship: QR + copy ID + author fingerprint
python3 md2pdf.py input.md --author "Jane Doe" --qr --copy-id --font-dir fonts

# Verify a generated PDF against the source
python3 md2pdf.py input.md --verify report.pdf
```

A full reference of all CLI flags and front-matter keys lives in [`md2pdf_format.md`](md2pdf_format.md).

### doc2md

```bash
# DOCX/PPTX/PDF → Markdown (compatible with md2pdf)
python3 doc2md.py examples/sample.docx -o sample.md
python3 doc2md.py examples/sample.pptx -o presentation.md
python3 doc2md.py report.pdf -o report.md
```

---

## macOS apps

Each `.app` bundle in this repo is a drag-and-drop launcher around the matching Python script:

- **`md2pdf.app`** — drop `.md` files, configure via the native Cocoa dialog (theme, template, margins, page size, watermark, merge mode, etc.), and the converter runs in the background with a notification when done. Settings persist between runs.
- **`doc2md.app`** — drop `.docx`, `.pptx`, or `.pdf` files; outputs Markdown.
- **`md2pdf-validator.app`** — drop a generated `.pdf` to verify SHA-256, UUID, and embedded fingerprints.

The bundles use **relative symlinks** to the Python scripts in the repo root, so they work immediately after `git clone` without any build step. To rebuild the native Swift settings dialogs from source, run:

```bash
./build.sh
```

This requires the Xcode Command Line Tools (`xcode-select --install`) for `swiftc`.

---

## Markdown format

The full format reference — every supported syntax, every directive, every CLI flag, the YAML front matter keys, the document templates, and the authorship-protection details — is in [`md2pdf_format.md`](md2pdf_format.md).

A practical tour with runnable examples is in [`examples/`](examples/).

---

## Project layout

```
md2pdf/
├── md2pdf.py                  # main Markdown → PDF converter
├── doc2md.py                  # DOCX/PPTX/PDF → Markdown
├── md2pdf_format.md           # full format reference
├── examples/                  # runnable examples (see examples/README.md)
├── fonts/                     # bundled DejaVu fonts (separate license)
├── md2pdf.app/                # macOS drag-and-drop bundle for md2pdf
├── doc2md.app/                # macOS drag-and-drop bundle for doc2md
├── md2pdf-validator.app/      # macOS PDF authorship verifier
├── build.sh                   # rebuild Swift GUIs from sources
├── requirements.txt
└── LICENSE                    # MIT
```

---

## Contributing

Issues and pull requests are welcome at <https://github.com/pinusmassoniana/md2pdf>.

- See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, conventions, and the PR workflow.
- See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) for community expectations.
- See [`SECURITY.md`](SECURITY.md) before reporting a security vulnerability — **do not** open a public issue.

If you add a feature that introduces a new Markdown construct, please:
1. Add or extend an example in `examples/` that exercises it.
2. Document the syntax in `md2pdf_format.md`.

---

## License

- The code in this repository is released under the **MIT License** — see [`LICENSE`](LICENSE).
- The bundled DejaVu fonts in `fonts/` are released under their **own license** — see [`fonts/LICENSE.md`](fonts/LICENSE.md).
