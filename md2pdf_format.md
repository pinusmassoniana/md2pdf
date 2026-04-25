# Markdown Format for md2pdf

The converter produces a tutorial-style PDF with a cover, a table of contents (with page numbers), and page numbering.

## File structure

```markdown
# Document title (exactly one H1 — becomes the title and the cover)

## Section title (H2 — included in the table of contents)

### Subsection (H3/H4 — included in the TOC when toc-depth is 3/4)

A regular paragraph. Consecutive lines without a blank line between
them are joined into a single paragraph.

A blank line separates paragraphs.

:::landscape
Content rendered on landscape pages (wide tables, charts)
:::

:::fit-page
Content scaled to fit on a single page
:::

:::columns 2
Multi-column layout
:::
```

## YAML Front Matter

You can specify metadata at the top of the file that overrides settings:

```markdown
---
theme: blue
author: J. Doe
subtitle: Physics lecture
watermark: DRAFT
template: lecture
title: Foundations of Genetics
cover_top: LECTURE 5
cover: true
toc: true
justify: true
code_line_numbers: false
margins: wide
page_size: a4
toc_depth: 3
---
```

Supported keys: `theme`, `author`, `subtitle`, `watermark`, `template`, `title` (document title overriding the H1), `cover_top` (cover super-title), `cover` (true/false), `toc` (true/false), `justify` (true/false), `code_line_numbers` (true/false), `margins` (narrow/medium/wide), `page_size`, `toc_depth` (2/3/4), `cover_image`, `qr` (true/false), `copy_id` (true/false).

Precedence: YAML front matter > template > CLI arguments > defaults.

## Document title (H1)

The first `# Heading` is the title of the whole document. It is shown on the cover and in the running header.

Format for an automatic cover:
```
# Lecture 3. Foundations of network protocols
```
Words like `Lecture`, `Topic`, `Class`, `Lesson`, `Chapter`, `Section`, `Module`, `Unit`, `Part` followed by a number are automatically lifted onto the cover as a large super-title.

**Override the title**: `--title "Name"` or `title:` in the YAML front matter replaces the title extracted from the first `# H1`. Useful when neither the file name nor the H1 is appropriate for the cover.

**Override the super-title**: `--cover-top "LECTURE 1"` or `cover_top:` in the YAML front matter replaces the auto-extracted super-title (e.g. "LECTURE 3"). If you don't want a super-title, pass an empty string `--cover-top ""`.

Subsequent `# H1`s are top-level sections (each starts on a new page). The current H1 is shown in the running header.

## Sections (H2)

All `## headings` are automatically included in the table of contents with page numbers. Numbering is recommended:
```
## 1. Introduction
## 2. Main part
## 3. Conclusion
```

## Inline formatting

| Syntax | Result |
|--------|--------|
| `**text**` | bold |
| `*text*` | italic |
| `` `code` `` | inline code (monospace, with background) |
| `~~text~~` | strikethrough |
| `[text](url)` | clickable link |
| `H~2~O` | subscript (H₂O) |
| `m^2^` | superscript (m²) |
| `$E=mc^2$` | inline formula |
| `[^key]` | footnote reference |
| `\*`, `\#`, `` \` ``, `\[`, `\]`, `\\`, `\^` | escape special characters |

## Lists

```markdown
- Bulleted item
  - Nested level 1 (2 spaces)
    - Level 2 (4 spaces)
      - Level 3 (6 spaces)

1. Numbered
2. List
   1. Nested (3 spaces)
   2. Sub-item
      1. Even deeper (6 spaces)
```

Bulleted lists support up to 4 levels of nesting (●, ○, ▪, ▸).
Numbered lists support nesting via indentation (3 spaces per level).

## Checkboxes

```markdown
- [x] Done
- [ ] Not done
  - [x] Nested item
