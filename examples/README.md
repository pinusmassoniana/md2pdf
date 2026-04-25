# Examples

Demo files for `md2pdf` and `doc2md`. Run any of them through the CLI to see the converter in action.

## md2pdf inputs

| File | What it demonstrates |
|---|---|
| [`quickstart.md`](quickstart.md) | Minimal Markdown — headings, list, italics, inline code, blockquote |
| [`features-showcase.md`](features-showcase.md) | Full feature tour — checkboxes, nested lists, escaping, syntax highlighting (Python / JS / SQL / Bash), tables, YAML front matter |
| [`charts.md`](charts.md) | All chart types (`pie`, `bar`, `line`, `area`), custom colors, sizes |
| [`merge-chapter-1.md`](merge-chapter-1.md), [`merge-chapter-2.md`](merge-chapter-2.md) | `--merge` mode: stitch multiple chapters into one PDF |
| [`sample-document.md`](sample-document.md) | Reference output: what `doc2md` produces from a `.docx` |
| [`sample-presentation.md`](sample-presentation.md) | Reference output: what `doc2md` produces from a `.pptx` |

## doc2md inputs

| File | What it demonstrates |
|---|---|
| [`sample.docx`](sample.docx) | Word document → Markdown round-trip |
| [`sample.pptx`](sample.pptx) | PowerPoint deck → Markdown round-trip |

## Running the examples

```bash
# Single file → PDF
python3 md2pdf.py examples/quickstart.md --font-dir fonts

# Feature showcase with a theme
python3 md2pdf.py examples/features-showcase.md --font-dir fonts --theme blue

# Charts
python3 md2pdf.py examples/charts.md --font-dir fonts

# Merge two chapters into one PDF
python3 md2pdf.py examples/merge-chapter-1.md examples/merge-chapter-2.md \
    --merge -o examples/merged.pdf --font-dir fonts --renumber

# Convert .docx / .pptx → Markdown
python3 doc2md.py examples/sample.docx -o examples/sample-document-rt.md
python3 doc2md.py examples/sample.pptx -o examples/sample-presentation-rt.md
```

The PDFs created by these commands are git-ignored — run the commands locally to generate them.
