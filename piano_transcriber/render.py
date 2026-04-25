"""Stage 3: MusicXML → PDF.

Verovio renders one SVG per page; cairosvg converts each SVG to a single-page
PDF; pypdf concatenates the pages into the final multi-page PDF.
"""

from __future__ import annotations

import io
from pathlib import Path

import cairosvg
import pypdf
import verovio

A4_HEIGHT_TENTHS = 2970
A4_WIDTH_TENTHS = 2100
DEFAULT_SCALE = 40


def render_pdf(musicxml_path: Path, pdf_path: Path) -> Path:
    tk = verovio.toolkit()
    tk.setOptions({
        "pageHeight": A4_HEIGHT_TENTHS,
        "pageWidth": A4_WIDTH_TENTHS,
        "scale": DEFAULT_SCALE,
        "adjustPageHeight": False,
    })
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError(f"Verovio failed to load {musicxml_path}")

    page_count = tk.getPageCount()
    if page_count == 0:
        raise RuntimeError(f"Verovio produced 0 pages from {musicxml_path}")

    writer = pypdf.PdfWriter()
    for page_no in range(1, page_count + 1):
        svg = tk.renderToSVG(page_no)
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    with open(pdf_path, "wb") as f:
        writer.write(f)
    return pdf_path