```

Renders as ☑/☐ followed by the text. Supports nesting.

## Images

```markdown
![Caption for the image](path/to/image.png)
![](photo.png)
```

The path may be absolute or relative (relative to the .md file). The image is scaled to the page width. The alt text is rendered as a caption underneath. If the file is not found, a placeholder is shown.

### Size and text wrap

Pandoc-style attributes in curly braces after the image:

```markdown
![Diagram](img.png){width=50% float=right}   # 50% wide, text wraps to the right
![](photo.png){width=30% float=left}          # 30%, wrap on the left
![Table](tbl.png){width=80%}                  # 80% wide, block-style (centered)
![](img.png){float=right}                     # wrap right, auto width
![Caption](img.png)                            # no attributes — current behavior
```

| Attribute | Values | Description |
|-----------|--------|-------------|
| `width` | `10%`–`100%` | Width as a percentage of the content area |
| `float` | `left`, `right` | Text wrap (text after the image wraps around it) |

Without `float` the image is block-style (centered). Without `width` it has auto sizing (fits the available width).

### Image directory (`--image-dir`)

If your images are not next to the .md file, you can specify a search directory:

```
python md2pdf.py input.md --image-dir /path/to/images
```

Then in markdown you can reference images by file name only:
```markdown
![Diagram](diagram.png)
```

Search precedence:
1. Absolute path — used as-is
2. Relative to the .md file's directory (the default behavior)
3. In `image-dir/file_name`
4. Recursively in `image-dir/**/file_name`

In the GUI there is an "📷 Images..." button to pick a folder.

## Code blocks with syntax highlighting

Wrap in triple backticks and specify a language:

````markdown
```python
def example():
    # Comment
    return "hello"
```
````

Syntax highlighting for: `python`/`py`, `javascript`/`js`/`ts`, `bash`/`sh`, `sql`, `java`, `go`/`golang`, `c`/`cpp`/`c++`, `html`/`css`/`xml`, `kotlin`/`kt`. Keywords, strings, comments, and numbers are highlighted. Without a language specifier — no highlighting.

When a language is specified, a label (Python, SQL, Bash, etc.) is shown in the top-right corner of the block.

Blocks of 3 or more lines automatically get line numbers (disable via `--no-line-numbers` or `code_line_numbers: false` in YAML).

### Line highlighting

To draw attention to specific lines, highlight them with a yellow background:

````markdown
```python {highlight="2-3"}
def greet(name):
    message = f"Hello, {name}!"  # ← highlighted
    print(message)               # ← highlighted
    return message
```
````

Format: `{highlight="LINES"}`, where LINES is comma-separated: numbers (`2,5`) or ranges (`2-5`). Combinations: `{highlight="1,3-5,8"}`.

### Strict block closing

A block is closed only by a fence of the same kind (`` ` `` or `~`) of length ≥ the opening fence. This lets you show code inside code:

`````markdown
````markdown
```python
print("hello")
```
````
`````

## Charts

Charts are rendered from a ` ```chart ` block. Data is described in a YAML-like format and rendered to PNG via matplotlib.

**Required**: `pip install matplotlib` (without it a placeholder is shown instead).

### Pie chart

````markdown
```chart
type: pie
title: Cause distribution
Tubal factor: 35
Endometriosis: 25
Male factor: 20
Unexplained: 20
```
````

### Bar chart

````markdown
```chart
type: bar
title: Test Scores by Group
labels: Group 1, Group 2, Group 3
Math: 85, 78, 92
Physics: 72, 88, 65
```
````

### Line chart

````markdown
```chart
type: line
title: Metric trend
labels: Jan, Feb, Mar, Apr, May
Series A: 10, 25, 18, 32, 28
Series B: 5, 15, 22, 19, 35
```
````

### Area chart

````markdown
```chart
type: area
title: Monthly load
labels: Jan, Feb, Mar, Apr
CPU: 45, 62, 55, 70
RAM: 30, 48, 42, 58
```
````

### Directives

| Directive | Value | Default |
|-----------|-------|---------|
| `type:` | `pie`, `bar`, `line`, `area` | `bar` |
| `title:` | Chart title | none |
| `labels:` | X-axis labels (comma-separated) | 1, 2, 3... |
| `legend:` | `true` / `false` | `true` |
| `size:` | `standard`, `wide`, `small` | `standard` |
| `colors:` | Hex colors, comma-separated | from theme |

Data rows have the format: `Series name: value1, value2, ...`

For a pie chart each row is a single sector with a single value.

## Tables

```markdown
Table 1: Table description

