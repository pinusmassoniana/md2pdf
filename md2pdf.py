#!/usr/bin/env python3
"""
md2pdf.py — Markdown -> PDF converter for tutorial-style booklets

Parses .md files automatically and produces nicely typeset PDFs
with a cover, a table of contents, colored blocks, tables, page
numbers, and a watermark.

Dependencies:
    pip install reportlab

Fonts:
    The DejaVuSans family is required (usually preinstalled on Linux).
    On Windows/macOS, download it and point to the directory via --font-dir.

Usage:
    python md2pdf.py input.md                          # -> input.pdf
    python md2pdf.py input.md -o output.pdf            # specify output file
    python md2pdf.py input.md --theme blue             # blue theme
    python md2pdf.py input.md --no-cover               # without cover
    python md2pdf.py input.md --watermark "My Name"    # watermark
    python md2pdf.py input.md --no-watermark           # no watermark
    python md2pdf.py input.md --no-toc                 # no table of contents
    python md2pdf.py input.md --subtitle "Lecture"     # cover subtitle text
    python md2pdf.py input.md --font-dir /path/to/fonts
    python md2pdf.py *.md                              # batch processing
    python md2pdf.py input.md --dry-run                # parse only

Supported Markdown:
    # H1             — section heading (new page)
    ## H2            — subsection
    ### / #### H3    — sub-subsection
    - / *            — bulleted list (nesting via indentation)
    1. 2. 3.         — numbered list
    **bold**         — bold text
    *italic*         — italic text
    `code`           — inline code
    [text](url)      — link
    ```              — code block (fenced)
    > blockquote     — blockquote / definition
    | table |        — Markdown tables
    ---              — horizontal rule
    ## Contents      — TOC section (skipped, generated automatically)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import logging
import uuid
import hashlib
import struct
from datetime import date
from pathlib import Path

_log = logging.getLogger("md2pdf")

from reportlab.lib.pagesizes import A4, letter, A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, Color
from reportlab.lib.styles import ParagraphStyle

try:
    import pyphen as _pyphen
    _HYPHENATOR = _pyphen.Pyphen(lang="en_US")
except Exception:
    _HYPHENATOR = None
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Frame, PageTemplate,
)
from reportlab.platypus.doctemplate import NextPageTemplate
from reportlab.platypus.flowables import Flowable, CondPageBreak, KeepTogether, _listWrapOn
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PAGE_SIZES = {
    "a4": A4,
    "a4-landscape": landscape(A4),
    "letter": letter,
    "letter-landscape": landscape(letter),
    "a3": A3,
    "a3-landscape": landscape(A3),
}
W, H = A4  # default, overridden per-instance

# Margin presets (top, bottom, left, right) in mm
MARGIN_PRESETS = {
    "narrow":  (15, 15, 18, 18),
    "medium":  (22, 22, 25, 25),
    "wide":    (28, 28, 32, 32),
}

# Document templates
DOC_TEMPLATES = {
    "lecture": {
        "subtitle": "Lecture",
        "no_cover": False,
        "no_toc": False,
        "toc_depth": 3,
        "no_justify": False,
        "margins": "medium",
    },
    "notes": {
        "subtitle": "Notes",
        "no_cover": True,
        "no_toc": True,
        "margins": "narrow",
        "no_justify": True,
    },
    "manual": {
        "subtitle": "Study guide",
        "no_cover": False,
        "no_toc": False,
        "toc_depth": 4,
        "duplex": True,
        "no_justify": False,
        "margins": "wide",
    },
    "report": {
        "subtitle": "Report",
        "no_cover": False,
        "no_toc": False,
        "toc_depth": 2,
        "no_justify": False,
        "margins": "medium",
    },
    "cheatsheet": {
        "subtitle": "",
        "no_cover": True,
        "no_toc": True,
        "margins": "narrow",
        "no_justify": True,
        "no_line_numbers": True,
    },
}


# ══════════════════════════════════════════════════════════════════
# COLOR THEMES
# ══════════════════════════════════════════════════════════════════

THEMES = {
    "teal": {
        "primary": "#1A6B5C", "primary_light": "#E8F5F1",
        "secondary": "#2D8B7A", "accent": "#D4A853",
        "table_alt": "#F0F7F5", "border": "#C8DDD8",
        "cover_circles": ["#1F7D6D", "#177060", "#1D7567"],
        "cover_sub": "#A8D5CB",
    },
    "blue": {
        "primary": "#1A4B8C", "primary_light": "#E8EFF8",
        "secondary": "#2D6BBF", "accent": "#D4A853",
        "table_alt": "#EFF4FB", "border": "#B8CCE0",
        "cover_circles": ["#1F5FA0", "#174B88", "#1D5590"],
        "cover_sub": "#A8C5E0",
    },
    "purple": {
        "primary": "#5B2D8C", "primary_light": "#F3EBF9",
        "secondary": "#7B4DBF", "accent": "#D4A853",
        "table_alt": "#F5F0FB", "border": "#D0BCE0",
        "cover_circles": ["#6B3DA0", "#5A2D88", "#653790"],
        "cover_sub": "#C8A8E0",
    },
    "red": {
        "primary": "#8C1A2D", "primary_light": "#FDEEF0",
        "secondary": "#BF3D4D", "accent": "#D4A853",
        "table_alt": "#FBF0F2", "border": "#E0B8BC",
        "cover_circles": ["#A01F35", "#881730", "#901D32"],
        "cover_sub": "#E0A8B0",
    },
    "dark": {
        "primary": "#2D3748", "primary_light": "#EDF2F7",
        "secondary": "#4A5568", "accent": "#D69E2E",
        "table_alt": "#F7FAFC", "border": "#CBD5E0",
        "cover_circles": ["#3D4A5C", "#2A3A50", "#354558"],
        "cover_sub": "#A0AEC0",
    },
    "green": {
        "primary": "#2E7D32", "primary_light": "#E8F5E9",
        "secondary": "#43A047", "accent": "#F9A825",
        "table_alt": "#F1F8F2", "border": "#A5D6A7",
        "cover_circles": ["#388E3C", "#2E7D32", "#339438"],
        "cover_sub": "#A5D6A7",
    },
    "orange": {
        "primary": "#E65100", "primary_light": "#FFF3E0",
        "secondary": "#F57C00", "accent": "#5D4037",
        "table_alt": "#FFF8F0", "border": "#FFCC80",
        "cover_circles": ["#EF6C00", "#E65100", "#EA6500"],
        "cover_sub": "#FFAB91",
    },
    "navy": {
        "primary": "#1A237E", "primary_light": "#E8EAF6",
        "secondary": "#283593", "accent": "#C6A700",
        "table_alt": "#ECEEF8", "border": "#9FA8DA",
        "cover_circles": ["#1E2A8C", "#1A237E", "#1C2785"],
        "cover_sub": "#9FA8DA",
    },
    "rose": {
        "primary": "#AD1457", "primary_light": "#FCE4EC",
        "secondary": "#C2185B", "accent": "#D4A853",
        "table_alt": "#FDF0F4", "border": "#F48FB1",
        "cover_circles": ["#C2185B", "#AD1457", "#B81759"],
        "cover_sub": "#F48FB1",
    },
    "brown": {
        "primary": "#4E342E", "primary_light": "#EFEBE9",
        "secondary": "#6D4C41", "accent": "#F9A825",
        "table_alt": "#F5F0EE", "border": "#BCAAA4",
        "cover_circles": ["#5D4037", "#4E342E", "#553B33"],
        "cover_sub": "#BCAAA4",
    },
}

# Fixed colors
DARK_TEXT = HexColor("#1A2332")
MEDIUM_TEXT = HexColor("#4A5568")
CODE_BG = HexColor("#F5F5F5")
CODE_BORDER = HexColor("#E0E0E0")
CODE_INLINE_COLOR = HexColor("#C7254E")
CODE_INLINE_BG = HexColor("#F9F2F4")
HIGHLIGHT_BG = HexColor("#FFF8E7")
ALERT_BG = HexColor("#FEF2F2")
ALERT_BORDER = HexColor("#DC6B6B")


# ══════════════════════════════════════════════════════════════════
# EXCEPTIONS
# ══════════════════════════════════════════════════════════════════

class FontNotFoundError(RuntimeError):
    """DejaVuSans fonts not found."""


class BookmarkFlowable(Flowable):
    """Invisible flowable — creates a PDF bookmark in the outline."""

    _last_level = -1  # class-var: tracks current outline level

    def __init__(self, title, level=0):
        super().__init__()
        self.title = title
        self.level = level
        self.width = 0
        self.height = 0
        self.keepWithNext = True

    def draw(self):
        key = f"bm_{id(self)}"
        self.canv.bookmarkPage(key)
        # ReportLab does not allow skipping levels (e.g. 1→3).
        # Cap level at most one above the previous.
        safe_level = min(self.level, BookmarkFlowable._last_level + 1)
        safe_level = max(safe_level, 0)
        self.canv.addOutlineEntry(self.title, key, level=safe_level)
        BookmarkFlowable._last_level = safe_level


class SectionTracker(Flowable):
    """Invisible flowable — updates the running header on draw()."""

    def __init__(self, section_text, attr="_running_header"):
        super().__init__()
        self.section_text = section_text
        self._attr = attr
        self.width = 0
        self.height = 0
        self.keepWithNext = True

    def draw(self):
        setattr(self.canv._doc, self._attr, self.section_text)


class AnchorFlowable(Flowable):
    """Invisible flowable — records current page number on draw()."""

    def __init__(self, anchor_name, page_tracker):
        super().__init__()
        self.anchor_name = anchor_name
        self.page_tracker = page_tracker
        self.width = 0
        self.height = 0
        self.keepWithNext = True

    def draw(self):
        self.page_tracker[self.anchor_name] = self.canv.getPageNumber()


class _FitPageStart(Flowable):
    """Sentinel: start of :::fit-page block."""

    def __init__(self, orientation="portrait"):
        super().__init__()
        self.orientation = orientation
        self.width = 0
        self.height = 0

    def draw(self):
        pass


class _FitPageEnd(Flowable):
    """Sentinel: end of :::fit-page block."""

    def __init__(self):
        super().__init__()
        self.width = 0
        self.height = 0

    def draw(self):
        pass


class _FitPageFlowable(Flowable):
    """Scales content to fit within max_w × max_h.

    Replacement for KeepInFrame(mode='shrink') with correct positioning:
    KeepInFrame mishandles _sW during scaling, which shifts content.

    Additionally: if after uniform height-based scaling there is
    leftover horizontal space, the content is stretched in width
    (up to 20% max) to better fill the page.
    """

    _MAX_STRETCH = 1.20  # maximum horizontal stretch

    def __init__(self, content, max_w, max_h):
        super().__init__()
        self._fitContent = content
        self._max_w = max_w
        self._max_h = max_h
        self._scale = 1.0
        self._stretch = 1.0  # additional horizontal stretch

    def wrap(self, availWidth, availHeight):
        # If the page already has content (a heading), shrink max_h
        # so that fit-page fits in the remaining space
        effective_max_h = min(self._max_h, availHeight)
        W, H = _listWrapOn(self._fitContent, self._max_w, self.canv)
        s = max(W / self._max_w, H / effective_max_h, 1.0)
        self._scale = s

        # Additional horizontal stretch:
        # after uniform scaling, visual_w = W/s may be < max_w.
        # Stretch horizontally to fill width (capped by limit).
        if s > 1.0:
            visual_w = W / s
            if visual_w < self._max_w:
                self._stretch = min(
                    self._max_w / max(visual_w, 1),  # fill width
                    self._MAX_STRETCH,                # stretch cap
                )
            else:
                self._stretch = 1.0
        else:
            self._stretch = 1.0

        self.width = self._max_w
        self.height = H / s
        return self.width, self.height

    def drawOn(self, canvas, x, y, _sW=0):
        canvas.saveState()
        s = self._scale
        stretch = self._stretch
        if s > 1.0:
            canvas.translate(x, y + self.height)
            canvas.scale(stretch / s, 1.0 / s)
            # Wrapper width in scaled coordinates:
            # visual_max_w * s / stretch = self._max_w * s / stretch
            wrap_w = self._max_w * s / stretch
            self._draw_content(canvas, x_off=0, y_top=0, wrap_w=wrap_w)
        else:
            self._draw_content(canvas, x_off=x, y_top=y + self.height,
                               wrap_w=self._max_w)
        canvas.restoreState()

    def _draw_content(self, canvas, x_off, y_top, wrap_w):
        """Draws child flowables top-down."""
        cur_y = y_top
        pS = 0
        for i, c in enumerate(self._fitContent):
            w, h = c.wrapOn(canvas, wrap_w, 0xFFFFFF)
            if h < 1e-6 and not getattr(c, "_ZEROSIZE", None):
                continue
            if i > 0:
                sb = c.getSpaceBefore()
                if not getattr(c, "_SPACETRANSFER", False):
                    gap = max(sb - pS, 0)
                else:
                    gap = 0
                cur_y -= gap
            cur_y -= h
            c.drawOn(canvas, x_off, cur_y, _sW=wrap_w - w)
            sa = c.getSpaceAfter()
            if getattr(c, "_SPACETRANSFER", False):
                sa = pS
            pS = sa
            if c is not self._fitContent[-1]:
                cur_y -= pS


# ══════════════════════════════════════════════════════════════════
# FONT REGISTRATION
# ══════════════════════════════════════════════════════════════════

def register_fonts(font_dir: str | None = None):
    """Finds and registers DejaVuSans fonts."""
    search_paths = []
    if font_dir:
        search_paths.append(font_dir)
    search_paths += [
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/dejavu",
        "/usr/local/share/fonts",
        os.path.expanduser("~/.fonts"),
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
        r"C:\Windows\Fonts",
    ]

    needed = {
        "DejaVu": "DejaVuSans.ttf",
        "DejaVuBd": "DejaVuSans-Bold.ttf",
        "DejaVuIt": "DejaVuSans-Oblique.ttf",
        "DejaVuBI": "DejaVuSans-BoldOblique.ttf",
        "DejaVuMono": "DejaVuSansMono.ttf",
        "DejaVuMonoBd": "DejaVuSansMono-Bold.ttf",
    }

    found_dir = None
    for d in search_paths:
        if os.path.isdir(d) and os.path.isfile(os.path.join(d, "DejaVuSans.ttf")):
            found_dir = d
            break

    if not found_dir:
        raise FontNotFoundError(
            "DejaVuSans fonts not found.\n"
            f"  Specify path via --font-dir\n"
            f"  Searched in: {search_paths}"
        )

    for name, filename in needed.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(found_dir, filename)))
    pdfmetrics.registerFontFamily(
        "DejaVu", normal="DejaVu", bold="DejaVuBd",
        italic="DejaVuIt", boldItalic="DejaVuBI",
    )


# ══════════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ══════════════════════════════════════════════════════════════════

class MdToken:
    """A single parsed Markdown token."""
    __slots__ = ("kind", "text", "level", "rows", "headers", "num",
                 "lang", "checked", "path", "alt", "alignments", "caption",
                 "width", "float_side", "admonition_type", "highlight_lines")

    def __init__(self, kind, text="", level=0, rows=None, headers=None,
                 num=0, lang="", checked=None, path="", alt="",
                 alignments=None, caption="", width=None, float_side="",
                 admonition_type="", highlight_lines=None):
        self.kind = kind
        self.text = text
        self.level = level
        self.rows = rows or []
        self.headers = headers or []
        self.num = num
        self.lang = lang          # language for code highlighting
        self.checked = checked    # None=not a checkbox, True/False=state
        self.path = path          # image path
        self.alt = alt            # image alt text
        self.alignments = alignments or []  # table column alignments
        self.caption = caption    # table caption
        self.width = width        # width in % (50 = 50%), None = auto
        self.float_side = float_side  # "left", "right", "" = block
        self.admonition_type = admonition_type  # note/warning/tip/important/caution
        self.highlight_lines = highlight_lines or []  # lines to highlight in code

    def __repr__(self):
        return f"MdToken({self.kind!r}, {self.text[:40]!r})"


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Extracts YAML front matter if present. Returns (metadata, remaining text)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    yaml_block = text[3:end].strip()
    rest = text[end + 4:]
    meta = {}
    for line in yaml_block.split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lower().replace("-", "_")
        val = val.strip().strip('"').strip("'")
        if val.lower() in ("true", "yes", "on"):
            val = True
        elif val.lower() in ("false", "no", "off"):
            val = False
        elif val.isdigit():
            val = int(val)
        meta[key] = val
    return meta, rest


def parse_markdown(text: str) -> tuple[str, list, list[MdToken], dict]:
    """
    Parses Markdown.
    Returns: (title, toc_items, tokens, footnote_defs)
    """
    raw_lines = text.split("\n")

    # Collect footnote definitions [^key]: text (multi-line support)
    footnote_defs: dict[str, str] = {}
    lines = []
    _last_fn_key = None
    for line in raw_lines:
        fn_m = re.match(r"^\[\^([\w.-]+)\]:\s*(.+)$", line.strip())
        if fn_m:
            _last_fn_key = fn_m.group(1)
            footnote_defs[_last_fn_key] = fn_m.group(2)
        elif _last_fn_key and line.startswith("    ") and line.strip():
            # Continuation of a multi-line footnote (4-space indent)
            footnote_defs[_last_fn_key] += " " + line.strip()
        else:
            _last_fn_key = None
            lines.append(line)

    tokens: list[MdToken] = []
    title = ""
    toc_items: list[str] = []
    i = 0
    skip_toc = False
    _directive_stack: list[str] = []  # stack of open directives (landscape, fit_page)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line — paragraph separator
        if not stripped:
            # Add a break marker for paragraph stitching
            if tokens and tokens[-1].kind == "body":
                tokens.append(MdToken("blank"))
            i += 1
            continue

        # Math block $$...$$
        if stripped.startswith("$$"):
            math_lines = []
            if stripped.endswith("$$") and len(stripped) > 4:
                # Single-line formula $$E=mc^2$$
                math_lines.append(stripped[2:-2])
                i += 1
            else:
                # Multi-line formula
                first = stripped[2:].strip()
                if first:
                    math_lines.append(first)
                i += 1
                while i < len(lines):
                    ml = lines[i].strip()
                    if ml.endswith("$$"):
                        tail = ml[:-2].strip()
                        if tail:
                            math_lines.append(tail)
                        i += 1
                        break
                    math_lines.append(ml)
                    i += 1
            tokens.append(MdToken("math", " ".join(math_lines).strip()))
            continue

        # Block directives: :::landscape, :::fit-page
        if stripped == ":::landscape":
            tokens.append(MdToken("landscape_start"))
            _directive_stack.append("landscape")
            i += 1
            continue

        if stripped == ":::fit-page":
            tokens.append(MdToken("fit_page_start"))
            _directive_stack.append("fit_page")
            i += 1
            continue

        if stripped == ":::" and _directive_stack:
            last = _directive_stack.pop()
            if last == "landscape":
                tokens.append(MdToken("landscape_end"))
            elif last == "fit_page":
                tokens.append(MdToken("fit_page_end"))
            i += 1
            continue

        # Multi-column block :::columns N
        col_match = re.match(r"^:::columns\s*(\d*)$", stripped)
        if col_match:
            num_cols = int(col_match.group(1)) if col_match.group(1) else 2
            col_lines = []
            i += 1
            while i < len(lines):
                if lines[i].strip() == ":::":
                    i += 1
                    break
                col_lines.append(lines[i])
                i += 1
            tokens.append(MdToken("columns", text="\n".join(col_lines), level=num_cols))
            continue

        # Code block (fenced) — capture language and {highlight=...}
        fence_m = re.match(r"^(`{3,}|~{3,})\s*(.*)", stripped)
        if fence_m:
            fence_marker = fence_m.group(1)[0]  # ` or ~
            fence_len = len(fence_m.group(1))
            meta = fence_m.group(2).strip()
            # Extract language and highlight
            hl_lines = []
            lang = ""
            hl_m = re.search(r'\{[^}]*highlight\s*=\s*"?([^}"]+)"?\s*[^}]*\}', meta)
            if hl_m:
                for part in hl_m.group(1).split(","):
                    part = part.strip()
                    if "-" in part:
                        a, b = part.split("-", 1)
                        hl_lines.extend(range(int(a), int(b) + 1))
                    elif part.isdigit():
                        hl_lines.append(int(part))
                meta = meta[:hl_m.start()] + meta[hl_m.end():]
            lang = meta.strip().lower()
            code_lines = []
            i += 1
            while i < len(lines):
                cl_stripped = lines[i].strip()
                # Closing fence: same char, >= same length, nothing after
                if (cl_stripped.startswith(fence_marker * fence_len)
                        and cl_stripped.rstrip(fence_marker) == ""):
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            if lang == "chart":
                tokens.append(MdToken("chart", "\n".join(code_lines)))
            else:
                tokens.append(MdToken("code", "\n".join(code_lines), lang=lang,
                                      highlight_lines=hl_lines))
            continue

        # --- (hr)
        if re.match(r"^[-*_]{3,}$", stripped):
            tokens.append(MdToken("hr"))
            i += 1
            continue

        # Explicit page break: \pagebreak or \newpage
        if stripped in (r"\pagebreak", r"\newpage"):
            tokens.append(MdToken("pagebreak"))
            i += 1
            continue

        # Escaped heading \# → body text
        if stripped.startswith("\\#"):
            clean = stripped[1:]
            if tokens and tokens[-1].kind == "body":
                tokens[-1].text += " " + clean
            else:
                tokens.append(MdToken("body", clean))
            i += 1
            continue

        # Image ![alt](path){width=50% float=right}
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)(?:\{([^}]+)\})?\s*$", stripped)
        if m:
            img_alt = m.group(1)
            img_path = m.group(2).strip()
            img_width = None
            img_float = ""
            if m.group(3):
                attrs = m.group(3)
                wm = re.search(r"width\s*=\s*(\d+)%", attrs)
                if wm:
                    img_width = int(wm.group(1))
                fm = re.search(r"float\s*=\s*(left|right)", attrs)
                if fm:
                    img_float = fm.group(1)
            tokens.append(MdToken("image", alt=img_alt, path=img_path,
                                   width=img_width, float_side=img_float))
            i += 1
            continue

        # "Contents" section — skip
        if stripped.lower() in ("[toc]",) or re.match(
            r"^##\s+Contents", stripped, re.IGNORECASE
        ):
            skip_toc = True
            i += 1
            continue

        # H1
        m = re.match(r"^#\s+(.+)", stripped)
        if m:
            skip_toc = False
            h1_text = m.group(1).strip()
            if not title:
                title = h1_text
            else:
                tokens.append(MdToken("h1", h1_text))
            i += 1
            continue

        # H2
        m = re.match(r"^##\s+(.+)", stripped)
        if m:
            skip_toc = False
            h2_text = m.group(1).strip()
            toc_items.append((2, h2_text))
            tokens.append(MdToken("h2", h2_text))
            i += 1
            continue

        # H3 / H4
        m = re.match(r"^(#{3,4})\s+(.+)", stripped)
        if m:
            skip_toc = False
            kind = "h3" if len(m.group(1)) == 3 else "h4"
            h_text = m.group(2).strip()
            toc_items.append((3 if kind == "h3" else 4, h_text))
            tokens.append(MdToken(kind, h_text))
            i += 1
            continue

        # Skip TOC lines
        if skip_toc:
            i += 1
            continue

        # Table
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            headers_list = []
            rows_list = []
            alignments = []
            def _split_table_row(row):
                """Splits a table row by | honoring the \\| escape."""
                row = row.strip().strip("|")
                # Replace \| with sentinel, split, restore
                row = row.replace("\\|", "\x00PIPE\x00")
                cells = [c.strip().replace("\x00PIPE\x00", "|") for c in row.split("|")]
                return cells
            for tl in table_lines:
                cells = _split_table_row(tl)
                if all(re.match(r"^:?-+:?$", c) for c in cells):
                    # Extract alignment
                    for c in cells:
                        if c.startswith(":") and c.endswith(":"):
                            alignments.append("center")
                        elif c.endswith(":"):
                            alignments.append("right")
                        else:
                            alignments.append("left")
                    continue
                if not headers_list:
                    headers_list = cells
                else:
                    rows_list.append(cells)
            # Table caption from previous body token
            caption = ""
            if tokens and tokens[-1].kind == "body":
                cap_m = re.match(
                    r"^Table\s*\d*\s*[.:]\s*(.+)$",
                    tokens[-1].text, re.IGNORECASE,
                )
                if cap_m:
                    caption = tokens[-1].text
                    tokens.pop()
            if headers_list:
                tokens.append(MdToken("table", headers=headers_list,
                                      rows=rows_list, alignments=alignments,
                                      caption=caption))
            continue

        # Quote / Admonition (> [!NOTE], > [!WARNING], > [!TIP], > [!IMPORTANT], > [!CAUTION])
        if stripped.startswith("> ") or stripped == ">":
            quote_lines = []
            while i < len(lines) and (
                lines[i].strip().startswith(">")
            ):
                txt = lines[i].strip()
                txt = txt[2:] if txt.startswith("> ") else txt[1:]
                quote_lines.append(txt)
                i += 1
            full_text = " ".join(quote_lines).strip()
            # Check callout syntax: [!NOTE], [!WARNING], etc.
            adm_m = re.match(r"^\[!(NOTE|WARNING|TIP|IMPORTANT|CAUTION)\]\s*(.*)",
                             full_text, re.IGNORECASE)
            if adm_m:
                adm_type = adm_m.group(1).lower()
                adm_text = adm_m.group(2).strip()
                tokens.append(MdToken("admonition", adm_text,
                                      admonition_type=adm_type))
            else:
                tokens.append(MdToken("quote", full_text))
            continue

        # Checkboxes - [ ] / - [x]
        m = re.match(r"^(\s*)[-*]\s+\[([ xX])\]\s+(.+)", line)
        if m:
            indent = len(m.group(1))
            level = min(indent // 2, 3)
            is_checked = m.group(2).lower() == "x"
            tokens.append(MdToken("checkbox", m.group(3).strip(),
                                  level=level, checked=is_checked))
            i += 1
            continue

        # Bulleted list (up to 4 nesting levels)
        m = re.match(r"^(\s*)([-*●○▪▸])\s+(.+)", line)
        if m:
            indent = len(m.group(1))
            level = min(indent // 2, 3)
            tokens.append(MdToken("bullet", m.group(3).strip(), level=level))
            i += 1
            continue

        # Numbered list (with nesting via indent)
        m = re.match(r"^(\s*)(\d+)[.)]\s+(.+)", line)
        if m:
            indent = len(m.group(1))
            level = min(indent // 3, 3)
            tokens.append(MdToken("numbered", m.group(3).strip(),
                                  num=int(m.group(2)), level=level))
            i += 1
            continue

        # Definition list: : definition (after a body token)
        if stripped.startswith(": ") and tokens and tokens[-1].kind == "body":
            term = tokens.pop().text
            definition = stripped[2:].strip()
            tokens.append(MdToken("definition", definition, alt=term))
            i += 1
            continue

        # Plain text — stitch consecutive lines into one paragraph
        if tokens and tokens[-1].kind == "body":
            tokens[-1].text += " " + stripped
        else:
            tokens.append(MdToken("body", stripped))
        i += 1

    # Warn about unclosed directives
    if _directive_stack:
        for d in _directive_stack:
            _log.warning("Unclosed directive :::%s — add ::: to close", d)
            if d == "landscape":
                tokens.append(MdToken("landscape_end"))
            elif d == "fit_page":
                tokens.append(MdToken("fit_page_end"))

    # Drop auxiliary blank tokens
    tokens = [t for t in tokens if t.kind != "blank"]

    # Append footnotes section if any
    if footnote_defs:
        tokens.append(MdToken("footnotes"))

    return title, toc_items, tokens, footnote_defs


# ══════════════════════════════════════════════════════════════════
# CHART HELPERS
# ══════════════════════════════════════════════════════════════════

def _parse_chart_spec(text):
    """Parses YAML-like content of a ```chart block → dict.

    Returns a dict with keys:
        chart_type: 'pie' | 'bar' | 'line' | 'area'
        title: str | None
        labels: list[str]          — X-axis labels (bar/line/area)
        series: list[(name, values)]  — series data
        show_legend: bool
        size: 'standard' | 'wide' | 'small'
        colors: list[str] | None   — custom colors
    """
    spec = {
        "chart_type": "bar",
        "title": None,
        "labels": [],
        "series": [],
        "show_legend": True,
        "size": "standard",
        "colors": None,
    }
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Directives
        if line.lower().startswith("type:"):
            spec["chart_type"] = line.split(":", 1)[1].strip().lower()
        elif line.lower().startswith("title:"):
            spec["title"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("labels:"):
            spec["labels"] = [l.strip() for l in line.split(":", 1)[1].split(",")]
        elif line.lower().startswith("legend:"):
            val = line.split(":", 1)[1].strip().lower()
            spec["show_legend"] = val not in ("false", "no", "0")
        elif line.lower().startswith("size:"):
            spec["size"] = line.split(":", 1)[1].strip().lower()
        elif line.lower().startswith("colors:"):
            spec["colors"] = [c.strip() for c in line.split(":", 1)[1].split(",")]
        else:
            # Data line: "Name: value[, value, ...]"
            if ":" in line:
                name, vals_str = line.split(":", 1)
                name = name.strip()
                try:
                    vals = [float(v.strip()) for v in vals_str.split(",")]
                    spec["series"].append((name, vals))
                except ValueError:
                    pass
    return spec


def _lighten(hex_color, factor=0.4):
    """Lightens a hex color (#RRGGBB) by factor (0..1). Returns a hex string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02X}{g:02X}{b:02X}"


def _render_chart_png(spec, palette, font_path=None):
    """Renders a chart to PNG bytes via matplotlib.

    Args:
        spec: dict from _parse_chart_spec()
        palette: list[str] — hex colors ('#RRGGBB')
        font_path: path to TTF font for non-ASCII glyphs (optional)
    Returns:
        bytes (PNG) or None if matplotlib is not available.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError:
        return None

    import io

    # Font setup for non-ASCII glyphs
    if font_path and os.path.isfile(font_path):
        try:
            font_prop = font_manager.FontProperties(fname=font_path)
            plt.rcParams["font.family"] = font_prop.get_name()
            font_manager.fontManager.addfont(font_path)
        except Exception as exc:
            _log.warning("Could not load font for chart: %s", exc)
            font_prop = None
    else:
        font_prop = None

    # Colors: custom or from theme palette
    colors = spec["colors"] if spec["colors"] else palette
    chart_type = spec["chart_type"]

    # Figure size
    if spec["size"] == "wide":
        fig_w, fig_h = 10, 5
    elif spec["size"] == "small":
        fig_w, fig_h = 5, 4
    else:
        fig_w, fig_h = 7.5, 4.5

    # ── Dynamic font-size selection ──
    # Base sizes scale with figure width
    _scale = fig_w / 7.5
    _title_size = max(10, min(15, 13 * _scale))
    _tick_size = max(7, min(11, 9.5 * _scale))
    _legend_size = max(7, min(10, 9 * _scale))

    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)

    if chart_type == "pie":
        # Pie: series — list of (name, [value])
        labels = [s[0] for s in spec["series"]]
        values = [s[1][0] if s[1] else 0 for s in spec["series"]]
        pie_colors = [colors[i % len(colors)] for i in range(len(values))]

        n_slices = len(values)
        max_label_len = max((len(l) for l in labels), default=0)

        # Strategy: with ≤3 short labels — draw labels directly on the pie.
        # Otherwise — move labels into the legend so they don't overlap.
        _use_legend = n_slices > 3 or max_label_len > 14

        if _use_legend:
            # Names in the legend, percentages — on pie with adaptive size
            import math
            total = sum(values) or 1
            _pct_base = max(7, min(10, _tick_size * 0.85))

            wedges, texts, autotexts = ax.pie(
                values, labels=None, autopct="%1.1f%%",
                colors=pie_colors, startangle=90,
                pctdistance=0.6,
                textprops={"fontproperties": font_prop} if font_prop else {},
            )
            # Post-process: per-% font size and position by slice share
            for i, t in enumerate(autotexts):
                pct = values[i] / total * 100 if i < len(values) else 0
                if pct < 2:
                    # Too small a slice — hide text
                    t.set_text("")
                else:
                    # Size: linear interpolation by slice share
                    # 25%+ → full size, 3% → 45% of base
                    ratio = min(1.0, max(0.45, pct / 25.0))
                    t.set_fontsize(_pct_base * ratio)
                    if font_prop:
                        t.set_fontproperties(font_prop)
                    # Small slices (<8%) — push % outward
                    if pct < 8:
                        x0, y0 = t.get_position()
                        dist = math.hypot(x0, y0)
                        if dist > 0:
                            push = 1.15 / dist if pct >= 4 else 1.3 / dist
                            t.set_position((x0 * push, y0 * push))

            # Legend with slice names
            _leg_labels = [f"{l} ({v:g})" for l, v in zip(labels, values)]
            _leg_font_size = max(6.5, min(9, _legend_size * 0.9))
            _leg_kw = {"prop": font_prop, "fontsize": _leg_font_size} if font_prop else {"fontsize": _leg_font_size}
            ax.legend(wedges, _leg_labels,
                      loc="center left", bbox_to_anchor=(1.0, 0.5),
                      framealpha=0.9, edgecolor="#cccccc", **_leg_kw)
        else:
            # Few slices — labels drawn on the pie itself
            _pie_label_size = max(8, min(11, _tick_size))
            _pie_pct_size = max(7, min(10, _tick_size * 0.9))
            _text_kw = {"fontproperties": font_prop, "fontsize": _pie_label_size} if font_prop else {"fontsize": _pie_label_size}
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct="%1.1f%%",
                colors=pie_colors, startangle=90,
                labeldistance=1.15, pctdistance=0.55,
                textprops=_text_kw,
            )
            for t in autotexts:
                t.set_fontsize(_pie_pct_size)
                if font_prop:
                    t.set_fontproperties(font_prop)
            if font_prop:
                for t in texts:
                    t.set_fontproperties(font_prop)
        ax.set_aspect("equal")

    elif chart_type in ("bar", "line", "area"):
        labels = spec["labels"]
        series = spec["series"]
        n_groups = max(len(labels), max((len(s[1]) for s in series), default=0)) if series else 0
        # If labels not set — generate from indices
        if not labels:
            labels = [str(i + 1) for i in range(n_groups)]
        elif len(labels) < n_groups:
            labels += [str(i + 1) for i in range(len(labels), n_groups)]

        x = list(range(n_groups))

        # Decide whether X-axis labels need rotation
        max_label_len = max((len(l) for l in labels), default=0)
        total_label_chars = sum(len(l) for l in labels)
        # Character density: total characters per inch of width
        _char_density = total_label_chars / fig_w if fig_w > 0 else 0

        if n_groups > 8 or _char_density > 8 or (max_label_len > 6 and n_groups > 4):
            _x_rotation = 45
            _x_ha = "right"
            _x_label_size = max(6, _tick_size * 0.85)
        elif max_label_len > 10 or _char_density > 5:
            _x_rotation = 30
            _x_ha = "right"
            _x_label_size = max(7, _tick_size * 0.9)
        else:
            _x_rotation = 0
            _x_ha = "center"
            _x_label_size = _tick_size

        if chart_type == "bar":
            n_series = len(series)
            if n_series == 0:
                n_series = 1
            bar_w = 0.8 / n_series
            for si, (name, vals) in enumerate(series):
                # Pad with zeros if fewer values than groups
                while len(vals) < n_groups:
                    vals.append(0)
                offsets = [xi - 0.4 + bar_w * si + bar_w / 2 for xi in x]
                color = colors[si % len(colors)]
                ax.bar(offsets, vals[:n_groups], bar_w, label=name, color=color)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, fontproperties=font_prop,
                               fontsize=_x_label_size,
                               rotation=_x_rotation, ha=_x_ha)

        elif chart_type in ("line", "area"):
            for si, (name, vals) in enumerate(series):
                while len(vals) < n_groups:
                    vals.append(0)
                color = colors[si % len(colors)]
                ax.plot(x, vals[:n_groups], marker="o", label=name, color=color,
                        linewidth=2, markersize=4)
                if chart_type == "area":
                    ax.fill_between(x, vals[:n_groups], alpha=0.2, color=color)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, fontproperties=font_prop,
                               fontsize=_x_label_size,
                               rotation=_x_rotation, ha=_x_ha)

        # Y-axis label size
        ax.tick_params(axis='y', labelsize=_tick_size)

        # Legend — place outside the plot area to avoid data overlap
        if spec["show_legend"] and len(series) > 1:
            _leg_prop = font_prop if font_prop else {}
            legend = ax.legend(prop=_leg_prop, fontsize=_legend_size,
                               loc="best", framealpha=0.9, edgecolor="#cccccc")

        # Hide top/right spines
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # Title
    if spec["title"]:
        ax.set_title(spec["title"], fontproperties=font_prop,
                     fontsize=_title_size, pad=10)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# STEGANOGRAPHY
# ══════════════════════════════════════════════════════════════════

def _embed_stego_lsb(png_bytes, message):
    """Embeds text into the LSB of the red channel of a PNG image."""
    try:
        from PIL import Image
        import io as _io
    except ImportError:
        return png_bytes
    data = message.encode("utf-8")
    payload = struct.pack(">I", len(data)) + data
    bits = []
    for byte in payload:
        for bit_pos in range(7, -1, -1):
            bits.append((byte >> bit_pos) & 1)
    try:
        img = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        return png_bytes
    pixels = list(img.getdata())
    if len(bits) > len(pixels):
        return png_bytes
    new_pixels = []
    for i, (r, g, b, a) in enumerate(pixels):
        if i < len(bits):
            r = (r & 0xFE) | bits[i]
        new_pixels.append((r, g, b, a))
    img.putdata(new_pixels)
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _extract_stego_lsb(png_bytes):
    """Extracts text from the LSB of the red channel of a PNG."""
    try:
        from PIL import Image
        import io as _io
    except ImportError:
        return None
    try:
        img = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
    except Exception:
        return None
    pixels = list(img.getdata())
    if len(pixels) < 32:
        return None
    # Read 32 bits of length
    length = 0
    for i in range(32):
        length = (length << 1) | (pixels[i][0] & 1)
    if length <= 0 or length > 10000:
        return None
    total_bits = (4 + length) * 8
    if total_bits > len(pixels):
        return None
    byte_array = bytearray()
    for j in range(4, 4 + length):
        byte_val = 0
        for k in range(8):
            byte_val = (byte_val << 1) | (pixels[j * 8 + k][0] & 1)
        byte_array.append(byte_val)
    try:
        return byte_array.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


def _make_canvas_factory(custom_meta):
    """Creates a Canvas factory that injects custom metadata into the PDF."""
    from reportlab.pdfgen.canvas import Canvas as _Canvas
    from reportlab.pdfbase.pdfdoc import PDFString, PDFDictionary, PDFDate, PDFName, PDFInfo
    _orig_format = PDFInfo.format
    class _MetadataCanvas(_Canvas):
        def save(self):
            if hasattr(self, '_doc') and hasattr(self._doc, 'info'):
                info = self._doc.info
                orig_fmt = info.__class__.format
                def _patched_format(self_info, document):
                    # Build the standard dictionary
                    D = {}
                    D["Title"] = PDFString(self_info.title)
                    D["Author"] = PDFString(self_info.author)
                    D['ModDate'] = D["CreationDate"] = PDFDate(
                        ts=document._timeStamp, dateFormatter=self_info._dateFormatter)
                    D["Producer"] = PDFString(self_info.producer)
                    D["Creator"] = PDFString(self_info.creator)
                    D["Subject"] = PDFString(self_info.subject)
                    D["Keywords"] = PDFString(self_info.keywords)
                    D["Trapped"] = PDFName(self_info.trapped)
                    # Add custom fields
                    for k, v in custom_meta.items():
                        D[k] = PDFString(v)
                    return PDFDictionary(D).format(document)
                info.format = lambda doc: _patched_format(info, doc)
            super().save()
    return _MetadataCanvas


# ══════════════════════════════════════════════════════════════════
# PDF RENDERER
# ══════════════════════════════════════════════════════════════════

class StudyGuidePDF:
    """Renderer: tokens → PDF."""

    def __init__(self, theme_name="teal", show_cover=True, show_toc=True,
                 watermark="", subtitle="Tutorial", author="",
                 duplex=False, cover_image=None, toc_depth=2,
                 page_size="a4", justify=True, code_line_numbers=True,
                 margins="medium", h2_break="always",
                 chapter_page=False, copy_id=False, show_qr=False,
                 cover_author=True, cover_pattern="circles"):
        theme = THEMES.get(theme_name, THEMES["teal"])
        self.show_cover = show_cover
        self.show_toc = show_toc
        self.toc_depth = toc_depth
        self.page_size = PAGE_SIZES.get(page_size.lower(), A4)
        self._landscape_size = landscape(self.page_size)
        self._current_orientation = "portrait"
        self._justify = justify
        self._code_line_numbers = code_line_numbers
        self._h2_break = h2_break  # "always" | "auto" | "never"
        self._chapter_page = chapter_page
        mt, mb, ml, mr = MARGIN_PRESETS.get(margins, MARGIN_PRESETS["medium"])
        self._margins = (mt * mm, mb * mm, ml * mm, mr * mm)
        self.watermark = watermark
        self.subtitle = subtitle
        self._author = author
        self._cover_author = cover_author
        self._cover_pattern = cover_pattern  # circles | diamonds | lines | dots | none
        self.duplex = duplex
        self._cover_image = cover_image
        # Authorship
        self._copy_id_show = copy_id
        self._show_qr = show_qr
        self._copy_uuid = str(uuid.uuid4())
        self._fingerprint_date = date.today().isoformat()
        self._md_hash = ""
        self._qr_cache = None

        self.PRIMARY = HexColor(theme["primary"])
        self.PRIMARY_LIGHT = HexColor(theme["primary_light"])
        self.SECONDARY = HexColor(theme["secondary"])
        self.ACCENT = HexColor(theme["accent"])
        self.TABLE_ALT = HexColor(theme["table_alt"])
        self.BORDER = HexColor(theme["border"])
        self.COVER_CIRCLES = [HexColor(c) for c in theme["cover_circles"]]
        self.COVER_SUB = HexColor(theme["cover_sub"])

        self._section_counter = 0
        self._build_styles()

    def _build_styles(self):
        P, S = self.PRIMARY, self.SECONDARY
        self.S = {
            "h1": ParagraphStyle(
                "H1", fontName="DejaVuBd", fontSize=18, leading=24,
                textColor=P, spaceAfter=5 * mm, spaceBefore=2 * mm,
                keepWithNext=1,
            ),
            "h2": ParagraphStyle(
                "H2", fontName="DejaVuBd", fontSize=13, leading=17,
                textColor=P, spaceAfter=3 * mm, spaceBefore=4 * mm,
                keepWithNext=1,
            ),
            "h3": ParagraphStyle(
                "H3", fontName="DejaVuBd", fontSize=11, leading=15,
                textColor=S, spaceAfter=2 * mm, spaceBefore=3 * mm,
                keepWithNext=1,
            ),
            "h4": ParagraphStyle(
                "H4", fontName="DejaVuBd", fontSize=10, leading=13.5,
                textColor=S, spaceAfter=1.5 * mm, spaceBefore=2.5 * mm,
                keepWithNext=1,
            ),
            "body": ParagraphStyle(
                "Body", fontName="DejaVu", fontSize=9, leading=13,
                textColor=DARK_TEXT, spaceAfter=1.5 * mm,
                alignment=TA_JUSTIFY if self._justify else TA_LEFT,
            ),
            "bullet": ParagraphStyle(
                "Bullet", fontName="DejaVu", fontSize=9, leading=12.5,
                textColor=DARK_TEXT, spaceAfter=1 * mm,
                leftIndent=12, bulletIndent=0,
            ),
            "sub_bullet": ParagraphStyle(
                "SubBullet", fontName="DejaVu", fontSize=8.5, leading=12,
                textColor=MEDIUM_TEXT, spaceAfter=1 * mm,
                leftIndent=24, bulletIndent=12,
            ),
            "bullet_l2": ParagraphStyle(
                "BulletL2", fontName="DejaVu", fontSize=8.5, leading=12,
                textColor=MEDIUM_TEXT, spaceAfter=1 * mm,
                leftIndent=36, bulletIndent=24,
            ),
            "bullet_l3": ParagraphStyle(
                "BulletL3", fontName="DejaVu", fontSize=8, leading=11.5,
                textColor=MEDIUM_TEXT, spaceAfter=0.8 * mm,
                leftIndent=48, bulletIndent=36,
            ),
            "quote": ParagraphStyle(
                "Quote", fontName="DejaVuBd", fontSize=9, leading=13,
                textColor=P, leftIndent=15,
            ),
            "toc": ParagraphStyle(
                "TOC", fontName="DejaVu", fontSize=10.5, leading=20,
                textColor=DARK_TEXT, leftIndent=5,
            ),
            "code": ParagraphStyle(
                "Code", fontName="DejaVuMono", fontSize=7.5, leading=10.5,
                textColor=DARK_TEXT, leftIndent=6, rightIndent=6,
            ),
            "code_nums": ParagraphStyle(
                "CodeNums", fontName="DejaVuMono", fontSize=7.5, leading=10.5,
                textColor=HexColor("#AAAAAA"), alignment=TA_RIGHT,
            ),
            "caption": ParagraphStyle(
                "Caption", fontName="DejaVu", fontSize=8, leading=11,
                textColor=MEDIUM_TEXT, alignment=TA_CENTER,
                spaceBefore=2 * mm, spaceAfter=3 * mm,
            ),
            "math": ParagraphStyle(
                "Math", fontName="DejaVu", fontSize=11, leading=16,
                textColor=DARK_TEXT, alignment=TA_CENTER,
                spaceBefore=3 * mm, spaceAfter=3 * mm,
            ),
            "footnote": ParagraphStyle(
                "Footnote", fontName="DejaVu", fontSize=7.5, leading=10.5,
                textColor=MEDIUM_TEXT, leftIndent=12, spaceAfter=1 * mm,
            ),
        }

    # ── Markdown → ReportLab XML ──

    # Markers and styles for list levels
    _BULLET_MARKERS = ["●  ", "○  ", "▪  ", "▸  "]
    _BULLET_STYLES = ["bullet", "sub_bullet", "bullet_l2", "bullet_l3"]

    # Sentinel pairs for escaping Markdown characters
    _ESCAPE_MAP = [
        ("\\\\", "\x00BSLASH\x00"),
        ("\\*", "\x00STAR\x00"),
        ("\\#", "\x00HASH\x00"),
        ("\\`", "\x00TICK\x00"),
        ("\\[", "\x00LBRA\x00"),
        ("\\]", "\x00RBRA\x00"),
        ("\\~", "\x00TILDE\x00"),
        ("\\^", "\x00CARET\x00"),
    ]
    _RESTORE_MAP = [
        ("\x00BSLASH\x00", "\\"),
        ("\x00STAR\x00", "*"),
        ("\x00HASH\x00", "#"),
        ("\x00TICK\x00", "`"),
        ("\x00LBRA\x00", "["),
        ("\x00RBRA\x00", "]"),
        ("\x00TILDE\x00", "~"),
        ("\x00CARET\x00", "^"),
    ]

    def _fmt(self, text: str) -> str:
        """Formats inline Markdown → ReportLab XML."""
        # Escape: \* \# \` \[ \] \\ → sentinel
        for esc, sentinel in self._ESCAPE_MAP:
            text = text.replace(esc, sentinel)

        # First protect & from double-escaping
        text = text.replace("&", "&amp;")
        # Inline code: `code` → <font ...>
        text = re.sub(
            r"`([^`]+)`",
            r'<font face="DejaVuMono" color="#C7254E" backColor="#F9F2F4">\1</font>',
            text,
        )
        # Strikethrough: ~~strikethrough~~
        text = re.sub(r"~~(.+?)~~", r"<strike>\1</strike>", text)
        # Subscript: H~2~O → H<sub>2</sub>O (no spaces inside)
        text = re.sub(r"~([^~\s]+)~", r"<sub>\1</sub>", text)
        # Superscript: m^2^ → m<super>2</super> (no spaces inside)
        text = re.sub(r"\^([^^\s]+)\^", r"<super>\1</super>", text)
        # Bold italic: ***bold italic***
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<b><i>\1</i></b>", text)
        # Bold: **bold**
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Italic: *italic* (no conflict — ** already replaced)
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
        # Links: [text](url)
        link_color = self.PRIMARY.hexval()
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            rf'<a href="\2" color="{link_color}"><u>\1</u></a>',
            text,
        )
        # Inline formulas: $E=mc^2$
        text = re.sub(r"\$([^$]+)\$", lambda m: self._math(m.group(1)), text)

        # Footnotes: [^key] → superscript number
        def _fn_replace(m):
            key = m.group(1)
            if key in self._footnote_defs:
                if key not in self._footnote_order:
                    self._footnote_order.append(key)
                num = self._footnote_order.index(key) + 1
                c = self.PRIMARY.hexval()
                return f'<super><font color="{c}" size="7">{num}</font></super>'
            return m.group(0)
        text = re.sub(r"\[\^([\w.-]+)\]", _fn_replace, text)

        # Escape < that are not our tags
        text = re.sub(
            r"<(?!/?(b|i|u|a|sub|super|font|br|strike)\b)", "&lt;", text
        )

        # Fix crossed tag nesting (e.g. <b><i>...</b></i> → <b><i>...</i></b>)
        text = self._fix_crossed_tags(text)

        # Restore escaped chars from sentinels
        for sentinel, char in self._RESTORE_MAP:
            text = text.replace(sentinel, char)

        return text

    @staticmethod
    def _fix_crossed_tags(text: str) -> str:
        """Fixes crossed XML tags for ReportLab.

        Example: <b>text <i>more</b> end</i> → <b>text <i>more</i></b><i> end</i>
        """
        _SIMPLE_TAGS = {"b", "i", "u", "strike", "sub", "super"}
        _OPEN = re.compile(r"<(" + "|".join(_SIMPLE_TAGS) + r")>")
        _CLOSE = re.compile(r"</(" + "|".join(_SIMPLE_TAGS) + r")>")

        # Collect all tags with positions
        events = []
        for m in _OPEN.finditer(text):
            events.append((m.start(), m.end(), "open", m.group(1)))
        for m in _CLOSE.finditer(text):
            events.append((m.start(), m.end(), "close", m.group(1)))
        if not events:
            return text
        events.sort(key=lambda x: x[0])

        # Check stack validity
        stack = []
        need_fix = False
        for _, _, kind, tag in events:
            if kind == "open":
                stack.append(tag)
            else:
                if stack and stack[-1] == tag:
                    stack.pop()
                else:
                    need_fix = True
                    break
        if not need_fix:
            return text

        # Rough fix: close/reopen tags in the right order
        stack = []
        result = []
        pos = 0
        for start, end, kind, tag in events:
            result.append(text[pos:start])
            pos = end
            if kind == "open":
                stack.append(tag)
                result.append(f"<{tag}>")
            else:
                if tag in stack:
                    # Close everything from the top down to the desired tag
                    to_reopen = []
                    while stack and stack[-1] != tag:
                        t = stack.pop()
                        result.append(f"</{t}>")
                        to_reopen.append(t)
                    if stack:
                        stack.pop()
                        result.append(f"</{tag}>")
                    # Reopen
                    for t in reversed(to_reopen):
                        result.append(f"<{t}>")
                        stack.append(t)
                else:
                    # Extra closing tag — skip
                    pass
        result.append(text[pos:])
        # Close any unclosed tags
        for t in reversed(stack):
            result.append(f"</{t}>")
        return "".join(result)

    # ── Math formulas ──

    _GREEK = {
        "alpha": "\u03b1", "beta": "\u03b2", "gamma": "\u03b3", "delta": "\u03b4",
        "epsilon": "\u03b5", "zeta": "\u03b6", "eta": "\u03b7", "theta": "\u03b8",
        "iota": "\u03b9", "kappa": "\u03ba", "lambda": "\u03bb", "mu": "\u03bc",
        "nu": "\u03bd", "xi": "\u03be", "pi": "\u03c0", "rho": "\u03c1",
        "sigma": "\u03c3", "tau": "\u03c4", "phi": "\u03c6", "chi": "\u03c7",
        "psi": "\u03c8", "omega": "\u03c9",
        "Alpha": "\u0391", "Beta": "\u0392", "Gamma": "\u0393", "Delta": "\u0394",
        "Sigma": "\u03a3", "Omega": "\u03a9", "Pi": "\u03a0", "Phi": "\u03a6",
    }
    _MATH_SYMBOLS = {
        "pm": "\u00b1", "mp": "\u2213", "times": "\u00d7", "cdot": "\u00b7",
        "leq": "\u2264", "geq": "\u2265", "ne": "\u2260", "approx": "\u2248",
        "infty": "\u221e", "to": "\u2192", "leftarrow": "\u2190",
        "rightarrow": "\u2192", "sum": "\u2211", "prod": "\u220f",
        "int": "\u222b", "partial": "\u2202", "nabla": "\u2207",
        "sqrt": "\u221a", "degree": "\u00b0",
    }

    def _math(self, expr: str) -> str:
        """Converts a LaTeX-like formula into ReportLab XML + Unicode."""
        # Greek letters
        for name, char in self._GREEK.items():
            expr = expr.replace(f"\\{name}", char)
        # Symbols
        for name, char in self._MATH_SYMBOLS.items():
            expr = expr.replace(f"\\{name}", char)
        # \frac{a}{b} → <super>a</super>/<sub>b</sub>
        expr = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}",
                       '<super>\\1</super>\u2044<sub>\\2</sub>', expr)
        # Superscript with braces: x^{2+n}
        expr = re.sub(r"\^\{([^}]+)\}", r"<super>\1</super>", expr)
        # Subscript with braces: H_{2}O
        expr = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", expr)
        # Single char: x^2, H_2
        expr = re.sub(r"\^(\w)", r"<super>\1</super>", expr)
        expr = re.sub(r"_(\w)", r"<sub>\1</sub>", expr)
        return expr

    # Backward compatibility
    _b = _fmt

    # ── Flowable constructors ──

    def _content_width(self):
        """Available content width (accounting for margins, orientation and small slack)."""
        _, _, ml, mr = self._margins
        if getattr(self, '_current_orientation', 'portrait') == 'landscape':
            lw, _ = self._landscape_size
            return lw - ml - mr - 2 * mm
        pw, _ = self.page_size
        return pw - ml - mr - 2 * mm

    def _sp(self, h=2):
        return Spacer(1, h * mm)

    def _body(self, text):
        return Paragraph(self._fmt(text), self.S["body"])

    def _bullet(self, text, level=0):
        text = self._fmt(text)
        level = min(level, 3)
        prefix = self._BULLET_MARKERS[level]
        s = self.S[self._BULLET_STYLES[level]]
        return Paragraph(prefix + text, s)

    def _checkbox(self, text, checked=False, level=0):
        prefix = "☑  " if checked else "☐  "
        text = self._fmt(text)
        level = min(level, 3)
        s = self.S[self._BULLET_STYLES[level]]
        return Paragraph(prefix + text, s)

    @staticmethod
    def _resolve_image_path(path, md_dir, image_dir=None):
        """Looks up an image file across a chain of directories.

        Priority:
        1. Absolute path → as is
        2. Relative to md_dir (current behavior)
        3. Directly in image_dir/<basename>
        4. Recursively in image_dir/**/<basename>
        """
        if os.path.isabs(path):
            return path
        # Relative to the .md file directory
        candidate = os.path.join(md_dir, path)
        if os.path.isfile(candidate):
            return candidate
        # Look up in image_dir
        if image_dir:
            basename = os.path.basename(path)
            # Directly in image_dir
            candidate = os.path.join(image_dir, basename)
            if os.path.isfile(candidate):
                return candidate
            # Recursively in image_dir subfolders
            for root, _dirs, files in os.walk(image_dir):
                if basename in files:
                    return os.path.join(root, basename)
        # Not found — return original relative path (for error messaging)
        return os.path.join(md_dir, path)

    def _image(self, path, alt, md_dir, width_pct=None, float_side=""):
        """Inserts an image with scaling, caption and float wrap.

        Args:
            width_pct: Width as % of content area (50 = 50%), None = auto.
            float_side: "left"/"right" for wrap, "" for block.
        Returns:
            Block: flowable. Float: tuple ("float", flowable, side).
        """
        from reportlab.platypus import Image as RLImage
        path = self._resolve_image_path(path, md_dir, self._image_dir)
        if not os.path.isfile(path):
            placeholder = f"[Image not found: {alt or path}]"
            return Paragraph(
                f'<i><font color="#999999">{placeholder}</font></i>',
                self.S["body"],
            )
        max_w = self._content_width()
        if getattr(self, '_current_orientation', 'portrait') == 'landscape':
            _, cur_h = self._landscape_size
        else:
            cur_h = H
        max_h = cur_h - 100 * mm
        try:
            img = RLImage(path)
            iw, ih = img.imageWidth, img.imageHeight
            if iw > 0 and ih > 0:
                if width_pct is not None:
                    target_w = min(max_w * width_pct / 100.0, max_w)
                    ratio = target_w / iw
                    if ih * ratio > max_h:
                        ratio = max_h / ih
                else:
                    ratio = min(max_w / iw, max_h / ih, 1.0)
                img.drawWidth = iw * ratio
                img.drawHeight = ih * ratio

            if float_side:
                # Float: image on one side, text wraps around
                # ImageAndFlowables expects raw Image, not KeepTogether
                img.hAlign = "LEFT" if float_side == "left" else "RIGHT"
                cap = None
                if alt and alt.strip():
                    cap = Paragraph(self._fmt(alt), self.S["caption"])
                return ("float", img, float_side, cap)
            else:
                # Block (current behavior)
                img.hAlign = "CENTER"
                if alt and alt.strip():
                    cap = Paragraph(self._fmt(alt), self.S["caption"])
                    return KeepTogether([img, cap])
                return img
        except Exception:
            placeholder = f"[Load error: {alt or path}]"
            return Paragraph(
                f'<i><font color="#999999">{placeholder}</font></i>',
                self.S["body"],
            )

    def _chart(self, text):
        """Renders a ```chart block into a chart image."""
        from reportlab.platypus import Image as RLImage
        import io as _io
        spec = _parse_chart_spec(text)
        # Build palette from theme colors
        c = self.PRIMARY
        p1 = '#%02X%02X%02X' % (int(c.red * 255), int(c.green * 255), int(c.blue * 255))
        c = self.SECONDARY
        p2 = '#%02X%02X%02X' % (int(c.red * 255), int(c.green * 255), int(c.blue * 255))
        c = self.ACCENT
        p3 = '#%02X%02X%02X' % (int(c.red * 255), int(c.green * 255), int(c.blue * 255))
        palette = [p1, p2, p3, _lighten(p1), _lighten(p2), _lighten(p3),
                   _lighten(p1, 0.6), _lighten(p2, 0.6), _lighten(p3, 0.6)]
        # Look up font for non-ASCII glyphs
        try:
            font_path = pdfmetrics.getFont("DejaVu").face.filename
        except Exception:
            font_path = None
        png = _render_chart_png(spec, palette, font_path)
        if png is not None and self._author:
            png = _embed_stego_lsb(png, self._author)
        if png is None:
            return Paragraph(
                '<i><font color="#999999">[Chart: install matplotlib — '
                'pip install matplotlib]</font></i>',
                self.S["body"],
            )
        max_w = self._content_width()
        if getattr(self, '_current_orientation', 'portrait') == 'landscape':
            _, cur_h = self._landscape_size
        else:
            cur_h = H
        max_h = cur_h - 100 * mm
        try:
            img = RLImage(_io.BytesIO(png))
            iw, ih = img.imageWidth, img.imageHeight
            if iw > 0 and ih > 0:
                ratio = min(max_w / iw, max_h / ih, 1.0)
                img.drawWidth = iw * ratio
                img.drawHeight = ih * ratio
            img.hAlign = "CENTER"
            if spec["title"]:
                cap = Paragraph(self._fmt(spec["title"]), self.S["caption"])
                return KeepTogether([img, cap])
            return img
        except Exception as exc:
            _log.warning("Chart rendering error: %s", exc)
            return Paragraph(
                '<i><font color="#999999">[Chart rendering error]</font></i>',
                self.S["body"],
            )

    _NUMBERED_STYLES = {
        0: "body",
        1: "sub_bullet",
        2: "bullet_l2",
        3: "bullet_l3",
    }

    def _numbered(self, num, text, level=0):
        style_key = self._NUMBERED_STYLES.get(level, "body")
        prefix = f"<b>{num}.</b>  "
        return Paragraph(prefix + self._fmt(text), self.S[style_key])

    def _quote(self, text):
        data = [[Paragraph(self._fmt(text), self.S["quote"])]]
        t = Table(data, colWidths=[self._content_width()])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.PRIMARY_LIGHT),
            ("BOX", (0, 0), (-1, -1), 1.5, self.PRIMARY),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        t.spaceAfter = 1 * mm
        return t

    # ── Admonition (callout) ──

    _ADMONITION_STYLES = {
        "note":      {"label": "Note",       "border": "#4393E4", "bg": "#DCEEFB"},
        "warning":   {"label": "Warning",    "border": "#D29922", "bg": "#FFF2D5"},
        "tip":       {"label": "Tip",        "border": "#4AC26B", "bg": "#D6F5DD"},
        "important": {"label": "Important",  "border": "#A855F7", "bg": "#EDE3FB"},
        "caution":   {"label": "Caution",    "border": "#E5534B", "bg": "#FCDAD8"},
    }

    def _admonition(self, text, adm_type):
        """Renders a callout block (NOTE, WARNING, TIP, IMPORTANT, CAUTION)."""
        style = self._ADMONITION_STYLES.get(adm_type, self._ADMONITION_STYLES["note"])
        border_color = HexColor(style["border"])
        bg_color = HexColor(style["bg"])

        header_style = ParagraphStyle(
            f"Adm_{adm_type}_header", fontName="DejaVuBd", fontSize=9, leading=12,
            textColor=DARK_TEXT,
        )
        body_style = ParagraphStyle(
            f"Adm_{adm_type}_body", fontName="DejaVu", fontSize=9, leading=13,
            textColor=DARK_TEXT,
        )
        header = Paragraph(f"{style['label']}", header_style)
        body = Paragraph(self._fmt(text), body_style) if text else Spacer(1, 1)
        data = [[header], [body]] if text else [[header]]
        t = Table(data, colWidths=[self._content_width() - 4 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("LINEBEFORE", (0, 0), (0, -1), 3, border_color),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
            ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ("TOPPADDING", (0, 0), (0, 0), 8),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ]))
        t.spaceBefore = 2 * mm
        t.spaceAfter = 2 * mm
        return t

    # ── Definition list ──

    def _definition(self, term, definition):
        """Renders a definition list item (term + definition)."""
        term_style = ParagraphStyle(
            "DefTerm", parent=self.S["body"], fontName="DejaVuBd",
            spaceAfter=0,
        )
        def_style = ParagraphStyle(
            "DefBody", parent=self.S["body"], leftIndent=16,
            spaceBefore=0,
        )
        return KeepTogether([
            Paragraph(self._fmt(term), term_style),
            Paragraph(self._fmt(definition), def_style),
        ])

    def _code_block(self, text, lang="", highlight_lines=None):
        """Renders a code block with gray background and syntax highlighting."""
        hl_set = set(highlight_lines) if highlight_lines else set()
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Syntax highlight if language is known
        lang_spec = self._get_lang_spec(lang)
        raw_lines = escaped.split("\n")
        if lang_spec:
            highlighted = [self._highlight_line(l, lang_spec) for l in raw_lines]
        else:
            highlighted = list(raw_lines)

        # Highlight selected lines (yellow background via <span>)
        if hl_set:
            HL_BG = "#FFFDE7"
            for idx, line in enumerate(highlighted):
                if (idx + 1) in hl_set:
                    highlighted[idx] = (
                        f'<font backColor="{HL_BG}">{line}  </font>'
                    )

        code_html = "<br/>".join(highlighted)
        code_html = code_html.replace("  ", " &nbsp;")

        # Line numbering (for blocks of ≥ 3 lines)
        total_w = self._content_width()

        # Language label (on its own line above the code)
        flowables = []
        if lang and lang != "chart":
            lang_display = self._LANG_ALIASES_REVERSE.get(lang, lang)
            lang_label = Paragraph(
                f'<font color="#999999" size="7">{lang_display}</font>',
                ParagraphStyle("LangLabel", fontName="DejaVuMono", fontSize=7,
                               leading=9, alignment=TA_RIGHT),
            )

        if self._code_line_numbers and len(raw_lines) >= 3:
            nums_html = "<br/>".join(
                f'<font color="#AAAAAA">{i}</font>'
                for i in range(1, len(raw_lines) + 1)
            )
            nums_para = Paragraph(nums_html, self.S["code_nums"])
            code_para = Paragraph(code_html, self.S["code"])
            gutter_w = 28
            data = [[nums_para, code_para]]
            ts = [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, CODE_BORDER),
                ("LINEAFTER", (0, 0), (0, -1), 0.5, CODE_BORDER),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("RIGHTPADDING", (0, 0), (0, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 8),
                ("RIGHTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
            if lang and lang != "chart":
                # Insert language label as the first table row
                data = [["", lang_label]] + data
                ts.append(("TOPPADDING", (0, 0), (-1, 0), 4))
                ts.append(("BOTTOMPADDING", (0, 0), (-1, 0), 0))
                ts.append(("LINEAFTER", (0, 0), (0, 0), 0, CODE_BG))
            t = Table(data, colWidths=[gutter_w, total_w - gutter_w])
            t.setStyle(TableStyle(ts))
        else:
            if lang and lang != "chart":
                data = [[lang_label], [Paragraph(code_html, self.S["code"])]]
                ts = [
                    ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, CODE_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (0, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 1), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ]
                t = Table(data, colWidths=[total_w])
                t.setStyle(TableStyle(ts))
            else:
                content = Paragraph(code_html, self.S["code"])
                data = [[content]]
                t = Table(data, colWidths=[total_w])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, CODE_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]))
        t.spaceBefore = 1 * mm
        t.spaceAfter = 1 * mm
        return t

    # ── Syntax highlighting ──

    _SYNTAX_COLORS = {
        "keyword": "#7B30D0",
        "string": "#2E8B57",
        "comment": "#808080",
        "number": "#D2691E",
        "builtin": "#1A6B8C",
    }

    _LANG_KEYWORDS = {
        "python": {
            "keywords": [
                "def", "class", "import", "from", "return", "if", "elif",
                "else", "for", "while", "try", "except", "finally", "with",
                "as", "yield", "lambda", "pass", "break", "continue", "raise",
                "in", "not", "and", "or", "is", "None", "True", "False",
                "async", "await", "global", "nonlocal", "del", "assert",
            ],
            "comment": r"#.*$",
            "string": r'(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
        },
        "javascript": {
            "keywords": [
                "function", "const", "let", "var", "return", "if", "else",
                "for", "while", "class", "new", "this", "import", "export",
                "default", "async", "await", "try", "catch", "throw",
                "typeof", "instanceof", "null", "undefined", "true", "false",
                "switch", "case", "break", "continue", "of", "in",
            ],
            "comment": r"//.*$",
            "string": r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`)',
        },
        "bash": {
            "keywords": [
                "if", "then", "else", "elif", "fi", "for", "do", "done",
                "while", "case", "esac", "function", "return", "exit",
                "echo", "set", "export", "local", "readonly", "shift",
                "source", "read", "declare", "eval", "exec", "trap",
            ],
            "comment": r"#.*$",
            "string": r'(?:"(?:[^"\\]|\\.)*"|\'[^\']*\')',
        },
        "sql": {
            "keywords": [
                "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE",
                "CREATE", "DROP", "ALTER", "TABLE", "INDEX", "JOIN",
                "LEFT", "RIGHT", "INNER", "OUTER", "ON", "AND", "OR",
                "NOT", "NULL", "IS", "IN", "AS", "ORDER", "BY", "GROUP",
                "HAVING", "LIMIT", "SET", "VALUES", "INTO", "DISTINCT",
                "COUNT", "SUM", "AVG", "MAX", "MIN", "BETWEEN", "LIKE",
                "EXISTS", "UNION", "ALL", "CASE", "WHEN", "THEN",
                "ELSE", "END", "PRIMARY", "KEY", "FOREIGN", "DEFAULT",
            ],
            "comment": r"--.*$",
            "string": r"'(?:[^'\\]|\\.)*'",
            "case_insensitive": True,
        },
        "c": {
            "keywords": [
                "auto", "break", "case", "char", "const", "continue",
                "default", "do", "double", "else", "enum", "extern",
                "float", "for", "goto", "if", "inline", "int", "long",
                "register", "return", "short", "signed", "sizeof", "static",
                "struct", "switch", "typedef", "union", "unsigned", "void",
                "volatile", "while", "NULL", "true", "false",
                "#include", "#define", "#ifdef", "#ifndef", "#endif", "#pragma",
            ],
            "comment": r"//.*$",
            "string": r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
        },
        "java": {
            "keywords": [
                "abstract", "assert", "boolean", "break", "byte", "case",
                "catch", "char", "class", "const", "continue", "default",
                "do", "double", "else", "enum", "extends", "final",
                "finally", "float", "for", "if", "implements", "import",
                "instanceof", "int", "interface", "long", "native", "new",
                "package", "private", "protected", "public", "return",
                "short", "static", "super", "switch", "synchronized",
                "this", "throw", "throws", "try", "void", "volatile",
                "while", "null", "true", "false", "var",
            ],
            "comment": r"//.*$",
            "string": r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
        },
        "go": {
            "keywords": [
                "break", "case", "chan", "const", "continue", "default",
                "defer", "else", "fallthrough", "for", "func", "go",
                "goto", "if", "import", "interface", "map", "package",
                "range", "return", "select", "struct", "switch", "type",
                "var", "nil", "true", "false", "iota",
                "int", "string", "bool", "float64", "float32",
                "byte", "rune", "error", "any",
            ],
            "comment": r"//.*$",
            "string": r'(?:"(?:[^"\\]|\\.)*"|`[^`]*`|\'(?:[^\'\\]|\\.)*\')',
        },
        "html": {
            "keywords": [
                "html", "head", "body", "div", "span", "p", "a", "img",
                "table", "tr", "td", "th", "ul", "ol", "li", "form",
                "input", "button", "select", "option", "textarea",
                "script", "style", "link", "meta", "title", "section",
                "header", "footer", "nav", "main", "article", "aside",
                "class", "id", "href", "src", "type", "name", "value",
            ],
            "comment": r"<!--.*?-->",
            "string": r'(?:"[^"]*"|\'[^\']*\')',
        },
        "css": {
            "keywords": [
                "color", "background", "margin", "padding", "border",
                "font", "display", "position", "width", "height",
                "top", "left", "right", "bottom", "flex", "grid",
                "align", "justify", "overflow", "opacity", "transform",
                "transition", "animation", "content", "cursor", "z-index",
                "none", "auto", "inherit", "initial", "unset",
                "important", "media", "keyframes", "import",
            ],
            "comment": r"/\*.*?\*/",
            "string": r'(?:"[^"]*"|\'[^\']*\')',
        },
        "xml": {
            "keywords": [
                "xml", "version", "encoding", "xmlns", "xsi",
                "schema", "element", "attribute", "complexType",
                "simpleType", "sequence", "choice", "annotation",
                "documentation", "restriction", "extension", "base",
                "type", "name", "value", "ref", "use", "required",
            ],
            "comment": r"<!--.*?-->",
            "string": r'(?:"[^"]*"|\'[^\']*\')',
        },
        "kotlin": {
            "keywords": [
                "abstract", "actual", "annotation", "as", "break", "by",
                "catch", "class", "companion", "const", "constructor",
                "continue", "data", "do", "else", "enum", "expect",
                "external", "false", "final", "finally", "for", "fun",
                "if", "import", "in", "infix", "init", "inline",
                "interface", "internal", "is", "it", "lateinit", "null",
                "object", "open", "operator", "out", "override", "package",
                "private", "protected", "public", "return", "sealed",
                "super", "suspend", "this", "throw", "true", "try",
                "typealias", "val", "var", "when", "while",
            ],
            "comment": r"//.*$",
            "string": r'(?:"""[\s\S]*?"""|"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')',
        },
    }

    # Language aliases
    _LANG_ALIASES = {
        "py": "python", "python3": "python",
        "js": "javascript", "ts": "javascript", "typescript": "javascript",
        "sh": "bash", "shell": "bash", "zsh": "bash",
        "mysql": "sql", "postgresql": "sql", "sqlite": "sql",
        "cpp": "c", "c++": "c", "h": "c", "hpp": "c",
        "svg": "xml", "xhtml": "html", "htm": "html",
        "scss": "css", "sass": "css", "less": "css",
        "kt": "kotlin", "kts": "kotlin",
        "golang": "go",
    }

    # Reverse map: canonical → display name
    _LANG_ALIASES_REVERSE = {
        "python": "Python", "javascript": "JavaScript", "bash": "Bash",
        "sql": "SQL", "c": "C", "xml": "XML", "html": "HTML", "css": "CSS",
        "kotlin": "Kotlin", "go": "Go", "java": "Java", "rust": "Rust",
        "swift": "Swift", "ruby": "Ruby", "php": "PHP", "yaml": "YAML",
        "json": "JSON", "toml": "TOML", "markdown": "Markdown",
    }

    def _get_lang_spec(self, lang):
        """Returns the language spec or None."""
        if not lang:
            return None
        lang = self._LANG_ALIASES.get(lang, lang)
        return self._LANG_KEYWORDS.get(lang)

    def _highlight_line(self, line, lang_spec):
        """Highlights a single line of code via per-character coloring."""
        if not line.strip():
            return line

        n = len(line)
        colors = [None] * n

        # 1. Strings
        string_pat = lang_spec.get("string", "")
        if string_pat:
            for m in re.finditer(string_pat, line):
                for j in range(m.start(), min(m.end(), n)):
                    colors[j] = self._SYNTAX_COLORS["string"]

        # 2. Comments (override strings)
        comment_pat = lang_spec.get("comment", "")
        if comment_pat:
            for m in re.finditer(comment_pat, line):
                for j in range(m.start(), min(m.end(), n)):
                    colors[j] = self._SYNTAX_COLORS["comment"]

        # 3. Numbers (not inside strings/comments)
        for m in re.finditer(r"\b\d+(?:\.\d+)?\b", line):
            if all(colors[j] is None for j in range(m.start(), m.end())):
                for j in range(m.start(), m.end()):
                    colors[j] = self._SYNTAX_COLORS["number"]

        # 4. Keywords
        kw_pattern = r"\b(" + "|".join(re.escape(k) for k in lang_spec["keywords"]) + r")\b"
        flags = re.IGNORECASE if lang_spec.get("case_insensitive") else 0
        for m in re.finditer(kw_pattern, line, flags):
            if all(colors[j] is None for j in range(m.start(), m.end())):
                for j in range(m.start(), m.end()):
                    colors[j] = self._SYNTAX_COLORS["keyword"]

        # Assemble with <font> tags
        result = []
        current_color = None
        for j in range(n):
            if colors[j] != current_color:
                if current_color is not None:
                    result.append("</font>")
                current_color = colors[j]
                if current_color is not None:
                    result.append(f'<font color="{current_color}">')
            result.append(line[j])
        if current_color is not None:
            result.append("</font>")

        return "".join(result)

    def _hr(self):
        """Horizontal rule."""
        return HRFlowable(
            width="100%", thickness=0.5, color=self.BORDER,
            spaceBefore=2 * mm, spaceAfter=2 * mm,
        )

    _ALIGN_MAP = {"left": TA_LEFT, "right": TA_RIGHT, "center": TA_CENTER}

    def _table(self, headers, rows, alignments=None, caption=""):
        # splitLongWords=1 (default): allows breaking words that don't
        # fit in a cell. _calc_col_widths guarantees columns are
        # wide enough for most words — breaks only happen when there
        # is genuinely not enough space.
        hdr_s = ParagraphStyle(
            "TH", fontName="DejaVuBd", fontSize=7.5,
            leading=10, textColor=white, alignment=TA_CENTER,
        )
        cell_s = ParagraphStyle(
            "TD", fontName="DejaVu", fontSize=7.5,
            leading=10.5, textColor=DARK_TEXT,
        )
        cell_b = ParagraphStyle(
            "TDB", fontName="DejaVuBd", fontSize=7.5,
            leading=10.5, textColor=DARK_TEXT,
        )

        ncols = len(headers)

        # Per-column alignment
        col_aligns = []
        for ci in range(ncols):
            if alignments and ci < len(alignments):
                col_aligns.append(self._ALIGN_MAP.get(alignments[ci], TA_LEFT))
            else:
                col_aligns.append(TA_LEFT)

        # Normalize rows — equalize number of cells
        norm_rows = []
        for row in rows:
            if len(row) < ncols:
                row = row + [""] * (ncols - len(row))
            elif len(row) > ncols:
                row = row[:ncols]
            norm_rows.append(row)

        _h = self._hyphenate
        data = [[Paragraph(self._fmt(_h(h)), hdr_s) for h in headers]]
        for row in norm_rows:
            prow = []
            for idx, cell in enumerate(row):
                base = cell_b if (idx == 0 and len(row) > 2) else cell_s
                st = ParagraphStyle(f"TD_{idx}", parent=base,
                                    alignment=col_aligns[idx])
                prow.append(Paragraph(self._fmt(_h(cell)), st))
            data.append(prow)

        # Smart column-width distribution
        total_w = self._content_width()
        col_widths = self._calc_col_widths(headers, norm_rows, total_w)

        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, self.BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, self.TABLE_ALT]),
        ]))
        t.spaceBefore = 1 * mm
        t.spaceAfter = 1 * mm

        # Small tables (≤ 8 rows): KeepTogether — don't break.
        # Large tables: release to the flow — ReportLab will split
        # across pages, and repeatRows=1 will repeat the header.
        _SMALL_TABLE = 8
        nrows = len(norm_rows)
        if caption:
            cap_para = Paragraph(self._fmt(caption), self.S["caption"])
            cap_para.spaceAfter = 2 * mm
            if nrows <= _SMALL_TABLE:
                return KeepTogether([cap_para, t])
            # Large table — return list: caption + table separately,
            # so ReportLab can paginate (repeatRows=1)
            return [cap_para, t]
        if nrows <= _SMALL_TABLE:
            return KeepTogether([t])
        return t

    @staticmethod
    def _strip_md(text):
        """Strips Markdown markup for measuring text length."""
        t = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        t = re.sub(r"\*(.+?)\*", r"\1", t)
        t = re.sub(r"`([^`]+)`", r"\1", t)
        t = re.sub(r"~~(.+?)~~", r"\1", t)
        t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
        t = re.sub(r"~([^~\s]+)~", r"\1", t)
        t = re.sub(r"\^([^^\s]+)\^", r"\1", t)
        return t

    _SHY = "\u00AD"  # soft hyphen

    @staticmethod
    def _hyphenate(text):
        """Inserts soft hyphens (\u00AD) into words for correct line
        breaks in narrow table cells.  If pyphen is unavailable,
        returns text unchanged (splitLongWords=1 will handle it)."""
        if not _HYPHENATOR:
            return text
        shy = StudyGuidePDF._SHY

        def _hyph_word(w):
            # Skip short words, numbers and HTML tags
            if len(w) < 6 or w.startswith("<") or w.startswith("&"):
                return w
            # If the word contains Markdown markup — skip
            if any(c in w for c in ("*", "`", "~", "[", "]")):
                return w
            return _HYPHENATOR.inserted(w, hyphen=shy)

        return re.sub(r"[A-Za-z]{6,}", lambda m: _hyph_word(m.group()), text)

    @staticmethod
    def _calc_col_widths(headers, rows, total_w):
        """Distributes column widths: proportional to content,
        but no narrower than the longest word (so words don't break)."""
        ncols = len(headers)
        if ncols == 0:
            return []

        pad = 10  # LEFTPADDING + RIGHTPADDING (5 + 5)
        font = "DejaVu"
        font_b = "DejaVuBd"
        fs = 7.5

        word_min = [0.0] * ncols   # min: the longest word
        content_w = [0.0] * ncols  # proportional: weighted-average width

        for ci in range(ncols):
            # Header (bold font)
            h_text = StudyGuidePDF._strip_md(headers[ci])
            h_full = pdfmetrics.stringWidth(h_text, font_b, fs) + pad
            h_words = h_text.split()
            h_word_max = max(
                (pdfmetrics.stringWidth(w, font_b, fs) for w in h_words),
                default=0,
            ) + pad

            all_full = [h_full]
            col_word_max = h_word_max

            for row in rows:
                c_text = StudyGuidePDF._strip_md(row[ci])
                c_full = pdfmetrics.stringWidth(c_text, font, fs) + pad
                all_full.append(c_full)
                words = c_text.split()
                if words:
                    longest = max(
                        pdfmetrics.stringWidth(w, font, fs) for w in words
                    ) + pad
                    col_word_max = max(col_word_max, longest)

            word_min[ci] = col_word_max
            avg_w = sum(all_full) / len(all_full)
            mx_w = max(all_full)
            content_w[ci] = avg_w * 0.4 + mx_w * 0.6

        # Distribute widths while guaranteeing word_min
        min_total = sum(word_min)

        if min_total <= total_w:
            # Enough space — every column gets its minimum,
            # remainder is distributed proportionally to content_w
            widths = list(word_min)
            remaining = total_w - min_total
            extra_need = [max(0, content_w[ci] - word_min[ci])
                          for ci in range(ncols)]
            total_extra = sum(extra_need)
            if total_extra > 0:
                for ci in range(ncols):
                    widths[ci] += remaining * (extra_need[ci] / total_extra)
            else:
                # All columns at minimum — even split
                for ci in range(ncols):
                    widths[ci] += remaining / ncols
        else:
            # Even the minimums don't fit — proportional compression.
            # splitLongWords=1 in cell styles will take care of breaking.
            widths = [w / min_total * total_w for w in word_min]

        return widths

    def _columns(self, text, num_cols=2):
        """Multi-column layout via Table."""
        _, _, inner_tokens, _ = parse_markdown(text)
        flowables = []
        for tok in inner_tokens:
            if tok.kind == "body":
                flowables.append(self._body(tok.text))
            elif tok.kind == "bullet":
                flowables.append(self._bullet(tok.text, tok.level))
            elif tok.kind == "numbered":
                flowables.append(self._numbered(tok.num, tok.text))
            elif tok.kind == "checkbox":
                flowables.append(self._checkbox(tok.text, tok.checked, tok.level))
            elif tok.kind == "quote":
                flowables.append(self._quote(tok.text))
            elif tok.kind in ("h1", "h2", "h3", "h4"):
                style = self.S.get(tok.kind, self.S["h3"])
                flowables.append(Paragraph(self._fmt(tok.text), style))
            elif tok.kind == "table":
                _tbl = self._table(tok.headers, tok.rows,
                                   tok.alignments, tok.caption)
                if isinstance(_tbl, list):
                    flowables.extend(_tbl)
                else:
                    flowables.append(_tbl)
            elif tok.kind == "code":
                flowables.append(self._code_block(tok.text, tok.lang))
            elif tok.kind == "image":
                md_dir = getattr(self, '_md_dir', '.')
                result = self._image(tok.path, tok.alt, md_dir,
                                     width_pct=tok.width)
                if isinstance(result, tuple) and result[0] == "float":
                    flowables.append(result[1])  # in columns float → inline
                else:
                    flowables.append(result)
            elif tok.kind == "math":
                flowables.append(self._math_block(tok.text))
            elif tok.kind == "chart":
                flowables.append(self._chart(tok.text))
            elif tok.kind == "hr":
                flowables.append(self._hr())
        if not flowables:
            return Spacer(1, 1)

        # Check: if content contains a table (directly or in KeepTogether),
        # columns layout may not fit — fall back to a single column
        def _has_table(f):
            if isinstance(f, Table):
                return True
            if isinstance(f, KeepTogether):
                return any(_has_table(c) for c in getattr(f, '_content', []))
            return False
        _has_big = any(_has_table(f) for f in flowables)
        if _has_big:
            # Return as a regular flow without columns
            flowables[0].spaceBefore = 2 * mm
            flowables[-1].spaceAfter = 2 * mm
            return KeepTogether(flowables) if len(flowables) <= 6 else flowables

        per_col = max(1, -(-len(flowables) // num_cols))  # ceil division
        columns = []
        for c in range(num_cols):
            columns.append(flowables[c * per_col:(c + 1) * per_col])
        # Pad empty columns
        while len(columns) < num_cols:
            columns.append([Spacer(1, 1)])
        total_w = self._content_width()
        col_w = total_w / num_cols
        data = [columns]
        t = Table(data, colWidths=[col_w] * num_cols)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        t.spaceBefore = 2 * mm
        t.spaceAfter = 2 * mm
        return t

    # ── Cover patterns ──

    def _draw_cover_pattern(self, c, pw, ph):
        """Draws a decorative pattern on the cover."""
        pat = self._cover_pattern
        colors = self.COVER_CIRCLES
        if pat == "none":
            return

        if pat == "circles":
            positions = [
                (pw * 0.85, ph * 0.8, 120),
                (pw * 0.1, ph * 0.15, 80),
                (pw * 0.7, ph * 0.25, 60),
            ]
            for (cx, cy, r), clr in zip(positions, colors):
                c.setFillColor(clr)
                c.circle(cx, cy, r, fill=True, stroke=False)

        elif pat == "diamonds":
            diamonds = [
                (pw * 0.88, ph * 0.82, 90),
                (pw * 0.08, ph * 0.12, 65),
                (pw * 0.72, ph * 0.22, 45),
            ]
            for (cx, cy, sz), clr in zip(diamonds, colors):
                c.setFillColor(clr)
                p = c.beginPath()
                p.moveTo(cx, cy + sz)
                p.lineTo(cx + sz * 0.7, cy)
                p.lineTo(cx, cy - sz)
                p.lineTo(cx - sz * 0.7, cy)
                p.close()
                c.drawPath(p, fill=True, stroke=False)

        elif pat == "lines":
            c.saveState()
            step = 18
            c.setStrokeColor(colors[0])
            c.setLineWidth(1)
            # Diagonal lines in the bottom-left corner
            for i in range(0, int(pw * 0.4), step):
                c.line(0, i, i, 0)
            # Diagonal lines in the top-right corner
            c.setStrokeColor(colors[1])
            for i in range(0, int(pw * 0.4), step):
                c.line(pw, ph - i, pw - i, ph)
            c.restoreState()

        elif pat == "dots":
            import random as _rnd
            _rnd.seed(42)  # deterministic pattern
            c.saveState()
            for clr in colors:
                c.setFillColor(clr)
                for _ in range(25):
                    x = _rnd.uniform(20, pw - 20)
                    y = _rnd.uniform(20, ph - 20)
                    r = _rnd.uniform(2, 6)
                    c.circle(x, y, r, fill=True, stroke=False)
            c.restoreState()

    # ── Cover ──

    def _draw_cover(self, c, doc):
        """Draws the cover. Title is auto-scaled."""
        pw, ph = c._pagesize

        # Cover background: image or solid color
        if self._cover_image and os.path.isfile(self._cover_image):
            from reportlab.lib.utils import ImageReader
            try:
                img = ImageReader(self._cover_image)
                iw, ih = img.getSize()
                scale = max(pw / iw, ph / ih)
                draw_w, draw_h = iw * scale, ih * scale
                x_off = (pw - draw_w) / 2
                y_off = (ph - draw_h) / 2
                c.drawImage(img, x_off, y_off, draw_w, draw_h, mask="auto")
                # Darkening for text readability
                c.setFillColor(Color(0, 0, 0, alpha=0.45))
                c.rect(0, 0, pw, ph, fill=True, stroke=False)
            except Exception:
                c.setFillColor(self.PRIMARY)
                c.rect(0, 0, pw, ph, fill=True, stroke=False)
        else:
            c.setFillColor(self.PRIMARY)
            c.rect(0, 0, pw, ph, fill=True, stroke=False)

            # Decorative cover pattern (only for solid background)
            self._draw_cover_pattern(c, pw, ph)

        # Gold lines
        c.setStrokeColor(self.ACCENT)
        c.setLineWidth(3)
        c.line(50, ph * 0.63, pw - 50, ph * 0.63)
        c.line(50, ph * 0.33, pw - 50, ph * 0.33)

        # --- Top label (LECTURE 3 / TOPIC 2 / ...) ---
        c.setFillColor(white)
        if self._cover_top:
            c.setFont("DejaVuBd", 14)
            c.drawCentredString(pw / 2, ph * 0.73, self._cover_top)

        # --- Main title (auto-scale) ---
        title_text = self._cover_title
        cover_lines = self._wrap_text(title_text, max_chars=32)

        max_line = max(cover_lines, key=len)
        max_width = pw - 100
        font_size = 28
        while font_size > 14:
            tw = pdfmetrics.stringWidth(max_line, "DejaVuBd", font_size)
            if tw <= max_width:
                break
            font_size -= 1

        c.setFont("DejaVuBd", font_size)
        c.setFillColor(white)
        line_height = font_size * 1.3
        total_height = len(cover_lines) * line_height
        y_start = ph * 0.48 + total_height / 2
        for idx, line in enumerate(cover_lines):
            c.drawCentredString(pw / 2, y_start - idx * line_height, line)

        # --- Subtitles (TOC items) — auto-scaling ---
        topics = self._cover_topics  # all topics, no limit
        if topics:
            n_topics = len(topics)
            # Available area: from ph*0.28 at top to ~90pt at bottom (author+subtitle)
            y_top = ph * 0.28
            y_bottom = 90
            avail_height = y_top - y_bottom
            # Pick font and step so it all fits
            font_size = min(10, max(6, avail_height / n_topics / 1.5))
            line_height = min(16, max(9, avail_height / n_topics))
            total_block = n_topics * line_height
            y = y_top - (avail_height - total_block) / 2  # center block vertically

            c.setFont("DejaVu", font_size)
            c.setFillColor(self.COVER_SUB)
            max_width = pw - 80
            for item in topics:
                clean = re.sub(r"^\d+\.\s*", "", item).upper()
                tw = pdfmetrics.stringWidth(clean, "DejaVu", font_size)
                while tw > max_width and len(clean) > 10:
                    clean = clean[:-4] + "..."
                    tw = pdfmetrics.stringWidth(clean, "DejaVu", font_size)
                c.drawCentredString(pw / 2, y, clean)
                y -= line_height

        # Author
        if self._author and self._cover_author:
            c.setFillColor(self.COVER_SUB)
            c.setFont("DejaVu", 11)
            c.drawCentredString(pw / 2, 68, self._author)

        # Subtitle
        if self.subtitle:
            c.setFillColor(self.ACCENT)
            c.setFont("DejaVuBd", 10)
            c.drawCentredString(pw / 2, 45, self.subtitle)

    @staticmethod
    def _wrap_text(text: str, max_chars: int = 32) -> list[str]:
        """Splits text into lines, trying not to exceed max_chars."""
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if len(test) <= max_chars:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [text]

    # ── Header, footer, watermark ──

    def _draw_chapter_page(self, c, doc):
        """Draws a chapter divider page (no header, just page number)."""
        c.saveState()
        page_num = doc.page
        pw, ph = c._pagesize
        c.setFillColor(self.PRIMARY)
        c.circle(pw / 2, 12 * mm, 8, fill=True, stroke=False)
        c.setFillColor(white)
        c.setFont("DejaVuBd", 7)
        c.drawCentredString(pw / 2, 10 * mm, str(page_num))
        c.restoreState()
        if self.watermark:
            self._draw_watermark(c)
        self._draw_fingerprint(c)

    def _draw_page(self, c, doc):
        """Draws header, footer and watermark on every page."""
        c.saveState()
        page_num = doc.page
        pw, ph = c._pagesize  # dynamic size (portrait or landscape)

        # Margins from preset
        _mt, _mb, base_l, base_r = self._margins
        if self.duplex and page_num % 2 == 0:
            left_m, right_m = base_r, base_l  # mirrored
        else:
            left_m, right_m = base_l, base_r

        # Header
        c.setStrokeColor(self.PRIMARY)
        c.setLineWidth(1.5)
        c.line(left_m, ph - 15 * mm, pw - right_m, ph - 15 * mm)

        # Running header: title · chapter · section
        # SectionTracker writes to c._doc (PDFDocument), not doc (BaseDocTemplate)
        pdf_doc = c._doc
        chapter = getattr(pdf_doc, "_running_chapter", "")
        section = getattr(pdf_doc, "_running_header", "")
        parts = [self._header_text]
        if chapter and chapter != self._header_text:
            parts.append(chapter)
        if section and section != chapter and section != self._header_text:
            parts.append(section)
        header_display = "  ·  ".join(parts)

        c.setFillColor(MEDIUM_TEXT)
        c.setFont("DejaVu", 7)
        max_header_w = pw - left_m - right_m
        while pdfmetrics.stringWidth(header_display, "DejaVu", 7) > max_header_w and len(header_display) > 20:
            header_display = header_display[:-4] + "..."
        c.drawString(left_m, ph - 13 * mm, header_display)

        # Footer
        c.setStrokeColor(self.BORDER)
        c.setLineWidth(0.5)
        c.line(left_m, 18 * mm, pw - right_m, 18 * mm)
        # Duplex: number on outer edge; otherwise: centered
        if self.duplex:
            c.setFillColor(self.PRIMARY)
            if page_num % 2 == 1:  # odd → right
                num_x = pw - right_m
            else:  # even → left
                num_x = left_m
            c.circle(num_x, 12 * mm, 8, fill=True, stroke=False)
            c.setFillColor(white)
            c.setFont("DejaVuBd", 7)
            c.drawCentredString(num_x, 10 * mm, str(page_num))
        else:
            c.setFillColor(self.PRIMARY)
            c.circle(pw / 2, 12 * mm, 8, fill=True, stroke=False)
            c.setFillColor(white)
            c.setFont("DejaVuBd", 7)
            c.drawCentredString(pw / 2, 10 * mm, str(page_num))

        # Copy UUID in footer
        if self._copy_id_show:
            c.setFillColor(Color(0.7, 0.7, 0.7, alpha=1))
            c.setFont("DejaVu", 4)
            uid = self._copy_uuid[:8]
            if self.duplex and page_num % 2 == 0:
                c.drawString(left_m, 6 * mm, uid)
            else:
                c.drawRightString(pw - right_m, 6 * mm, uid)

        # QR code in the bottom corner (opposite the page number)
        if self._show_qr:
            qr_reader = self._get_qr_image()
            if qr_reader:
                qr_size = 10 * mm
                if self.duplex:
                    # Number on outer edge → QR on inner
                    if page_num % 2 == 1:
                        qr_x = left_m
                    else:
                        qr_x = pw - right_m - qr_size
                else:
                    # Number centered → QR on the left
                    qr_x = left_m
                c.drawImage(qr_reader, qr_x, 3 * mm,
                            qr_size, qr_size, mask="auto")

        c.restoreState()

        # Watermark
        if self.watermark:
            self._draw_watermark(c)

        # Invisible fingerprint
        self._draw_fingerprint(c)

    def _draw_watermark(self, c):
        """
        Draws a diagonal watermark as a raster image.
        The image has no text glyphs — cannot be selected/copied.
        """
        try:
            self._draw_watermark_image(c)
        except Exception:
            self._draw_watermark_text(c)

    def _draw_watermark_image(self, c):
        """Raster watermark — fully unselectable."""
        import io
        from PIL import Image, ImageDraw, ImageFont
        from reportlab.lib.utils import ImageReader

        if not hasattr(self, "_wm_cache"):
            scale = 2  # 2x for on-screen clarity
            font_size = int(11 * scale)
            font_path = pdfmetrics.getFont("DejaVuBd").face.filename
            pil_font = ImageFont.truetype(font_path, font_size)

            bbox = pil_font.getbbox(self.watermark)
            tw = bbox[2] - bbox[0] + 10
            th = bbox[3] - bbox[1] + 10

            txt_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            draw = ImageDraw.Draw(txt_img)
            draw.text(
                (5, 5 - bbox[1]), self.watermark,
                fill=(0, 0, 0, 10), font=pil_font,
            )
            rotated = txt_img.rotate(35, expand=True, resample=Image.BICUBIC)

            buf = io.BytesIO()
            rotated.save(buf, "PNG")
            buf.seek(0)
            self._wm_cache = (
                ImageReader(buf),
                rotated.width / scale,
                rotated.height / scale,
            )

        img, tile_w, tile_h = self._wm_cache
        pw, ph = c._pagesize
        c.saveState()
        for x_off in range(-50, int(pw) + 100, 160):
            for y_off in range(-50, int(ph) + 100, 100):
                c.drawImage(img, x_off, y_off,
                            width=tile_w, height=tile_h, mask="auto")
        c.restoreState()

    def _draw_watermark_text(self, c):
        """Fallback: text watermark (may be selectable in some viewers)."""
        c.saveState()
        try:
            c._code.append(
                '/Artifact <</Type /Pagination /Subtype /Watermark>> BDC'
            )
        except (AttributeError, TypeError):
            pass

        pw, ph = c._pagesize
        c.setFillColor(Color(0, 0, 0, alpha=0.04))
        c.setFont("DejaVuBd", 11)
        for x_off in range(-50, int(pw) + 100, 160):
            for y_off in range(-50, int(ph) + 100, 100):
                c.saveState()
                c.translate(x_off, y_off)
                c.rotate(35)
                c.drawString(0, 0, self.watermark)
                c.restoreState()

        try:
            c._code.append('EMC')
        except (AttributeError, TypeError):
            pass
        c.restoreState()

    def _draw_fingerprint(self, c):
        """Invisible fingerprint: author + date as micro text in background color."""
        if not self._author:
            return
        c.saveState()
        c.setFillColor(Color(1, 1, 1, alpha=0.01))
        c.setFont("DejaVu", 1)
        fp_text = f"{self._author} {self._fingerprint_date} {self._copy_uuid[:8]}"
        pw, ph = c._pagesize
        for x_off in range(-20, int(pw) + 50, 120):
            for y_off in range(-20, int(ph) + 50, 80):
                c.saveState()
                c.translate(x_off, y_off)
                c.rotate(45)
                c.drawString(0, 0, fp_text)
                c.restoreState()
        c.restoreState()

    def _get_qr_image(self):
        """Returns a cached ImageReader with the QR code in theme colors."""
        if self._qr_cache is not None:
            return self._qr_cache
        try:
            import qrcode
            import json
            import io as _io
            from PIL import Image as _PILImage
            from reportlab.lib.utils import ImageReader
        except ImportError:
            _log.warning("QR: install qrcode — pip install qrcode[pil]")
            self._qr_cache = False
            return False
        data = json.dumps({
            "author": self._author or "",
            "date": self._fingerprint_date,
            "hash": f"sha256:{self._md_hash}" if self._md_hash else "",
            "uuid": self._copy_uuid,
        }, ensure_ascii=False)
        # Theme color for QR dots
        pc = self.PRIMARY
        pr, pg, pb = int(pc.red * 255), int(pc.green * 255), int(pc.blue * 255)
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=6, border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=(pr, pg, pb), back_color="white").convert("RGBA")
        # White background → transparent
        pixels = img.load()
        w, h = img.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if r > 240 and g > 240 and b > 240:
                    pixels[x, y] = (255, 255, 255, 0)
                else:
                    pixels[x, y] = (r, g, b, 160)  # semi-transparent dots
        buf = _io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        self._qr_cache = ImageReader(buf)
        return self._qr_cache

    # ── Anchors and bookmarks ──

    def _anchor_name(self, text):
        """Generates a unique anchor name from heading text."""
        self._section_counter += 1
        return f"section_{self._section_counter}"

    # ── Story assembly ──

    @staticmethod
    def _flatten_flowables(items):
        """Flattens KeepTogether groups into a flat flowable list.
        _FitPageFlowable does not support nested KeepTogether (no draw())."""
        flat = []
        for item in items:
            if isinstance(item, KeepTogether):
                flat.extend(StudyGuidePDF._flatten_flowables(
                    getattr(item, '_content', [])))
            else:
                flat.append(item)
        return flat

    def _apply_fit_page(self, story):
        """Post-processing: wraps content between _FitPageStart/_FitPageEnd
        in _FitPageFlowable so everything fits on one page."""
        result = []
        i = 0
        while i < len(story):
            if isinstance(story[i], _FitPageStart):
                orient = story[i].orientation
                if orient == "landscape":
                    pw, ph = self._landscape_size
                else:
                    pw, ph = self.page_size
                mt, mb, ml, mr = self._margins
                # Frame has 6pt padding on each side (ReportLab default)
                _FP = 6
                avail_w = pw - ml - mr - 2 * _FP
                avail_h = ph - mt - mb - 2 * _FP
                # Account for header/footer intrusion with narrow margins:
                # header: line ph-15mm, text ph-13mm → bottom edge ~ph-17mm
                # footer: line 18mm, circle 12mm → top edge ~20mm
                _header_intrusion = max(0, 17 * mm - mt)
                _footer_intrusion = max(0, 20 * mm - mb)
                avail_h -= _header_intrusion + _footer_intrusion
                buf = []
                i += 1
                while i < len(story) and not isinstance(story[i], _FitPageEnd):
                    item = story[i]
                    # Drop PageBreak/NextPageTemplate inside fit-page
                    if not isinstance(item, (PageBreak, NextPageTemplate)):
                        buf.append(item)
                    i += 1
                if buf:
                    flat = self._flatten_flowables(buf)
                    fpf = _FitPageFlowable(flat, avail_w, avail_h)
                    result.append(fpf)
                if i < len(story) and isinstance(story[i], _FitPageEnd):
                    i += 1  # skip _FitPageEnd
                else:
                    _log.warning(":::fit-page without closing :::")
            else:
                result.append(story[i])
                i += 1
        return result

    # Element kinds that are NOT included in a heading's KeepTogether group
    _KT_STOP = frozenset((
        "h1", "h2", "h3", "h4", "float_image",
        "landscape_start", "landscape_end",
        "fit_page_start", "fit_page_end",
        "pagebreak",
    ))

    _KT_HEIGHT_BUDGET = 120  # pt — max group height after a heading

    @staticmethod
    def _estimate_height(kind, obj):
        """Rough estimate of flowable height (pt) for the KeepTogether budget."""
        if kind == "content":
            # Paragraph body ≈ 13pt (leading) × number of lines
            text = getattr(obj, 'text', '')
            return max(15, len(text) / 60 * 13)
        if kind == "table":
            # Tables — treated as expensive
            return 200
        if kind == "code":
            return 150
        if kind in ("image", "chart", "math"):
            return 200
        # bullet, numbered, checkbox, quote, hr — ~15pt
        return 15

    def _greedy_collect(self, raw, start, group, stop_kinds=None):
        """Greedily collects items into group while total height < budget.
        Returns the new index j."""
        if stop_kinds is None:
            stop_kinds = self._KT_STOP
        budget = self._KT_HEIGHT_BUDGET
        used = 0
        j = start
        while j < len(raw):
            nk, no = raw[j]
            if nk in stop_kinds:
                break
            h = self._estimate_height(nk, no)
            if used > 0 and used + h > budget:
                break  # already have items, next won't fit
            group.append(no)
            used += h
            j += 1
        return j

    def _build_story(self, toc_items, tokens, pass_num=2):
        """
        Builds the story list from tokens.
        pass_num=1: first pass — collects page numbers for the TOC.
        pass_num=2: final pass — TOC with page numbers.
        """
        story = []

        # Cover
        if self.show_cover:
            story.append(NextPageTemplate("Normal"))
            story.append(PageBreak())

        # Generate anchors for TOC (h2 and h3)
        # Use a list + queue to support duplicate headings
        # (e.g. "Introduction" in different files with --merge)
        from collections import deque, defaultdict
        toc_anchor_list = []  # positional: toc_anchor_list[i] for toc_items[i]
        _anchor_queues = defaultdict(deque)  # text → queue of anchors
        anchor_counter = 0
        for _lvl, item_text in toc_items:
            anchor_counter += 1
            anchor_name = f"toc_{anchor_counter}"
            toc_anchor_list.append(anchor_name)
            _anchor_queues[item_text].append(anchor_name)

        # Root bookmark for the document (needed before H2 level=1)
        story.append(BookmarkFlowable(self._header_text, level=0))

        # Table of contents
        if self.show_toc and toc_items:
            bar = HRFlowable(
                width="100%", thickness=2, color=self.PRIMARY, spaceAfter=2 * mm,
            )
            story.append(bar)
            story.append(Paragraph("Contents", self.S["h1"]))
            story.append(self._sp(2))

            # ── TOC styles (adaptive scale) ──
            cw = self._content_width()
            visible = sum(1 for l, _ in toc_items if l <= self.toc_depth)
            # Scale: <=20 entries — normal, 20-40 — medium, >40 — compact
            if visible <= 20:
                s1, l1 = 10, 15       # H2: font, leading
                s_h1, l_h1 = 10.5, 16  # H1
                s3, l3 = 8.5, 12      # H3
                s4, l4 = 7.5, 11      # H4
                sp_h1 = 1 * mm        # spaceBefore H1
            elif visible <= 40:
                s1, l1 = 9, 13
                s_h1, l_h1 = 9.5, 14
                s3, l3 = 7.5, 10.5
                s4, l4 = 7, 9.5
                sp_h1 = 0.6 * mm
            else:
                s1, l1 = 8, 11
                s_h1, l_h1 = 8.5, 12
                s3, l3 = 7, 9.5
                s4, l4 = 6.5, 8.5
                sp_h1 = 0.3 * mm

            _toc_zero_pad = TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
            toc_page_style = ParagraphStyle(
                "TOCPage", fontName="DejaVu", fontSize=s1,
                leading=l1, textColor=MEDIUM_TEXT,
            )
            toc_dots_style = ParagraphStyle(
                "TOCDots", fontName="DejaVu", fontSize=s1,
                leading=l1, textColor=HexColor("#CCCCCC"),
            )
            toc_h1_style = ParagraphStyle(
                "TOCH1", fontName="DejaVuBd", fontSize=s_h1,
                leading=l_h1, textColor=self.PRIMARY,
                spaceBefore=sp_h1,
            )
            toc_h2_style = ParagraphStyle(
                "TOCH2", fontName="DejaVu", fontSize=s1,
                leading=l1, textColor=DARK_TEXT, leftIndent=5,
            )
            toc_h3_style = ParagraphStyle(
                "TOCH3", fontName="DejaVu", fontSize=s3,
                leading=l3, textColor=DARK_TEXT, leftIndent=14,
            )
            toc_h3_page = ParagraphStyle(
                "TOCH3Page", fontName="DejaVu", fontSize=s3,
                leading=l3, textColor=MEDIUM_TEXT,
            )
            toc_h3_dots = ParagraphStyle(
                "TOCH3Dots", fontName="DejaVu", fontSize=s3,
                leading=l3, textColor=HexColor("#DDDDDD"),
            )
            toc_h4_style = ParagraphStyle(
                "TOCH4", fontName="DejaVu", fontSize=s4,
                leading=l4, textColor=MEDIUM_TEXT, leftIndent=24,
            )
            toc_h4_page = ParagraphStyle(
                "TOCH4Page", fontName="DejaVu", fontSize=s4,
                leading=l4, textColor=MEDIUM_TEXT,
            )
            toc_h4_dots = ParagraphStyle(
                "TOCH4Dots", fontName="DejaVu", fontSize=s4,
                leading=l4, textColor=HexColor("#DDDDDD"),
            )

            def _toc_row(label_p, dots_p, page_p, indent=0):
                """TOC row: text + dots + page number."""
                row = Table(
                    [[label_p, dots_p, page_p]],
                    colWidths=[cw - 30 * mm - indent, None, 12 * mm],
                )
                row.setStyle(_toc_zero_pad)
                if indent:
                    row = Table([[Spacer(indent, 1), row]],
                                colWidths=[indent, cw - indent])
                    row.setStyle(_toc_zero_pad)
                return row

            # Collect TOC entries grouped by chapters for KeepTogether
            _file_counter = 0
            _chapter_num = 0
            _has_h1 = any(l == 1 for l, _ in toc_items)
            _chapter_group = []  # current group (H1 + first H2s)
            _h2_in_group = 0     # how many H2s already in the group

            def _flush_chapter_group():
                nonlocal _chapter_group
                if _chapter_group:
                    story.append(KeepTogether(_chapter_group))
                    _chapter_group = []

            for toc_idx, (lvl, item_text) in enumerate(toc_items):
                if lvl > self.toc_depth:
                    continue
                anchor = toc_anchor_list[toc_idx]
                page_num = self._page_tracker.get(anchor, "")
                dots = " · " * 20 if page_num else ""

                if lvl == 1:
                    # Flush previous group
                    _flush_chapter_group()
                    _h2_in_group = 0
                    _chapter_num += 1

                    # ── Divider between chapters (except the first) ──
                    if _chapter_num > 1:
                        story.append(Spacer(1, 2 * mm))
                        story.append(HRFlowable(
                            width="30%", thickness=0.5, color=self.BORDER,
                            hAlign="CENTER", spaceBefore=0, spaceAfter=2 * mm))

                    # Level 1 — chapter title with number
                    num_label = f'{_chapter_num}.&nbsp;&nbsp;'
                    label = (f'<a href="#{anchor}">'
                             f'<font color="{MEDIUM_TEXT.hexval()}">{num_label}</font>'
                             f'<b>{self._fmt(item_text)}</b></a>')
                    meta = getattr(self, '_file_meta', [])
                    fm = meta[_file_counter] if _file_counter < len(meta) else {}
                    _file_counter += 1
                    sub_parts = []
                    if fm.get("subtitle"):
                        sub_parts.append(fm["subtitle"])
                    if fm.get("author"):
                        sub_parts.append(fm["author"])
                    if sub_parts:
                        sub_sz = max(s_h1 - 2, 6)
                        label += (f'<br/><font size="{sub_sz}" color="{MEDIUM_TEXT.hexval()}">'
                                  f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'
                                  f'{" — ".join(sub_parts)}</font>')
                    _chapter_group.append(_toc_row(
                        Paragraph(label, toc_h1_style),
                        Paragraph(dots, toc_dots_style),
                        Paragraph(str(page_num), toc_page_style),
                    ))
                    continue

                def _make_entry():
                    if lvl == 3:
                        lbl = f'<a href="#{anchor}">{self._fmt(item_text)}</a>'
                        return _toc_row(
                            Paragraph(lbl, toc_h3_style),
                            Paragraph(dots, toc_h3_dots),
                            Paragraph(str(page_num), toc_h3_page),
                            indent=14,
                        )
                    if lvl >= 4:
                        lbl = f'<a href="#{anchor}">{self._fmt(item_text)}</a>'
                        return _toc_row(
                            Paragraph(lbl, toc_h4_style),
                            Paragraph(dots, toc_h4_dots),
                            Paragraph(str(page_num), toc_h4_page),
                            indent=24,
                        )
                    # h2
                    m_toc = re.match(r"^(\d+)\.\s*(.+)", item_text)
                    if m_toc:
                        lbl = (
                            f'<a href="#{anchor}">'
                            f'<b><font color="{self.PRIMARY.hexval()}">'
                            f"{m_toc.group(1)}.</font></b>   {m_toc.group(2)}</a>"
                        )
                    else:
                        lbl = f'<a href="#{anchor}">{self._fmt(item_text)}</a>'
                    return _toc_row(
                        Paragraph(lbl, toc_h2_style),
                        Paragraph(dots, toc_dots_style),
                        Paragraph(str(page_num), toc_page_style),
                    )

                entry = _make_entry()

                # First 2 H2s after H1 — into the group (KeepTogether)
                if _has_h1 and _h2_in_group < 2 and _chapter_group:
                    _chapter_group.append(entry)
                    if lvl == 2:
                        _h2_in_group += 1
                    if _h2_in_group >= 2:
                        _flush_chapter_group()
                else:
                    story.append(entry)

            _flush_chapter_group()
            story.append(PageBreak())

        # Render tokens into an intermediate list of labeled flowables
        raw: list[tuple[str, object]] = []

        for tok in tokens:
            if tok.kind == "h1":
                q = _anchor_queues.get(tok.text)
                anchor = q.popleft() if q else ""
                anchor_tag = f'<a name="{anchor}"/>' if anchor else ""
                raw.append(("h1", (tok.text, anchor_tag)))
            elif tok.kind == "h2":
                q = _anchor_queues.get(tok.text)
                anchor = q.popleft() if q else ""
                anchor_tag = f'<a name="{anchor}"/>' if anchor else ""
                raw.append(("h2", (tok.text, anchor_tag)))
            elif tok.kind == "h3":
                q = _anchor_queues.get(tok.text)
                h3_anchor = q.popleft() if q else ""
                h3_tag = f'<a name="{h3_anchor}"/>' if h3_anchor else ""
                raw.append(("h3", Paragraph(h3_tag + tok.text, self.S["h3"])))
            elif tok.kind == "h4":
                q = _anchor_queues.get(tok.text)
                h4_anchor = q.popleft() if q else ""
                h4_tag = f'<a name="{h4_anchor}"/>' if h4_anchor else ""
                raw.append(("h4", Paragraph(h4_tag + tok.text, self.S["h4"])))
            elif tok.kind == "body":
                raw.append(("content", self._body(tok.text)))
            elif tok.kind == "bullet":
                raw.append(("content", self._bullet(tok.text, tok.level)))
            elif tok.kind == "numbered":
                raw.append(("content", self._numbered(tok.num, tok.text, tok.level)))
            elif tok.kind == "quote":
                raw.append(("content", self._quote(tok.text)))
            elif tok.kind == "admonition":
                raw.append(("content", self._admonition(tok.text, tok.admonition_type)))
            elif tok.kind == "definition":
                raw.append(("content", self._definition(tok.alt, tok.text)))
            elif tok.kind == "pagebreak":
                raw.append(("pagebreak", None))
            elif tok.kind == "table":
                _tbl = self._table(tok.headers, tok.rows,
                                   tok.alignments, tok.caption)
                if isinstance(_tbl, list):
                    for _t in _tbl:
                        raw.append(("content", _t))
                else:
                    raw.append(("content", _tbl))
            elif tok.kind == "checkbox":
                raw.append(("content", self._checkbox(tok.text, tok.checked, tok.level)))
            elif tok.kind == "image":
                result = self._image(tok.path, tok.alt, self._md_dir,
                                     width_pct=tok.width, float_side=tok.float_side)
                if isinstance(result, tuple) and result[0] == "float":
                    _, img_flowable, side, cap = result
                    raw.append(("float_image", (img_flowable, side, cap)))
                else:
                    raw.append(("content", result))
            elif tok.kind == "code":
                raw.append(("content", self._code_block(tok.text, tok.lang,
                                                         tok.highlight_lines)))
            elif tok.kind == "chart":
                raw.append(("content", self._chart(tok.text)))
            elif tok.kind == "hr":
                raw.append(("content", self._hr()))
            elif tok.kind == "math":
                raw.append(("content", Paragraph(self._math(tok.text), self.S["math"])))
            elif tok.kind == "columns":
                _col_result = self._columns(tok.text, tok.level)
                if isinstance(_col_result, list):
                    for _c in _col_result:
                        raw.append(("content", _c))
                else:
                    raw.append(("content", _col_result))
            elif tok.kind == "landscape_start":
                self._current_orientation = "landscape"
                raw.append(("landscape_start", None))
            elif tok.kind == "landscape_end":
                self._current_orientation = "portrait"
                raw.append(("landscape_end", None))
            elif tok.kind == "fit_page_start":
                raw.append(("fit_page_start", None))
            elif tok.kind == "fit_page_end":
                raw.append(("fit_page_end", None))
            elif tok.kind == "footnotes":
                if self._footnote_order:
                    fn_items = [self._hr()]
                    fn_items.append(Paragraph("Notes", self.S["h4"]))
                    for idx, key in enumerate(self._footnote_order, 1):
                        fn_text = self._footnote_defs.get(key, "")
                        c = self.PRIMARY.hexval()
                        fn_items.append(Paragraph(
                            f'<font color="{c}"><super>{idx}</super></font> {self._fmt(fn_text)}',
                            self.S["footnote"],
                        ))
                    raw.append(("content", KeepTogether(fn_items)))

        # Walk raw and stitch headings with their content
        first_h1 = True
        first_h2 = True
        i = 0
        while i < len(raw):
            kind, obj = raw[i]

            if kind == "h1":
                text, anchor_tag = obj if isinstance(obj, tuple) else (obj, "")
                was_first = first_h1
                if first_h1:
                    first_h1 = False
                    if self._chapter_page:
                        story.append(NextPageTemplate("ChapterPage"))
                else:
                    if self._chapter_page:
                        story.append(NextPageTemplate("ChapterPage"))
                    # Suppress PageBreak if the next landscape_start
                    # adds its own PageBreak (avoid double-break)
                    next_is_break = (i + 1 < len(raw)
                                     and raw[i + 1][0] in ("landscape_start",))
                    if not next_is_break:
                        story.append(PageBreak())
                # Reset first_h2 — the first ## after each # stays on the same page
                first_h2 = True

                # Chapter divider page (--chapter-page in merge mode)
                if self._chapter_page:
                    # Centered chapter title on its own page
                    cp_style = ParagraphStyle(
                        "ChapterTitle", parent=self.S["h1"],
                        fontSize=28, leading=34, alignment=1,
                        spaceBefore=0, spaceAfter=0,
                    )
                    _, ch_ph = self.page_size
                    _cmt, _cmb, _, _ = self._margins
                    story.append(Spacer(1, (ch_ph - _cmt - _cmb - 80) / 2))
                    story.append(HRFlowable(
                        width="50%", thickness=2, color=self.PRIMARY,
                        hAlign="CENTER", spaceAfter=8))
                    if anchor_tag:
                        anchor_name = anchor_tag.split('"')[1]
                        story.append(AnchorFlowable(anchor_name, self._page_tracker))
                    story.append(BookmarkFlowable(text, level=0))
                    story.append(SectionTracker(text, "_running_chapter"))
                    # Chapter subtitle/author from metadata
                    meta = getattr(self, '_file_meta', [])
                    file_num = sum(1 for k2, _ in raw[:i] if k2 == "h1")
                    fm = meta[file_num] if file_num < len(meta) else {}
                    story.append(Paragraph(anchor_tag + text, cp_style))
                    if fm.get("subtitle"):
                        sub_style = ParagraphStyle(
                            "ChapterSub", fontName="DejaVu", fontSize=12,
                            leading=16, alignment=1, textColor=MEDIUM_TEXT,
                            spaceBefore=4)
                        story.append(Paragraph(fm["subtitle"], sub_style))
                    if fm.get("author"):
                        auth_style = ParagraphStyle(
                            "ChapterAuth", fontName="DejaVuIt", fontSize=10,
                            leading=14, alignment=1, textColor=MEDIUM_TEXT,
                            spaceBefore=6)
                        story.append(Paragraph(fm["author"], auth_style))
                    story.append(Spacer(1, 8))
                    story.append(HRFlowable(
                        width="50%", thickness=2, color=self.PRIMARY,
                        hAlign="CENTER"))
                    story.append(NextPageTemplate("Normal"))
                    story.append(PageBreak())
                    i += 1
                    continue

                bar = HRFlowable(
                    width="100%", thickness=2, color=self.PRIMARY, spaceAfter=2 * mm,
                )
                # H1 + first following element in KeepTogether
                h1_group = [bar]
                h1_group.append(BookmarkFlowable(text, level=0))
                if anchor_tag:
                    anchor_name = anchor_tag.split('"')[1]
                    h1_group.append(AnchorFlowable(anchor_name, self._page_tracker))
                h1_group.append(SectionTracker(text, "_running_chapter"))
                h1_group.append(Paragraph(anchor_tag + text, self.S["h1"]))
                j = i + 1
                # H2 is handled separately — don't include
                h1_stop = self._KT_STOP | {"h2"}
                j = self._greedy_collect(raw, j, h1_group, stop_kinds=h1_stop)
                story.append(KeepTogether(h1_group))
                i = j
                continue

            if kind == "h2":
                text, anchor_tag = obj
                # Group h2 + first following element in KeepTogether
                # so h2 doesn't end up orphaned at the bottom of the page
                h2_group = [BookmarkFlowable(text, level=1)]
                if anchor_tag:
                    anchor_name = anchor_tag.split('"')[1]
                    h2_group.append(AnchorFlowable(anchor_name, self._page_tracker))
                h2_group.append(SectionTracker(text))
                h2_group.append(Paragraph(anchor_tag + text, self.S["h2"]))
                j = self._greedy_collect(raw, i + 1, h2_group)

                if first_h2:
                    first_h2 = False
                elif self._h2_break == "always":
                    story.append(PageBreak())
                elif self._h2_break == "auto":
                    # Conditional break: new page only if there's little room
                    story.append(CondPageBreak(80))

                story.append(KeepTogether(h2_group))
                i = j
                continue

            if kind == "h3":
                # Conditional break: if < 40pt remains — break
                story.append(CondPageBreak(40))
                h3_group = [BookmarkFlowable(obj.text, level=2), obj]
                j = self._greedy_collect(raw, i + 1, h3_group)
                story.append(KeepTogether(h3_group))
                i = j
                continue

            if kind == "h4":
                story.append(CondPageBreak(35))
                h4_group = [BookmarkFlowable(obj.text, level=3), obj]
                j = self._greedy_collect(raw, i + 1, h4_group)
                story.append(KeepTogether(h4_group))
                i = j
                continue

            # Float image: collect following elements for the wrap
            if kind == "float_image":
                img_flowable, side, cap = obj
                wrap_flowables = []
                # Caption below the image — first wrapped element
                if cap:
                    wrap_flowables.append(cap)
                _MAX_FLOAT_WRAP = 5  # max wrap elements
                j = i + 1
                while j < len(raw) and len(wrap_flowables) < _MAX_FLOAT_WRAP:
                    nk, no = raw[j]
                    if nk in ("h1", "h2", "h3", "h4", "float_image",
                              "landscape_start", "landscape_end",
                              "fit_page_start", "fit_page_end"):
                        break
                    wrap_flowables.append(no)
                    j += 1
                from reportlab.platypus import ImageAndFlowables
                padding = 3 * mm
                iaf = ImageAndFlowables(
                    img_flowable, wrap_flowables,
                    imageSide=side,
                    imageLeftPadding=padding if side == "right" else 0,
                    imageRightPadding=padding if side == "left" else 0,
                    imageBottomPadding=padding,
                )
                story.append(iaf)
                i = j
                continue

            # Explicit page break
            if kind == "pagebreak":
                story.append(PageBreak())
                i += 1
                continue

            # Landscape: switch page template
            if kind == "landscape_start":
                self._current_orientation = "landscape"
                story.append(NextPageTemplate("Landscape"))
                story.append(PageBreak())
                # Suppress next heading's PageBreak (landscape already broke)
                if i + 1 < len(raw):
                    nk_next = raw[i + 1][0]
                    if nk_next == "h1" and not first_h1:
                        first_h1 = True
                    elif nk_next == "h2" and not first_h2:
                        first_h2 = True
                i += 1
                continue

            if kind == "landscape_end":
                self._current_orientation = "portrait"
                # If next is h2 → landscape_start, don't switch to Normal:
                # the h2 handler will switch to Landscape itself, avoiding an empty Normal page
                next_h2_landscape = (
                    i + 1 < len(raw) and raw[i + 1][0] == "h2" and
                    i + 2 < len(raw) and raw[i + 2][0] == "landscape_start"
                )
                if next_h2_landscape:
                    # Don't add Normal+PageBreak — h2 handler will add Landscape+PageBreak
                    i += 1
                    continue
                story.append(NextPageTemplate("Normal"))
                story.append(PageBreak())
                # Suppress next heading's PageBreak
                if i + 1 < len(raw):
                    nk_next = raw[i + 1][0]
                    if nk_next == "h1" and not first_h1:
                        first_h1 = True
                    elif nk_next == "h2" and not first_h2:
                        first_h2 = True
                i += 1
                continue

            # Fit-page: sentinel markers
            if kind == "fit_page_start":
                story.append(_FitPageStart(
                    getattr(self, '_current_orientation', 'portrait')))
                i += 1
                continue

            if kind == "fit_page_end":
                story.append(_FitPageEnd())
                i += 1
                continue

            # Regular content
            story.append(obj)
            i += 1

        # Post-process: :::fit-page → KeepInFrame(mode='shrink')
        story = self._apply_fit_page(story)

        return story

    # ── Main method ──

    def _create_doc(self, output):
        """Creates a BaseDocTemplate with page templates."""
        pw, ph = self.page_size
        mt, mb, ml, mr = self._margins
        doc = BaseDocTemplate(
            output, pagesize=self.page_size,
            topMargin=mt, bottomMargin=mb,
            leftMargin=ml, rightMargin=mr,
        )
        templates = []
        if self.show_cover:
            cover_frame = Frame(ml, mb, pw - ml - mr, ph - mt - mb, id="cover")
            templates.append(
                PageTemplate(id="Cover", frames=cover_frame, onPage=self._draw_cover)
            )
        normal_frame = Frame(ml, mb, pw - ml - mr, ph - mt - mb, id="normal")
        templates.append(
            PageTemplate(id="Normal", frames=normal_frame,
                         onPageEnd=self._draw_page)
        )
        # Chapter divider page template (no header)
        chapter_frame = Frame(ml, mb, pw - ml - mr, ph - mt - mb, id="chapter_f")
        templates.append(
            PageTemplate(id="ChapterPage", frames=chapter_frame,
                         onPageEnd=self._draw_chapter_page)
        )
        # Landscape template (landscape orientation for some pages)
        lw, lh = self._landscape_size
        landscape_frame = Frame(ml, mb, lw - ml - mr, lh - mt - mb, id="landscape_f")
        templates.append(
            PageTemplate(id="Landscape", frames=landscape_frame,
                         onPageEnd=self._draw_page,
                         pagesize=self._landscape_size)
        )
        doc.addPageTemplates(templates)

        # PDF metadata
        doc.title = self._header_text
        doc.author = self._author
        doc.subject = self.subtitle
        doc.creator = "md2pdf"
        doc._running_header = ""

        return doc

    def render(self, title: str, toc_items: list[str],
               tokens: list[MdToken], output_path: str,
               md_dir: str = ".", on_progress=None,
               footnote_defs: dict = None,
               cover_top: str = None,
               image_dir: str = None,
               md_hash: str = ""):
        """Builds the PDF from parsed tokens (two-pass for TOC with page numbers)."""
        global W, H
        W, H = self.page_size
        self._landscape_size = landscape(self.page_size)
        self._current_orientation = "portrait"
        self._md_dir = md_dir
        self._image_dir = image_dir
        self._md_hash = md_hash
        self._page_tracker = {}
        self._footnote_defs = footnote_defs or {}
        self._footnote_order = []

        if on_progress:
            on_progress("build", "Building document...")

        # Extract metadata for the cover
        m = re.match(
            r"(Lecture|Topic|Class|Lesson|Chapter|Section|Module|Unit|Part)\s+(\d+)[.\s:]+(.+)",
            title, re.IGNORECASE,
        )
        if m:
            self._cover_top = f"{m.group(1).upper()} {m.group(2)}"
            self._cover_title = m.group(3).strip()
        else:
            self._cover_top = ""
            self._cover_title = title

        # Override cover top text from argument
        if cover_top is not None:
            self._cover_top = cover_top

        # Merge mode: file names (level 1) on the cover
        # Normal mode: H2 sections (level 2)
        lvl_1 = [t for lvl, t in toc_items if lvl == 1]
        self._cover_topics = lvl_1 if lvl_1 else [t for lvl, t in toc_items if lvl == 2]
        self._header_text = title

        # Pass 1: collect page numbers for the TOC
        if self.show_toc and toc_items:
            import io
            self._section_counter = 0
            self._footnote_order = []
            self._current_orientation = "portrait"
            BookmarkFlowable._last_level = -1
            story1 = self._build_story(toc_items, tokens, pass_num=1)
            buf = io.BytesIO()
            doc1 = self._create_doc(buf)
            doc1.build(story1)

        # Pass 2: final PDF with TOC page numbers
        self._section_counter = 0
        self._footnote_order = []
        self._current_orientation = "portrait"
        BookmarkFlowable._last_level = -1
        story = self._build_story(toc_items, tokens, pass_num=2)

        if on_progress:
            on_progress("write", f"Writing PDF → {output_path}")

        doc = self._create_doc(output_path)
        custom_meta = {"CopyUUID": self._copy_uuid}
        if self._md_hash:
            custom_meta["SourceSHA256"] = f"sha256:{self._md_hash}"
        if self._author:
            custom_meta["DocumentAuthor"] = self._author
        doc.build(story, canvasmaker=_make_canvas_factory(custom_meta))


# ══════════════════════════════════════════════════════════════════
# HTML RENDERER
# ══════════════════════════════════════════════════════════════════

class HtmlRenderer:
    """Renders tokens into a standalone HTML file."""

    # Greek and math symbols (duplicated from StudyGuidePDF)
    _GREEK = StudyGuidePDF._GREEK
    _MATH_SYMBOLS = StudyGuidePDF._MATH_SYMBOLS
    _LANG_KEYWORDS = StudyGuidePDF._LANG_KEYWORDS
    _LANG_ALIASES = StudyGuidePDF._LANG_ALIASES
    _SYNTAX_COLORS = StudyGuidePDF._SYNTAX_COLORS

    def __init__(self, theme_name="teal", title=""):
        self._theme = THEMES.get(theme_name, THEMES["teal"])
        self._title = title
        self._footnote_defs = {}
        self._footnote_order = []

    def _math_html(self, expr):
        """LaTeX subset → HTML."""
        for name, char in self._GREEK.items():
            expr = expr.replace(f"\\{name}", char)
        for name, char in self._MATH_SYMBOLS.items():
            expr = expr.replace(f"\\{name}", char)
        expr = re.sub(r"\\frac\{([^}]+)\}\{([^}]+)\}",
                       r'<sup>\1</sup>&frasl;<sub>\2</sub>', expr)
        expr = re.sub(r"\^\{([^}]+)\}", r"<sup>\1</sup>", expr)
        expr = re.sub(r"_\{([^}]+)\}", r"<sub>\1</sub>", expr)
        expr = re.sub(r"\^(\w)", r"<sup>\1</sup>", expr)
        expr = re.sub(r"_(\w)", r"<sub>\1</sub>", expr)
        return expr

    _HTML_ESCAPE_MAP = [
        ("\\\\", "\x00BSLASH\x00"),
        ("\\*", "\x00STAR\x00"),
        ("\\#", "\x00HASH\x00"),
        ("\\`", "\x00TICK\x00"),
        ("\\[", "\x00LBRA\x00"),
        ("\\]", "\x00RBRA\x00"),
        ("\\~", "\x00TILDE\x00"),
        ("\\^", "\x00CARET\x00"),
    ]
    _HTML_RESTORE_MAP = [
        ("\x00BSLASH\x00", "\\"),
        ("\x00STAR\x00", "*"),
        ("\x00HASH\x00", "#"),
        ("\x00TICK\x00", "`"),
        ("\x00LBRA\x00", "["),
        ("\x00RBRA\x00", "]"),
        ("\x00TILDE\x00", "~"),
        ("\x00CARET\x00", "^"),
    ]

    def _fmt(self, text):
        """Inline Markdown → HTML."""
        for esc, sentinel in self._HTML_ESCAPE_MAP:
            text = text.replace(esc, sentinel)
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Inline code
        text = re.sub(r"`([^`]+)`",
                       r'<code>\1</code>', text)
        # Strikethrough
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
        # Subscript / superscript (no spaces inside)
        text = re.sub(r"~([^~\s]+)~", r"<sub>\1</sub>", text)
        text = re.sub(r"\^([^^\s]+)\^", r"<sup>\1</sup>", text)
        # Bold italic / bold / italic
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                       r'<a href="\2">\1</a>', text)
        # Inline formulas
        text = re.sub(r"\$([^$]+)\$", lambda m: self._math_html(m.group(1)), text)
        # Footnotes
        def _fn_replace(m):
            key = m.group(1)
            if key in self._footnote_defs:
                if key not in self._footnote_order:
                    self._footnote_order.append(key)
                num = self._footnote_order.index(key) + 1
                return f'<sup class="fn-ref">{num}</sup>'
            return m.group(0)
        text = re.sub(r"\[\^([\w.-]+)\]", _fn_replace, text)
        for sentinel, char in self._HTML_RESTORE_MAP:
            text = text.replace(sentinel, char)
        return text

    def _get_lang_spec(self, lang):
        if not lang:
            return None
        lang = self._LANG_ALIASES.get(lang, lang)
        return self._LANG_KEYWORDS.get(lang)

    def _highlight_code(self, text, lang):
        """Code highlighting for HTML."""
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lang_spec = self._get_lang_spec(lang)
        if not lang_spec:
            return escaped
        lines = escaped.split("\n")
        result = []
        for line in lines:
            if not line.strip():
                result.append(line)
                continue
            n = len(line)
            colors = [None] * n
            string_pat = lang_spec.get("string", "")
            if string_pat:
                for m in re.finditer(string_pat, line):
                    for j in range(m.start(), min(m.end(), n)):
                        colors[j] = "string"
            comment_pat = lang_spec.get("comment", "")
            if comment_pat:
                for m in re.finditer(comment_pat, line):
                    for j in range(m.start(), min(m.end(), n)):
                        colors[j] = "comment"
            for m in re.finditer(r"\b\d+(?:\.\d+)?\b", line):
                if all(colors[j] is None for j in range(m.start(), m.end())):
                    for j in range(m.start(), m.end()):
                        colors[j] = "number"
            kw_pattern = r"\b(" + "|".join(re.escape(k) for k in lang_spec["keywords"]) + r")\b"
            flags = re.IGNORECASE if lang_spec.get("case_insensitive") else 0
            for m in re.finditer(kw_pattern, line, flags):
                if all(colors[j] is None for j in range(m.start(), m.end())):
                    for j in range(m.start(), m.end()):
                        colors[j] = "keyword"
            parts = []
            cur = None
            for j in range(n):
                if colors[j] != cur:
                    if cur is not None:
                        parts.append("</span>")
                    cur = colors[j]
                    if cur is not None:
                        parts.append(f'<span class="hl-{cur}">')
                parts.append(line[j])
            if cur is not None:
                parts.append("</span>")
            result.append("".join(parts))
        return "\n".join(result)

    def _chart_html(self, text):
        """Renders a ```chart block into <img> with base64 PNG."""
        import base64 as _b64
        spec = _parse_chart_spec(text)
        P = self._theme
        palette = [
            P["primary"], P["secondary"], P["accent"],
            _lighten(P["primary"]), _lighten(P["secondary"]), _lighten(P["accent"]),
            _lighten(P["primary"], 0.6), _lighten(P["secondary"], 0.6),
            _lighten(P["accent"], 0.6),
        ]
        png = _render_chart_png(spec, palette)
        if png is None:
            return '<p><em style="color:#999">Chart: install matplotlib — pip install matplotlib</em></p>'
        b64 = _b64.b64encode(png).decode("ascii")
        title_attr = f' title="{spec["title"]}"' if spec["title"] else ""
        cap = f'<figcaption>{spec["title"]}</figcaption>' if spec["title"] else ""
        return f'<figure class="chart"><img src="data:image/png;base64,{b64}" alt="chart"{title_attr}>{cap}</figure>'

    def render(self, title, toc_items, tokens, output_path, footnote_defs=None,
               md_dir=".", image_dir=None):
        """Generates a standalone HTML file."""
        self._footnote_defs = footnote_defs or {}
        self._footnote_order = []
        self._md_dir = md_dir
        self._image_dir = image_dir
        P = self._theme
        primary = P["primary"]
        parts = []

        for tok in tokens:
            if tok.kind == "h1":
                parts.append(f'<h1>{self._fmt(tok.text)}</h1>')
            elif tok.kind == "h2":
                parts.append(f'<h2>{self._fmt(tok.text)}</h2>')
            elif tok.kind == "h3":
                parts.append(f'<h3>{self._fmt(tok.text)}</h3>')
            elif tok.kind == "h4":
                parts.append(f'<h4>{self._fmt(tok.text)}</h4>')
            elif tok.kind == "body":
                parts.append(f'<p>{self._fmt(tok.text)}</p>')
            elif tok.kind == "bullet":
                indent = "margin-left:{}em".format(tok.level * 2)
                parts.append(f'<ul style="{indent}"><li>{self._fmt(tok.text)}</li></ul>')
            elif tok.kind == "numbered":
                indent = f' style="margin-left:{tok.level * 2}em"' if tok.level else ""
                parts.append(f'<ol start="{tok.num}"{indent}><li>{self._fmt(tok.text)}</li></ol>')
            elif tok.kind == "checkbox":
                chk = "checked" if tok.checked else ""
                indent = "margin-left:{}em".format(tok.level * 2)
                parts.append(f'<div class="checkbox" style="{indent}">'
                             f'<input type="checkbox" disabled {chk}> {self._fmt(tok.text)}</div>')
            elif tok.kind == "quote":
                parts.append(f'<blockquote>{self._fmt(tok.text)}</blockquote>')
            elif tok.kind == "admonition":
                _ADM_BORDER = {"note": "#4393E4", "warning": "#D29922",
                               "tip": "#4AC26B", "important": "#A855F7",
                               "caution": "#E5534B"}
                _ADM_BG = {"note": "#DCEEFB", "warning": "#FFF2D5",
                           "tip": "#D6F5DD", "important": "#EDE3FB",
                           "caution": "#FCDAD8"}
                _ADM_LABELS = {"note": "Note", "warning": "Warning",
                               "tip": "Tip", "important": "Important",
                               "caution": "Caution"}
                aborder = _ADM_BORDER.get(tok.admonition_type, "#4393E4")
                abg = _ADM_BG.get(tok.admonition_type, "#DCEEFB")
                alabel = _ADM_LABELS.get(tok.admonition_type, "Note")
                parts.append(f'<div class="admonition adm-{tok.admonition_type}" '
                             f'style="border-left:4px solid {aborder};'
                             f'background:{abg};padding:0.8em 1em;margin:1em 0">'
                             f'<strong>{alabel}</strong>'
                             f'<p>{self._fmt(tok.text)}</p></div>')
            elif tok.kind == "definition":
                parts.append(f'<dl><dt><strong>{self._fmt(tok.alt)}</strong></dt>'
                             f'<dd>{self._fmt(tok.text)}</dd></dl>')
            elif tok.kind == "pagebreak":
                parts.append('<div style="page-break-after:always"></div>')
            elif tok.kind == "code":
                highlighted = self._highlight_code(tok.text, tok.lang)
                lang_label = f' data-lang="{tok.lang}"' if tok.lang else ""
                parts.append(f'<pre{lang_label}><code>{highlighted}</code></pre>')
            elif tok.kind == "chart":
                parts.append(self._chart_html(tok.text))
            elif tok.kind == "table":
                tbl = ['<figure>']
                if tok.caption:
                    tbl.append(f'<figcaption>{self._fmt(tok.caption)}</figcaption>')
                tbl.append('<table>')
                if tok.headers:
                    tbl.append('<thead><tr>')
                    for i, h in enumerate(tok.headers):
                        align = ""
                        if tok.alignments and i < len(tok.alignments):
                            align = f' style="text-align:{tok.alignments[i]}"'
                        tbl.append(f'<th{align}>{self._fmt(h)}</th>')
                    tbl.append('</tr></thead>')
                tbl.append('<tbody>')
                for row in (tok.rows or []):
                    tbl.append('<tr>')
                    for i, cell in enumerate(row):
                        align = ""
                        if tok.alignments and i < len(tok.alignments):
                            align = f' style="text-align:{tok.alignments[i]}"'
                        tbl.append(f'<td{align}>{self._fmt(cell)}</td>')
                    tbl.append('</tr>')
                tbl.append('</tbody></table></figure>')
                parts.append("\n".join(tbl))
            elif tok.kind == "image":
                img_path = StudyGuidePDF._resolve_image_path(
                    tok.path, self._md_dir, self._image_dir) if tok.path else tok.path
                cap = f'<figcaption>{self._fmt(tok.alt)}</figcaption>' if tok.alt else ""
                styles = []
                if tok.width is not None:
                    styles.append(f"width:{tok.width}%")
                if tok.float_side:
                    styles.append(f"float:{tok.float_side}")
                    if tok.float_side == "left":
                        styles.append("margin:0 1em 0.5em 0")
                    else:
                        styles.append("margin:0 0 0.5em 1em")
                style_attr = f' style="{"; ".join(styles)}"' if styles else ""
                parts.append(f'<figure{style_attr}><img src="{img_path}" alt="{tok.alt}">{cap}</figure>')
            elif tok.kind == "hr":
                parts.append('<hr>')
            elif tok.kind == "math":
                parts.append(f'<div class="math">{self._math_html(tok.text)}</div>')
            elif tok.kind == "columns":
                inner_lines = tok.text.split("\n")
                # Simple render: split by blank line or evenly
                parts.append(f'<div class="columns" style="column-count:{tok.level}">')
                for line in inner_lines:
                    if line.strip():
                        parts.append(f'<p>{self._fmt(line)}</p>')
                parts.append('</div>')
            elif tok.kind == "landscape_start":
                parts.append('<div class="landscape-page">')
            elif tok.kind == "landscape_end":
                parts.append('</div>')
            elif tok.kind == "fit_page_start":
                parts.append('<div class="fit-page">')
            elif tok.kind == "fit_page_end":
                parts.append('</div>')
            elif tok.kind == "footnotes":
                if self._footnote_order:
                    parts.append('<hr><section class="footnotes"><h4>Notes</h4><ol>')
                    for key in self._footnote_order:
                        fn_text = self._footnote_defs.get(key, "")
                        parts.append(f'<li>{self._fmt(fn_text)}</li>')
                    parts.append('</ol></section>')

        body = "\n".join(parts)
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
:root {{
  --primary: {primary};
  --primary-light: {P["primary_light"]};
  --border: {P["border"]};
  --table-alt: {P["table_alt"]};
}}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 900px; margin: 0 auto; padding: 2em;
  line-height: 1.6; color: #333;
}}
h1 {{ color: var(--primary); border-bottom: 2px solid var(--primary); padding-bottom: 0.3em; clear: both; }}
h2 {{ color: var(--primary); margin-top: 1.5em; clear: both; }}
h3, h4 {{ color: var(--primary); clear: both; }}
a {{ color: var(--primary); }}
code {{
  background: #F9F2F4; color: #C7254E;
  padding: 2px 6px; border-radius: 3px; font-size: 0.9em;
}}
pre {{
  background: #F8F9FA; border: 1px solid #E0E0E0;
  border-radius: 6px; padding: 1em; overflow-x: auto;
  line-height: 1.5;
}}
pre code {{ background: none; color: inherit; padding: 0; }}
blockquote {{
  border-left: 4px solid var(--primary); margin: 1em 0;
  padding: 0.5em 1em; background: var(--primary-light);
}}
table {{
  border-collapse: collapse; width: 100%; margin: 1em 0;
}}
th, td {{ border: 1px solid var(--border); padding: 8px 12px; }}
th {{ background: var(--primary); color: white; }}
tr:nth-child(even) {{ background: var(--table-alt); }}
figcaption {{ text-align: center; font-style: italic; color: #666; font-size: 0.9em; margin: 0.5em 0; }}
figure {{ margin: 1em 0; }}
figure img {{ max-width: 100%; height: auto; }}
.math {{ text-align: center; font-size: 1.1em; margin: 1em 0; }}
.columns {{ column-gap: 2em; }}
.landscape-page {{ background: #FAFCFF; padding: 1em; border-left: 3px solid var(--primary-light); margin: 1em 0; }}
.fit-page {{ border: 1px dashed var(--border); padding: 1em; margin: 1em 0; }}
@media print {{ .fit-page {{ page-break-inside: avoid; }} }}
@media print {{ @page landscape {{ size: landscape; }} .landscape-page {{ page: landscape; break-before: page; break-after: page; }} }}
.checkbox {{ margin: 0.3em 0; }}
.fn-ref {{ color: var(--primary); cursor: pointer; }}
.footnotes {{ font-size: 0.85em; color: #666; }}
.footnotes ol {{ padding-left: 1.5em; }}
hr {{ border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }}
dl {{ margin: 0.5em 0; }}
dt {{ font-weight: bold; }}
dd {{ margin-left: 1.5em; margin-bottom: 0.5em; }}
.admonition {{ border-radius: 6px; }}
.admonition p {{ margin: 0.3em 0 0 0; }}
.hl-keyword {{ color: {self._SYNTAX_COLORS['keyword']}; }}
.hl-string {{ color: {self._SYNTAX_COLORS['string']}; }}
.hl-comment {{ color: {self._SYNTAX_COLORS['comment']}; font-style: italic; }}
.hl-number {{ color: {self._SYNTAX_COLORS['number']}; }}
.hl-builtin {{ color: {self._SYNTAX_COLORS['builtin']}; }}
del {{ text-decoration: line-through; }}
</style>
</head>
<body>
<h1>{title}</h1>
{body}
</body>
</html>"""

        Path(output_path).write_text(html, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def _print_dry_run(input_path, title, toc_items, tokens):
    """Prints the parsing result without generating a PDF."""
    print(f"\n  === DRY RUN: {input_path.name} ===")
    print(f"  Title: {title}")
    print(f"  TOC sections: {len(toc_items)}")
    for lvl, item_text in toc_items:
        indent = "    " if lvl == 2 else "      "
        print(f"{indent}- {item_text}")
    print(f"  Tokens: {len(tokens)}")
    kinds = {}
    for t in tokens:
        kinds[t.kind] = kinds.get(t.kind, 0) + 1
    for k, v in sorted(kinds.items()):
        print(f"    {k}: {v}")
    print()


def _progress_printer(step, message):
    """Callback that prints build stages."""
    icons = {"parse": "[1/3]", "build": "[2/3]", "write": "[3/3]"}
    print(f"  {icons.get(step, '[…]')} {message}")


def _process_one_file(input_path, args, output_path=None):
    """Processes a single .md file."""
    import copy
    args = copy.copy(args)  # protect against mutation in batch mode
    # Extension validation
    if input_path.suffix.lower() not in (".md", ".markdown", ".txt"):
        print(f"  Warning: file {input_path.name} is not .md — continuing")

    # Read with encoding-error handling
    try:
        md_text = input_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  Warning: {input_path.name} is not UTF-8, trying with errors='replace'")
        md_text = input_path.read_text(encoding="utf-8", errors="replace")

    md_hash = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    # YAML front matter
    front_matter, md_text = parse_front_matter(md_text)

    # Template (front matter > CLI > default)
    template_name = front_matter.pop("template", None) or getattr(args, "template", None)
    if template_name and template_name in DOC_TEMPLATES:
        tmpl = DOC_TEMPLATES[template_name]
        for key, val in tmpl.items():
            # Template sets default unless CLI overrode it explicitly
            attr = key.replace("-", "_")
            if not hasattr(args, f"_explicit_{attr}"):
                setattr(args, attr, val)

    # Front matter overrides everything
    _FM_BOOL_MAP = {"cover": "no_cover", "toc": "no_toc", "justify": "no_justify",
                     "code_line_numbers": "no_line_numbers"}
    for key, val in front_matter.items():
        attr = key.replace("-", "_")
        if attr in _FM_BOOL_MAP:
            # Inverted flags: cover=true → no_cover=False
            setattr(args, _FM_BOOL_MAP[attr], not val if isinstance(val, bool) else val != "true")
        elif attr == "no_watermark" and isinstance(val, bool):
            args.no_watermark = val
        elif hasattr(args, attr):
            setattr(args, attr, val)

    _progress_printer("parse", f"Parsing {input_path.name}...")
    title, toc_items, tokens, footnote_defs = parse_markdown(md_text)
    if not title:
        title = input_path.stem.replace("_", " ")
    # --title overrides title from file
    if getattr(args, "title", None):
        title = args.title

    # Dry run
    if args.dry_run:
        _print_dry_run(input_path, title, toc_items, tokens)
        return

    out = output_path or str(input_path.with_suffix(".pdf"))

    print(f"  File:       {input_path.name}")
    print(f"  Title:      {title}")
    print(f"  Sections:   {sum(1 for lvl, _ in toc_items if lvl == 2)}")
    print(f"  Tokens:     {len(tokens)}")
    print(f"  Theme:      {args.theme}")
    watermark = "" if args.no_watermark else args.watermark
    if watermark:
        print(f"  Watermark: {watermark}")

    renderer = StudyGuidePDF(
        theme_name=args.theme,
        show_cover=not args.no_cover,
        show_toc=not args.no_toc,
        watermark=watermark,
        subtitle=args.subtitle,
        author=getattr(args, "author", ""),
        duplex=getattr(args, "duplex", False),
        cover_image=getattr(args, "cover_image", None),
        toc_depth=getattr(args, "toc_depth", 2),
        page_size=getattr(args, "page_size", "a4"),
        justify=not getattr(args, "no_justify", False),
        code_line_numbers=not getattr(args, "no_line_numbers", False),
        margins=getattr(args, "margins", "medium"),
        h2_break=getattr(args, "h2_break", "always"),
        copy_id=getattr(args, "copy_id", False),
        show_qr=getattr(args, "qr", False),
        cover_author=not getattr(args, "no_cover_author", False),
        cover_pattern=getattr(args, "cover_pattern", "circles"),
    )
    image_dir = getattr(args, "image_dir", None)
    renderer.render(title, toc_items, tokens, out,
                    md_dir=str(input_path.parent), on_progress=_progress_printer,
                    footnote_defs=footnote_defs,
                    cover_top=getattr(args, "cover_top", None),
                    image_dir=image_dir,
                    md_hash=md_hash)

    print(f"  ✓ PDF created: {out}")

    # HTML preview
    if getattr(args, "html", False):
        html_out = str(input_path.with_suffix(".html"))
        html_renderer = HtmlRenderer(theme_name=args.theme, title=title)
        html_renderer.render(title, toc_items, tokens, html_out, footnote_defs,
                             md_dir=str(input_path.parent), image_dir=image_dir)
        print(f"  ✓ HTML created: {html_out}")

    # First-page preview (for GUI)
    if getattr(args, "preview", False):
        import tempfile
        preview_tokens = tokens[:15]  # first 15 tokens
        _tf = tempfile.NamedTemporaryFile(suffix=".pdf", prefix="md2pdf_preview_", delete=False)
        preview_out = _tf.name
        _tf.close()
        preview_renderer = StudyGuidePDF(
            theme_name=args.theme,
            show_cover=not args.no_cover,
            show_toc=False,
            watermark="",
            subtitle=args.subtitle,
            page_size=getattr(args, "page_size", "a4"),
            margins=getattr(args, "margins", "medium"),
        )
        preview_renderer.render(title, [], preview_tokens, preview_out,
                                md_dir=str(input_path.parent),
                                footnote_defs=footnote_defs,
                                image_dir=image_dir)
        print(f"PREVIEW:{preview_out}")

    print()


def _process_merged_files(input_paths, args):
    """Merges several .md files into one PDF with shared cover and TOC."""
    combined_toc_items = []
    combined_tokens = []
    combined_footnote_defs = {}
    file_meta = []  # [{subtitle, author}, ...] per file
    merged_title = None
    skipped = []
    h2_global = 0  # global H2 counter for --renumber
    all_raw_texts = []  # for SHA-256

    for file_idx, input_path in enumerate(input_paths):
        # --- 1. Per-file error handling ---
        try:
            try:
                md_text = input_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                md_text = input_path.read_text(encoding="utf-8", errors="replace")

            all_raw_texts.append(md_text)
            front_matter, md_text = parse_front_matter(md_text)

            # First file: front matter defines settings for the merged document
            if file_idx == 0 and front_matter:
                _FM_BOOL_MAP = {"cover": "no_cover", "toc": "no_toc",
                                "justify": "no_justify",
                                "code_line_numbers": "no_line_numbers"}
                for key, val in front_matter.items():
                    attr = key.replace("-", "_")
                    if attr in _FM_BOOL_MAP:
                        if not hasattr(args, f"_explicit_{_FM_BOOL_MAP[attr]}"):
                            setattr(args, _FM_BOOL_MAP[attr],
                                    not val if isinstance(val, bool) else val != "true")
                    elif attr == "template" and val in DOC_TEMPLATES:
                        tmpl = DOC_TEMPLATES[val]
                        for tk, tv in tmpl.items():
                            ta = tk.replace("-", "_")
                            if not hasattr(args, f"_explicit_{ta}"):
                                setattr(args, ta, tv)
                    elif hasattr(args, attr) and not hasattr(args, f"_explicit_{attr}"):
                        setattr(args, attr, val)

            _progress_printer("parse",
                f"Parsing {input_path.name} ({file_idx + 1}/{len(input_paths)})...")
            title, toc_items, tokens, footnote_defs = parse_markdown(md_text)
        except Exception as e:
            print(f"  ⚠ Skipping {input_path.name}: {e}")
            skipped.append(input_path.name)
            file_meta.append({})
            continue

        if not title:
            title = input_path.stem.replace("_", " ")

        # --h1-titles overrides H1 title for each file
        h1_titles = getattr(args, "h1_titles", None)
        if h1_titles and file_idx < len(h1_titles) and h1_titles[file_idx]:
            title = h1_titles[file_idx]

        # First file → merged document title
        if merged_title is None:
            merged_title = title

        # --- 7. Per-file subtitle/author from front matter ---
        fm_subtitle = front_matter.get("subtitle", "")
        fm_author = front_matter.get("author", "")
        file_meta.append({"subtitle": fm_subtitle, "author": fm_author})

        # --- 4. H2 renumber (--renumber) ---
        if getattr(args, "renumber", False):
            h2_local = 0  # reset per chapter
            new_toc = []
            for lvl, text in toc_items:
                if lvl == 2:
                    h2_local += 1
                    m_num = re.match(r"^(\d+)\.\s+(.+)", text)
                    bare = m_num.group(2) if m_num else text
                    text = f"{h2_local}. {bare}"
                new_toc.append((lvl, text))
            toc_items = new_toc
            local_h2 = 0
            for tok in tokens:
                if tok.kind == "h2":
                    local_h2 += 1
                    m_num = re.match(r"^(\d+)\.\s+(.+)", tok.text)
                    bare = m_num.group(2) if m_num else tok.text
                    tok.text = f"{local_h2}. {bare}"

        # H1 of each file → level 1 in TOC
        combined_toc_items.append((1, title))
        combined_toc_items.extend(toc_items)

        # parse_markdown drops the first H1 from tokens → re-insert it
        combined_tokens.append(MdToken("h1", title))

        # Resolve image paths to absolute (files from different directories)
        file_dir = str(input_path.parent)
        image_dir = getattr(args, "image_dir", None)
        for tok in tokens:
            if tok.kind == "image" and tok.path and not os.path.isabs(tok.path):
                tok.path = StudyGuidePDF._resolve_image_path(
                    tok.path, file_dir, image_dir)
            # Inline images in text: ![alt](relative/path)
            if tok.text and "![" in tok.text:
                def _resolve_inline(m, _fd=file_dir, _id=image_dir):
                    alt, path = m.group(1), m.group(2)
                    if not os.path.isabs(path) and not path.startswith(("http://", "https://")):
                        path = StudyGuidePDF._resolve_image_path(path, _fd, _id)
                    return f"![{alt}]({path})"
                tok.text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", _resolve_inline, tok.text)

        # Footnote namespace: prefix with file index
        if footnote_defs:
            prefix = f"f{file_idx}_"
            for key, val in footnote_defs.items():
                combined_footnote_defs[prefix + key] = val
            for tok in tokens:
                if tok.text and "[^" in tok.text:
                    for key in footnote_defs:
                        tok.text = tok.text.replace(f"[^{key}]", f"[^{prefix}{key}]")
            tokens = [t for t in tokens if t.kind != "footnotes"]

        combined_tokens.extend(tokens)

    # Sanity: at least one file processed successfully
    if not combined_tokens:
        print("ERROR: No files could be processed")
        sys.exit(1)

    # Single footnotes sentinel at the end
    if combined_footnote_defs:
        combined_tokens.append(MdToken("footnotes"))

    # --title overrides
    if getattr(args, "title", None):
        merged_title = args.title

    # Dry run
    if args.dry_run:
        n_files = len(input_paths) - len(skipped)
        print(f"\n  === MERGE ({n_files} files) ===")
        print(f"  Title: {merged_title}")
        print(f"  TOC sections: {len(combined_toc_items)}")
        print(f"  Tokens: {len(combined_tokens)}")
        kinds = {}
        for t in combined_tokens:
            kinds[t.kind] = kinds.get(t.kind, 0) + 1
        for k, v in sorted(kinds.items()):
            print(f"    {k}: {v}")
        if skipped:
            print(f"  Skipped: {', '.join(skipped)}")
        return

    # Output path
    if args.output:
        out = args.output
    else:
        out = str(input_paths[0].with_name("merged.pdf"))

    n_files = len(input_paths) - len(skipped)
    print(f"  Mode:       MERGE ({n_files} files)")
    print(f"  Title:      {merged_title}")
    print(f"  Sections:   {sum(1 for lvl, _ in combined_toc_items if lvl == 2)}")
    print(f"  Files:      {sum(1 for lvl, _ in combined_toc_items if lvl == 1)}")
    print(f"  Tokens:     {len(combined_tokens)}")
    print(f"  Theme:      {args.theme}")
    watermark = "" if args.no_watermark else args.watermark
    if watermark:
        print(f"  Watermark: {watermark}")
    if skipped:
        print(f"  Skipped: {', '.join(skipped)}")

    md_hash = hashlib.sha256("\n".join(all_raw_texts).encode("utf-8")).hexdigest()

    renderer = StudyGuidePDF(
        theme_name=args.theme,
        show_cover=not args.no_cover,
        show_toc=not args.no_toc,
        watermark=watermark,
        subtitle=args.subtitle,
        author=getattr(args, "author", ""),
        duplex=getattr(args, "duplex", False),
        cover_image=getattr(args, "cover_image", None),
        toc_depth=getattr(args, "toc_depth", 2),
        page_size=getattr(args, "page_size", "a4"),
        justify=not getattr(args, "no_justify", False),
        code_line_numbers=not getattr(args, "no_line_numbers", False),
        margins=getattr(args, "margins", "medium"),
        h2_break=getattr(args, "h2_break", "always"),
        chapter_page=getattr(args, "chapter_page", False),
        copy_id=getattr(args, "copy_id", False),
        show_qr=getattr(args, "qr", False),
        cover_author=not getattr(args, "no_cover_author", False),
        cover_pattern=getattr(args, "cover_pattern", "circles"),
    )
    # --- 7. Pass per-file metadata for chapter page and TOC ---
    renderer._file_meta = file_meta
    renderer.render(merged_title, combined_toc_items, combined_tokens, out,
                    md_dir=str(input_paths[0].parent), on_progress=_progress_printer,
                    footnote_defs=combined_footnote_defs,
                    cover_top=getattr(args, "cover_top", None),
                    image_dir=getattr(args, "image_dir", None),
                    md_hash=md_hash)

    print(f"  ✓ PDF created: {out}")

    # HTML
    if getattr(args, "html", False):
        html_out = out.replace(".pdf", ".html") if out.endswith(".pdf") else out + ".html"
        html_renderer = HtmlRenderer(theme_name=args.theme, title=merged_title)
        html_renderer.render(merged_title, combined_toc_items, combined_tokens,
                             html_out, combined_footnote_defs,
                             md_dir=str(input_paths[0].parent),
                             image_dir=getattr(args, "image_dir", None))
        print(f"  ✓ HTML created: {html_out}")

    print()


def _verify_hash(pdf_path, md_paths):
    """Verifies SHA-256 hash of the PDF vs source .md files."""
    import re as _re_v
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)
    # Read PDF binary and look for SourceSHA256
    raw = pdf_path.read_bytes()
    m = _re_v.search(rb'/SourceSHA256\s*\(sha256:([0-9a-f]{64})\)', raw)
    if not m:
        print("✗ SourceSHA256 hash not found in PDF.")
        sys.exit(1)
    stored_hash = m.group(1).decode()
    # Compute hash of source files
    if len(md_paths) == 1:
        md_text = md_paths[0].read_text(encoding="utf-8")
    else:
        md_text = "\n".join(p.read_text(encoding="utf-8") for p in md_paths)
    actual_hash = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
    if stored_hash == actual_hash:
        print(f"✓ Hash matches: {stored_hash[:16]}...")
    else:
        print(f"✗ Hash does NOT match!")
        print(f"  PDF:     {stored_hash[:16]}...")
        print(f"  Source:  {actual_hash[:16]}...")
        sys.exit(1)


def _extract_stego_from_pdf(pdf_path):
    """Extracts steganography from images inside the PDF."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)
    found = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    # Convert to PNG
                    png_data = pix.tobytes("png")
                    msg = _extract_stego_lsb(png_data)
                    if msg:
                        found.append((page_num + 1, msg))
                except Exception:
                    pass
        doc.close()
    except ImportError:
        # Fallback: scan for raw PNG signatures
        raw = pdf_path.read_bytes()
        PNG_SIG = b'\x89PNG\r\n\x1a\n'
        PNG_END = b'IEND\xaeB`\x82'
        pos = 0
        while True:
            idx = raw.find(PNG_SIG, pos)
            if idx == -1:
                break
            end_idx = raw.find(PNG_END, idx)
            if end_idx == -1:
                break
            png_data = raw[idx:end_idx + len(PNG_END)]
            try:
                msg = _extract_stego_lsb(png_data)
                if msg:
                    found.append((0, msg))
            except Exception:
                pass
            pos = end_idx + len(PNG_END)
    if found:
        print(f"✓ Steganography found in {len(found)} image(s):")
        for i, (pg, msg) in enumerate(found, 1):
            prefix = f" (page {pg})" if pg else ""
            print(f"  [{i}]{prefix} {msg}")
    else:
        print("✗ No steganography found in PDF images.")


def _inspect_pdf(pdf_path):
    """Prints JSON with the PDF's authorship metadata."""
    import json as _json
    import re as _re_i
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(_json.dumps({"error": f"PDF not found: {pdf_path}"}))
        return
    raw = pdf_path.read_bytes()
    result = {"file": pdf_path.name}
    # CopyUUID
    m = _re_i.search(rb'/CopyUUID\s*\(([^)]+)\)', raw)
    result["uuid"] = m.group(1).decode() if m else ""
    # SourceSHA256
    m = _re_i.search(rb'/SourceSHA256\s*\(sha256:([0-9a-f]{64})\)', raw)
    result["hash"] = f"sha256:{m.group(1).decode()}" if m else ""
    # DocumentAuthor — ReportLab encodes as PDF octal escapes + UTF-16BE BOM
    m = _re_i.search(rb'/DocumentAuthor\s*\(([^)]*)\)', raw)
    author = ""
    if m:
        raw_author = m.group(1)
        # Decode PDF octal escapes: \376 → 0xFE, etc.
        decoded = bytearray()
        i = 0
        while i < len(raw_author):
            if raw_author[i:i+1] == b'\\' and i + 1 < len(raw_author):
                oct_m = _re_i.match(rb'([0-7]{1,3})', raw_author[i+1:])
                if oct_m:
                    decoded.append(int(oct_m.group(1), 8))
                    i += 1 + len(oct_m.group(1))
                    continue
                decoded.append(raw_author[i+1])
                i += 2
            else:
                decoded.append(raw_author[i])
                i += 1
        decoded = bytes(decoded)
        if decoded.startswith(b'\xfe\xff'):
            try:
                author = decoded[2:].decode('utf-16-be')
            except Exception:
                author = decoded.decode('latin-1', errors='replace')
        else:
            author = decoded.decode('utf-8', errors='replace')
    result["author"] = author
    # Steganography
    stego_msgs = []
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    png_data = pix.tobytes("png")
                    msg = _extract_stego_lsb(png_data)
                    if msg:
                        stego_msgs.append(msg)
                except Exception:
                    pass
        doc.close()
    except ImportError:
        pass
    result["stego"] = list(set(stego_msgs))
    result["stego_count"] = len(stego_msgs)
    # Fingerprint — look for micro text (invisible, alpha≈0)
    # Check via pdftotext or search for the characteristic pattern
    has_fp = False
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        if len(doc) > 0:
            # Check the first content page
            for pg_idx in range(min(3, len(doc))):
                text = doc[pg_idx].get_text()
                # Fingerprint contains a YYYY-MM-DD date and uuid
                if _re_i.search(r'\d{4}-\d{2}-\d{2}\s+[0-9a-f]{8}', text):
                    has_fp = True
                    break
        doc.close()
    except Exception:
        pass
    result["fingerprint"] = has_fp
    print(_json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="md2pdf — Markdown → PDF converter for tutorial booklets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python md2pdf.py lecture_3.md
  python md2pdf.py lecture_3.md -o study_guide.pdf --theme blue
  python md2pdf.py input.md --watermark "File by Author"
  python md2pdf.py input.md --no-cover --theme dark
  python md2pdf.py input.md --no-toc --no-watermark
  python md2pdf.py input.md --subtitle "Study guide"
  python md2pdf.py *.md                                   # batch processing
  python md2pdf.py *.md --merge -o book.pdf               # merge into one PDF
  python md2pdf.py *.md --merge --title "Textbook"        # with custom title
  python md2pdf.py *.md --merge --h1-titles "Chapter 1" "Chapter 2"  # custom H1 titles
  python md2pdf.py input.md --dry-run                     # parse only

Available themes: teal (default), blue, purple, red, dark
        """,
    )
    parser.add_argument("input", nargs="+", help="Path to .md file (multiple allowed)")
    parser.add_argument(
        "-o", "--output",
        help="Path to output .pdf (only with a single input file)",
    )
    parser.add_argument(
        "--theme", default="teal",
        help=f"Color theme: {', '.join(THEMES.keys())} (default teal)",
    )
    parser.add_argument("--no-cover", action="store_true", help="No cover")
    parser.add_argument("--no-toc", action="store_true", help="No table of contents")
    parser.add_argument(
        "--toc-depth", type=int, default=2, choices=[2, 3, 4],
        help="TOC depth: 2=only ##, 3=## and ###, 4=## ### #### (default 2)",
    )
    parser.add_argument(
        "--watermark", default="",
        help="Watermark text on every page",
    )
    parser.add_argument("--no-watermark", action="store_true", help="No watermark")
    parser.add_argument(
        "--subtitle", default="Tutorial",
        help="Cover subtitle text (default 'Tutorial')",
    )
    parser.add_argument(
        "--font-dir", default=None,
        help="Path to the directory with DejaVuSans fonts",
    )
    parser.add_argument(
        "--author", default="",
        help="Author name for PDF metadata",
    )
    parser.add_argument(
        "--no-cover-author", action="store_true",
        help="Do not show author on the cover (only in metadata/stego/fingerprint)",
    )
    parser.add_argument(
        "--cover-pattern", default="circles",
        choices=["circles", "diamonds", "lines", "dots", "none"],
        help="Cover pattern: circles, diamonds, lines, dots, none",
    )
    parser.add_argument(
        "--duplex", action="store_true",
        help="Mirrored margins for double-sided printing",
    )
    parser.add_argument(
        "--cover-image", default=None,
        help="Path to an image for the cover background",
    )
    parser.add_argument(
        "--custom-theme", default=None,
        help="Path to a JSON file with a custom theme",
    )
    parser.add_argument(
        "--page-size", default="a4",
        choices=["a4", "a4-landscape", "letter", "letter-landscape", "a3", "a3-landscape"],
        help="Page size (default a4)",
    )
    parser.add_argument(
        "--no-justify", action="store_true",
        help="Left-align instead of justified",
    )
    parser.add_argument(
        "--no-line-numbers", action="store_true",
        help="No line numbers in code blocks",
    )
    parser.add_argument(
        "--margins", default="medium",
        choices=["narrow", "medium", "wide"],
        help="Margin width: narrow, medium, wide (default medium)",
    )
    parser.add_argument(
        "--h2-break", default="always",
        choices=["always", "auto", "never"],
        help="Page break on ##: always (default), auto (conditional), never",
    )
    parser.add_argument(
        "--template", default=None,
        choices=list(DOC_TEMPLATES.keys()),
        help="Document template: " + ", ".join(DOC_TEMPLATES.keys()),
    )
    parser.add_argument(
        "--html", action="store_true",
        help="Also generate an HTML version",
    )
    parser.add_argument(
        "--title", default=None,
        help="Document title (instead of first # from file)",
    )
    parser.add_argument(
        "--cover-top", default=None,
        help="Cover top label (instead of auto-detected 'LECTURE 1' etc.)",
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Generate a first-page preview (for GUI)",
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Watch the file and auto-convert on change",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse only — print tokens without generating a PDF",
    )
    parser.add_argument(
        "--merge", action="store_true",
        help="Merge several .md files into one PDF with shared cover and TOC",
    )
    parser.add_argument(
        "--h1-titles", nargs="+", default=None, metavar="TITLE",
        help="H1 titles per file in merge mode (in file order)",
    )
    parser.add_argument(
        "--renumber", action="store_true",
        help="Renumber H2 headings globally with --merge (1. 2. 3. ...)",
    )
    parser.add_argument(
        "--chapter-page", action="store_true",
        help="Insert a divider page before each chapter with --merge",
    )
    parser.add_argument(
        "--no-sort", action="store_true",
        help="Do not sort files with --merge (preserve given order)",
    )
    parser.add_argument(
        "--image-dir", default=None,
        help="Image directory (default: search next to the .md file)",
    )
    parser.add_argument(
        "--qr", action="store_true",
        help="QR code with metadata in the page header on every page",
    )
    parser.add_argument(
        "--copy-id", action="store_true", dest="copy_id",
        help="Copy UUID in the page footer",
    )
    parser.add_argument(
        "--verify", metavar="PDF",
        help="Verify the PDF's SHA-256 hash vs source .md file(s)",
    )
    parser.add_argument(
        "--extract-stego", metavar="PDF", dest="extract_stego",
        help="Extract steganography from PDF charts",
    )
    parser.add_argument(
        "--inspect", metavar="PDF",
        help="Show PDF authorship metadata (JSON)",
    )

    args = parser.parse_args()

    input_paths = []
    for p in (Path(x) for x in args.input):
        if p.is_dir():
            # Expand directory into a list of .md files
            md_files = sorted(p.glob("*.md"))
            if not md_files:
                print(f"ERROR: No .md files in folder {p}")
                sys.exit(1)
            input_paths.extend(md_files)
        else:
            input_paths.append(p)

    # Early exit: --verify
    if args.verify:
        _verify_hash(args.verify, input_paths)
        return

    # Early exit: --extract-stego
    if args.extract_stego:
        _extract_stego_from_pdf(args.extract_stego)
        return

    # Early exit: --inspect
    if args.inspect:
        _inspect_pdf(args.inspect)
        return

    # Check that all files exist
    for p in input_paths:
        if not p.exists():
            print(f"ERROR: File not found: {p}")
            sys.exit(1)

    # -o can be used only with a single file (or with --merge)
    if args.output and len(input_paths) > 1 and not args.merge:
        print("ERROR: --output (-o) can only be used with a single input file or with --merge")
        sys.exit(1)

    if args.merge and len(input_paths) >= 2 and not getattr(args, "no_sort", False):
        # Natural file sorting (1, 2, 10 instead of 1, 10, 2)
        import re as _re_sort
        def _nat_key(p):
            return [int(c) if c.isdigit() else c.lower()
                    for c in _re_sort.split(r'(\d+)', p.stem)]
        # Sort h1_titles together with files so positional mapping stays in sync
        h1t = getattr(args, "h1_titles", None)
        if h1t:
            paired = list(zip(input_paths, h1t + [""] * (len(input_paths) - len(h1t))))
            paired.sort(key=lambda x: _nat_key(x[0]))
            input_paths[:] = [p for p, _ in paired]
            args.h1_titles = [t for _, t in paired]
        else:
            input_paths.sort(key=_nat_key)

    # Load custom theme from JSON
    if args.custom_theme:
        import json
        try:
            with open(args.custom_theme, encoding="utf-8") as f:
                custom = json.load(f)
            base = dict(THEMES["teal"])
            base.update(custom)
            THEMES["custom"] = base
            args.theme = "custom"
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"ERROR: Could not load theme: {e}")
            sys.exit(1)

    # Validate theme name
    if args.theme not in THEMES:
        print(f"ERROR: Unknown theme '{args.theme}'. Available: {', '.join(THEMES.keys())}")
        sys.exit(1)

    # Register fonts (not needed in dry-run)
    if not args.dry_run:
        try:
            register_fonts(args.font_dir)
        except FontNotFoundError as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    # Process files
    def _run_all():
        if args.merge:
            _process_merged_files(input_paths, args)
        else:
            for idx, input_path in enumerate(input_paths):
                if len(input_paths) > 1:
                    print(f"\n{'='*50}")
                    print(f"  File {idx + 1}/{len(input_paths)}: {input_path.name}")
                    print(f"{'='*50}")
                _process_one_file(input_path, args, args.output)

    _run_all()

    # Watch mode: monitor files for changes
    if args.watch:
        import time
        print("\n  Watch mode (Ctrl+C to exit)...")
        mtimes = {}
        for p in input_paths:
            try:
                mtimes[p] = p.stat().st_mtime
            except OSError:
                pass
        try:
            while True:
                time.sleep(1.5)
                changed = False
                for input_path in input_paths:
                    try:
                        current = input_path.stat().st_mtime
                    except OSError:
                        continue
                    if current != mtimes.get(input_path):
                        mtimes[input_path] = current
                        changed = True
                        if not args.merge:
                            print(f"\n  Change: {input_path.name}")
                            try:
                                _process_one_file(input_path, args, args.output)
                            except Exception as e:
                                print(f"  Error: {e}")
                if changed and args.merge:
                    print(f"\n  Change detected, rebuilding merged PDF...")
                    try:
                        _process_merged_files(input_paths, args)
                    except Exception as e:
                        print(f"  Error: {e}")
        except KeyboardInterrupt:
            print("\n  Watching stopped.")


if __name__ == "__main__":
    main()
