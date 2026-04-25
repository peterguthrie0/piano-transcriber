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

# Verovio works in MEI tenths-of-a-mm. A4 = 210 × 297 mm.
A4_WIDTH_TENTHS = 2100
A4_HEIGHT_TENTHS = 2970
A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297


def render_pdf(musicxml_path: Path, pdf_path: Path) -> Path:
    tk = verovio.toolkit()
    tk.setOptions({
        "pageHeight": A4_HEIGHT_TENTHS,
        "pageWidth": A4_WIDTH_TENTHS,
        "adjustPageHeight": False,
    })
    if not tk.loadFile(str(musicxml_path)):
        raise RuntimeError(f"Verovio failed to load {musicxml_path}")

    page_count = tk.getPageCount()
    if page_count == 0:
        raise RuntimeError(f"Verovio produced 0 pages from {musicxml_path}")

    # Verovio emits SVGs declared in px with no viewBox; cairosvg then treats
    # the declared px size as a literal clip region, cutting off any drawing
    # coords beyond it. Replace with mm dimensions + a viewBox so cairosvg
    # rescales the coordinate system into a true A4 PDF page.
    sized_header = (
        f'width="{A4_WIDTH_TENTHS}px" height="{A4_HEIGHT_TENTHS}px"'
    )
    fixed_header = (
        f'width="{A4_WIDTH_MM}mm" height="{A4_HEIGHT_MM}mm" '
        f'viewBox="0 0 {A4_WIDTH_TENTHS} {A4_HEIGHT_TENTHS}"'
    )

    writer = pypdf.PdfWriter()
    for page_no in range(1, page_count + 1):
        svg = tk.renderToSVG(page_no).replace(sized_header, fixed_header, 1)
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg.encode("utf-8"))
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    with open(pdf_path, "wb") as f:
        writer.write(f)
    return pdf_path