| Header 1 | Header 2 | Header 3 |
|:---------|:--------:|---------:|
| Left     | Center   | Right    |
```

Column widths are auto-distributed by content.

**Escaping**: a `|` character inside cells is escaped as `\|`:
```markdown
| Formula | Description |
|---------|-------------|
| a \| b  | a or b      |
```

**Alignment**: `:---` — left, `:---:` — center, `---:` — right.

**Captions**: a line before the table of the form `Table N: text` automatically becomes the caption.

## Quotes / definitions

```markdown
> Quoted text or a definition. Supports **bold** and *italic*.
```

Rendered as a colored block with a border.

## Callouts (Admonitions)

GitHub-style callouts to highlight important information:

```markdown
> [!NOTE]
> Additional information.

> [!WARNING]
> Warning about possible problems.

> [!TIP]
> A useful tip.

> [!IMPORTANT]
> Critical information.

> [!CAUTION]
> Be careful with this operation.
```

Rendered as a block with a colored left bar and a pastel background: NOTE (light blue), WARNING (yellow), TIP (green), IMPORTANT (purple), CAUTION (red). The text is always dark — readable on any theme.

## Definition Lists

```markdown
HTTP
: HyperText Transfer Protocol, the foundation of the web.

API
: Application Programming Interface.
```

The term goes on its own line; the definition begins with `: ` on the next line.

## Explicit page break

```markdown
\pagebreak
```

or

```markdown
\newpage
```

Inserts a forced page break. Useful for separating content without creating a new heading.

## Horizontal rule

```markdown
---
```

## Footnotes

```markdown
Text with a footnote reference[^note1] and another one[^note-2].

[^note1]: First footnote text. Supports **formatting**.
[^note-2]: A multi-line footnote — continues
    on the next line (4-space indent).
```

Footnote definitions (`[^key]: text`) may appear anywhere in the file — they are collected automatically and removed from the body. Keys support letters, digits, hyphens, and dots (`[^note-1]`, `[^ref.2]`). Multi-line definitions continue with 4-space-indented lines. References `[^key]` in the body are replaced with superscript numbers. A "Notes" section with numbered footnotes is rendered at the end of the document.

## Math formulas

### Inline formulas

```markdown
Energy $E = mc^2$, sum $\sum_{i=1}^{n} x_i$.
```

### Block formulas

```markdown
$$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$
```

Supported syntax:
- Greek letters: `\alpha`, `\beta`, `\gamma`, `\delta`, `\epsilon`, `\theta`, `\lambda`, `\mu`, `\pi`, `\sigma`, `\phi`, `\omega`, etc.
- Capitals: `\Alpha`, `\Gamma`, `\Delta`, `\Sigma`, `\Omega`, `\Pi`, `\Phi`
- Symbols: `\pm`, `\times`, `\cdot`, `\leq`, `\geq`, `\ne`, `\approx`, `\infty`, `\to`, `\sum`, `\prod`, `\int`, `\partial`, `\nabla`, `\sqrt`, `\degree`
- Fractions: `\frac{numerator}{denominator}`
- Super/subscripts: `x^2`, `x_{i+1}`, `x^{2n}`, `H_2O`

## Block directives

Block directives wrap content and affect its rendering. Syntax: `:::directive` opens, `:::` closes. Directives can be nested.

| Directive | Description |
|-----------|-------------|
| `:::columns N` | Multi-column layout (N columns, default 2) |
| `:::landscape` | Landscape page orientation |
| `:::fit-page` | Scale content to fit on one page |

Nesting example:

```markdown
:::landscape
:::fit-page

| huge | wide | table |
| --- | --- | --- |
| ... | ... | ... |

:::
:::
```

## Multi-column layout

```markdown
:::columns 3
First column text.

Second column text.

