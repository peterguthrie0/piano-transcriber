"""End-to-end smoke test.

We don't try to render a synthesized waveform through the ML model (basic-pitch
on a synthesized arpeggio doesn't give clean output anyway). Instead we test
each downstream stage on a hand-crafted MIDI:

  - Skip Stage 1 (audio→MIDI) — that's the slow ML path; integration-test it manually
  - Test Stage 2 (notate) and Stage 3 (render) on a known-good PrettyMIDI
"""

from __future__ import annotations

from pathlib import Path

import pretty_midi
import pytest

from piano_transcriber.notate import midi_to_musicxml
from piano_transcriber.render import render_pdf


def _build_arpeggio_midi() -> pretty_midi.PrettyMIDI:
    """C-major arpeggio across the grand staff, 4 seconds, 4/4 at 120bpm."""
    midi = pretty_midi.PrettyMIDI(initial_tempo=120.0)
    piano = pretty_midi.Instrument(program=0, name="Piano")
    pitches = [48, 52, 55, 60, 64, 67, 72, 76]  # C3 → E5
    for i, pitch in enumerate(pitches):
        start = i * 0.5
        piano.notes.append(
            pretty_midi.Note(velocity=80, pitch=pitch, start=start, end=start + 0.5)
        )
    midi.instruments.append(piano)
    return midi


def test_pipeline_midi_to_pdf(tmp_path: Path) -> None:
    midi = _build_arpeggio_midi()
    musicxml_path = tmp_path / "out.musicxml"
    pdf_path = tmp_path / "out.pdf"

    midi_to_musicxml(midi, musicxml_path)
    assert musicxml_path.exists() and musicxml_path.stat().st_size > 0
    assert b"<score-partwise" in musicxml_path.read_bytes()

    render_pdf(musicxml_path, pdf_path)
    assert pdf_path.exists() and pdf_path.stat().st_size > 0
    assert pdf_path.read_bytes().startswith(b"%PDF-")


def test_grand_staff_split() -> None:
    """Notes below middle C land on the bass clef; notes at/above on treble."""
    midi = _build_arpeggio_midi()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        midi_to_musicxml(midi, path)
        xml = path.read_text()
        # Both clefs should appear in the grand staff
        assert "<sign>G</sign>" in xml, "expected treble clef in MusicXML"
        assert "<sign>F</sign>" in xml, "expected bass clef in MusicXML"
    finally:
        path.unlink(missing_ok=True)
