"""Stage 2: PrettyMIDI → MusicXML.

Quantize, detect key/meter, split into a two-staff piano grand staff
using a middle-C pitch threshold heuristic.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pretty_midi
from music21 import clef, converter, instrument, meter, stream


SPLIT_PITCH = 60  # middle C: notes at or above → treble, below → bass
DEFAULT_QUANTIZATION = (4, 3)  # 16th-note grid + 8th-note triplet grid


def midi_to_musicxml(
    midi: pretty_midi.PrettyMIDI,
    output_path: Path,
    *,
    quantization: tuple[int, ...] = DEFAULT_QUANTIZATION,
) -> Path:
    score = _midi_to_score(midi)
    score.quantize(quantization, inPlace=True, recurse=True)
    piano_score = _split_into_grand_staff(score)
    _attach_key_and_meter(piano_score)
    piano_score.write("musicxml", fp=str(output_path))
    return output_path


def _midi_to_score(midi: pretty_midi.PrettyMIDI) -> stream.Score:
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        midi_path = Path(tmp.name)
    try:
        midi.write(str(midi_path))
        parsed = converter.parse(str(midi_path))
    finally:
        midi_path.unlink(missing_ok=True)
    if isinstance(parsed, stream.Score):
        return parsed
    score = stream.Score()
    score.append(parsed)
    return score


def _split_into_grand_staff(score: stream.Score) -> stream.Score:
    treble = stream.Part()
    bass = stream.Part()
    treble.insert(0, instrument.Piano())
    treble.insert(0, clef.TrebleClef())
    bass.insert(0, instrument.Piano())
    bass.insert(0, clef.BassClef())

    for note_or_chord in score.flatten().notes:
        if note_or_chord.isChord:
            highs = [n for n in note_or_chord.notes if n.pitch.midi >= SPLIT_PITCH]
            lows = [n for n in note_or_chord.notes if n.pitch.midi < SPLIT_PITCH]
            if highs:
                treble.insert(note_or_chord.offset, _make_chord_or_note(highs, note_or_chord))
            if lows:
                bass.insert(note_or_chord.offset, _make_chord_or_note(lows, note_or_chord))
        else:
            target = treble if note_or_chord.pitch.midi >= SPLIT_PITCH else bass
            target.insert(note_or_chord.offset, note_or_chord)

    treble.makeMeasures(inPlace=True)
    bass.makeMeasures(inPlace=True)

    piano = stream.Score()
    piano.insert(0, treble)
    piano.insert(0, bass)
    return piano


def _make_chord_or_note(notes, source):
    from music21 import chord, note

    if len(notes) == 1:
        new_note = note.Note(notes[0].pitch)
        new_note.duration = source.duration
        new_note.offset = source.offset
        return new_note
    new_chord = chord.Chord([n.pitch for n in notes])
    new_chord.duration = source.duration
    new_chord.offset = source.offset
    return new_chord


def _attach_key_and_meter(score: stream.Score) -> None:
    try:
        detected_key = score.analyze("key")
        first_measure = score.parts[0].getElementsByClass(stream.Measure).first()
        if first_measure is not None:
            first_measure.insert(0, detected_key)
    except Exception:
        pass

    for part in score.parts:
        for measure in part.getElementsByClass(stream.Measure):
            if measure.timeSignature is None:
                ts = measure.bestTimeSignature() if measure.notes else meter.TimeSignature("4/4")
                measure.timeSignature = ts
                break