Third column text.
:::
```

The number after `columns` is the column count (default 2). Standard markup is supported inside.

## Landscape orientation

Individual pages can be rendered in landscape — for wide tables, charts, or code:

```markdown
:::landscape

## Wide table

| col1 | col2 | col3 | col4 | col5 | col6 | col7 | col8 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| data | data | data | data | data | data | data | data |

:::
```

Everything between `:::landscape` and `:::` will be placed on landscape-oriented pages (width and height swapped). The header, footer, and watermark adapt automatically to the new page dimensions. Switching to a landscape page and back happens automatically — no blank pages are produced.

Between `:::landscape` and `:::` you can use any headings (H1–H4), tables, images, code, charts, and other standard markup.

**Note**: if the entire document is already in landscape (`--page-size a4-landscape`), `:::landscape` does not change orientation — pages stay landscape.

## Fit on a single page (fit-page)

The `:::fit-page` directive scales content (tables, charts, code) so that it fits on a single page. If the content does not fit, fonts and elements are scaled down proportionally automatically.

```markdown
:::fit-page

Table 1: A large table with 30 rows

| Column 1 | Column 2 | Column 3 | Column 4 |
| --- | --- | --- | --- |
| data | data | data | data |
| ...29 more rows... | | | |

:::
```

It can be combined with `:::landscape` for wide tables:

```markdown
:::landscape
:::fit-page

| very | wide | table | with | many | columns | and | rows |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ... | ... | ... | ... | ... | ... | ... | ... |

:::
:::
```

In the HTML version the block is wrapped in `<div class="fit-page">` and gets `page-break-inside: avoid` when printed.

## Document templates

Predefined preset bundles:

| Template | Cover | TOC | Margins | Justify | Description |
|----------|-------|-----|---------|---------|-------------|
| `lecture` | yes | yes (depth 3) | medium | yes | Standard lecture |
| `notes` | no | no | narrow | no | Compact notes |
| `manual` | yes | yes (depth 4) | wide | yes | Study guide, duplex |
| `report` | yes | yes (depth 2) | medium | yes | Term paper / report |
| `cheatsheet` | no | no | narrow | no | Without code line numbers |

Specified via `--template lecture` on the CLI or `template: lecture` in the YAML front matter.

## CLI arguments

```
python md2pdf.py input.md                           # → input.pdf
python md2pdf.py input.md -o output.pdf             # specify the output file
python md2pdf.py input.md --theme blue              # blue theme
python md2pdf.py input.md --no-cover                # without cover
python md2pdf.py input.md --no-toc                  # without table of contents
python md2pdf.py input.md --toc-depth 3             # TOC depth
python md2pdf.py input.md --watermark "Name"        # watermark
python md2pdf.py input.md --no-watermark            # no watermark
python md2pdf.py input.md --subtitle "Lecture"      # cover subtitle text
python md2pdf.py input.md --author "Author"         # author name (shown on the cover)
python md2pdf.py input.md --template lecture        # document template
python md2pdf.py input.md --margins wide            # wide margins
python md2pdf.py input.md --page-size a4-landscape  # page size / orientation
python md2pdf.py input.md --duplex                  # mirrored margins + outer page numbers
python md2pdf.py input.md --cover-image bg.png      # cover background
python md2pdf.py input.md --title "Name"             # document title (instead of H1)
python md2pdf.py input.md --cover-top "LECTURE 1"    # cover super-title
python md2pdf.py input.md --no-justify              # no justified alignment
python md2pdf.py input.md --no-line-numbers         # no code line numbers
python md2pdf.py input.md --html                    # + HTML version
python md2pdf.py input.md --custom-theme theme.json # custom theme
python md2pdf.py input.md --font-dir /path/to/fonts # path to fonts
python md2pdf.py input.md --watch                   # watch for changes
python md2pdf.py input.md --dry-run                 # parse only
python md2pdf.py *.md                               # batch processing
python md2pdf.py input.md --image-dir /path/to/images # image directory
python md2pdf.py input.md --h2-break auto            # conditional break before ##
python md2pdf.py input.md --h2-break never           # no break before ##
python md2pdf.py *.md --merge -o book.pdf            # merge into a single PDF
python md2pdf.py *.md --merge --title "Textbook"     # with a custom title
python md2pdf.py *.md --merge --h1-titles "Ch. 1" "Ch. 2"  # custom chapter titles
python md2pdf.py *.md --merge --renumber             # global renumbering of ##
python md2pdf.py *.md --merge --chapter-page         # decorative chapter separator pages
python md2pdf.py input.md --qr                       # QR code with metadata in the header
python md2pdf.py input.md --copy-id                  # UUID of the copy in the footer
python md2pdf.py input.md --verify output.pdf        # verify SHA-256 hash
python md2pdf.py input.md --extract-stego output.pdf # extract steganography from charts
```

## Break before H2 (`--h2-break`)

Controls page breaks before `##` headings:

