"""Top-level orchestrator: audio → PDF in one call.

Both the CLI and a future web handler should call this function rather
than reaching into the individual stage modules.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from piano_transcriber.notate import DEFAULT_QUANTIZATION, midi_to_musicxml
from piano_transcriber.render import render_pdf
from piano_transcriber.transcribe import get_transcriber


def transcribe_to_pdf(
    audio_path: Path,
    pdf_path: Path,
    *,
    model: str = "basic-pitch",
    quantization: tuple[int, ...] = DEFAULT_QUANTIZATION,
    musicxml_path: Path | None = None,
) -> Path:
    """Run the full audio → MIDI → MusicXML → PDF pipeline.

    If ``musicxml_path`` is None, an intermediate file is created in a
    temp directory and discarded.
    """
    audio_path = Path(audio_path)
    pdf_path = Path(pdf_path)

    transcriber = get_transcriber(model)
    midi = transcriber.transcribe(audio_path)

    if musicxml_path is None:
        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
            xml_path = Path(tmp.name)
        cleanup = True
    else:
        xml_path = Path(musicxml_path)
        cleanup = False

    try:
        midi_to_musicxml(midi, xml_path, quantization=quantization)
        render_pdf(xml_path, pdf_path)
    finally:
        if cleanup:
            xml_path.unlink(missing_ok=True)

    return pdf_path