| Value | Behavior |
|-------|----------|
| `always` | Each `##` starts on a new page (default) |
| `auto` | Break only if there is little room left on the page |
| `never` | No forced break |

Set via `--h2-break auto` on the CLI, or in the GUI ("## break" dropdown).

## Merging files (merge)

`--merge` mode combines several `.md` files into a single PDF with one shared cover, one shared TOC, and continuous page numbering. Each file becomes a separate chapter (H1).

```
python md2pdf.py file1.md file2.md file3.md --merge -o book.pdf
```

### File order

When several files are passed, they are sorted automatically in **natural order** (1, 2, 10 instead of 1, 10, 2). This is convenient with globs:

```
python md2pdf.py chapter_*.md --merge -o textbook.pdf
```

### Chapter titles (`--h1-titles`)

By default the chapter title is the first `# H1` in each file. You can override:

```
python md2pdf.py *.md --merge --h1-titles "Introduction" "Main part" "Conclusion"
```

In the GUI there is an input field for each file in the merge panel (right side of the window).

### Continuous H2 numbering (`--renumber`)

The `--renumber` flag renumbers all `##` headings globally. If H2s are numbered locally in each file (1, 2, 3), after merging they get a continuous numbering: 1–12 in the first file, 13–20 in the second, and so on.

It recognizes the format `## N. Text` (where N is a number with a dot) and replaces N with the global counter.

### Chapter separator pages (`--chapter-page`)

The `--chapter-page` flag adds a decorative separator page before each chapter (except the first). The page shows:
- The chapter title (large, centered)
- The subtitle and author from the file's front matter (if set)

### Running header

In merge mode the header shows: `Document title · Chapter · Section`. The document title is the overall heading, the chapter is the current H1, the section is the current H2.

### Front matter of the first file

Metadata from the YAML front matter of **the first file** (theme, template, author, subtitle, watermark, etc.) applies to the entire merged document.

### Subtitle/author in the TOC

If the front matter of individual files defines `subtitle` or `author`, they are shown under the chapter title in the TOC (in small type).

### Error handling

If one of the files fails to parse, it is skipped — the other files are still processed. Skipped files are listed in the output.

### A single file in merge

`--merge` works with a single file too — useful for uniform processing (front matter, cover format, TOC).

## Themes

Available themes: `teal` (default), `blue`, `purple`, `red`, `green`, `orange`, `navy`, `rose`, `brown`, `dark`.

You can load a custom theme from JSON (`--custom-theme theme.json`):
```json
{
  "primary": "#1A6B5C",
  "primary_light": "#E8F5F1",
  "secondary": "#2D8B7A",
  "accent": "#D4A853",
  "table_alt": "#F0F7F5",
  "border": "#C8DDD8",
  "cover_circles": ["#1F7D6D", "#177060", "#1D7567"],
  "cover_sub": "#A8D5CB"
}
```

## Page sizes

`a4`, `a4-landscape`, `letter`, `letter-landscape`, `a3`, `a3-landscape`.

The page size sets the orientation of **the whole** document. For individual landscape pages use the `:::landscape` directive (see "Landscape orientation").

## Margins

`narrow` (15/18 mm), `medium` (22/25 mm), `wide` (28/32 mm).

## HTML preview

The `--html` flag creates an .html file alongside the .pdf — a standalone page with embedded CSS and code highlighting. It supports all token types: aligned tables, footnotes, formulas, multi-column layout, landscape pages, fit-page, charts (base64 PNG). Landscape blocks are wrapped in `<div class="landscape-page">`, fit-page in `<div class="fit-page">` with `page-break-inside: avoid` when printed.

## Authorship protection

The converter supports several mechanisms for protecting authorship of PDF documents.

### Automatic (no flags)

- **SHA-256 hash** — the hash of the source .md file is written into custom PDF metadata (`SourceSHA256`). Verification: `--verify output.pdf input.md`.
- **Copy UUID** — a unique identifier of each generation is written into PDF metadata (`CopyUUID`).
- **Invisible fingerprint** — when `--author` is set, a microtext (1pt, almost invisible) is drawn on every page with the author name, date, and UUID. Visible when selecting text or via `pdftotext`.
- **Steganography in charts** — when `--author` is set and there are charts, the author name is embedded into the LSB of the red channel of PNG images. Extraction: `--extract-stego output.pdf`.

### Flags

- `--qr` — a QR code with JSON metadata (author, date, hash, UUID) in the top-right corner of the header on every page. Requires `pip install qrcode[pil]`.
- `--copy-id` — the first 8 characters of the copy UUID in small grey text in the footer of every page.

### Verification

```bash
# Check integrity (SHA-256 hash matches the source)
python md2pdf.py input.md --verify output.pdf

# Extract steganography from charts
python md2pdf.py input.md --extract-stego output.pdf
```

YAML front matter: `qr: true`, `copy_id: true`.

## Document template

```markdown
---
theme: teal
author: J. Doe
template: lecture
---

# Lecture N. Topic name

## 1. Introduction

Introductory paragraph with a formula $E = mc^2$ and a footnote[^1].

![Process diagram](schema.png)

## 2. Core concepts

### Definitions

> **Term** — definition of the term.

### Data table

Table 1: System parameters

| Parameter | Description | Value |
|:----------|:-----------:|------:|
| timeout   | Timeout     | 30 s  |
| retries   | Attempts    | 3     |

### Formulas

Quadratic equation:

$$\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$

### Tasks

- [x] Study the theory
- [ ] Do the exercises
  - [ ] Exercise 1
  - [ ] Exercise 2

### Code samples

```python
def process(data):
    for item in data:
        if item.valid:
            yield item.value
```

### Charts

```chart
type: pie
title: Grade distribution
Excellent: 30
Good: 45
Satisfactory: 20
Unsatisfactory: 5
```

```chart
type: bar
title: Group results
labels: Group A, Group B, Group C
Theory: 85, 72, 90
Practice: 78, 88, 65
```

```chart
type: line
title: Semester trend
labels: Sep, Oct, Nov, Dec, Jan
Attendance: 95, 88, 82, 78, 85
Performance: 70, 75, 72, 80, 85
```

```chart
type: area
title: Weekly load
labels: Wk 1, Wk 2, Wk 3, Wk 4
Lectures: 6, 8, 6, 10
Practice: 4, 6, 8, 6
```

## 3. Two-column section

:::columns 2
Left column with text.

Right column with text.
:::

:::landscape
:::fit-page

## 4. Wide table (landscape, fit on one page)

Table 2: Experiment results

| Experiment | Param A | Param B | Param C | Param D | Param E | Result | Error |
|:-----------|:-------:|:-------:|:-------:|:-------:|:-------:|-------:|------:|
| Trial 1    | 12.5    | 8.3     | 45.1    | 2.7     | 0.95    | 156.2  | ±2.1  |
| Trial 2    | 14.8    | 7.1     | 38.9    | 3.2     | 0.87    | 148.7  | ±1.8  |

:::
:::

---

## 5. Conclusion

Closing paragraph. Water H~2~O, area m^2^, ~~obsolete text~~.

[^1]: Footnote text with **formatting** and a [link](https://example.com).
```
