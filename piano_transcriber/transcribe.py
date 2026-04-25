"""Stage 1: audio file → MIDI (pretty_midi.PrettyMIDI).

Two backends sit behind the Transcriber Protocol:
  - basic-pitch (default): lightweight, CPU, polyphonic, multi-instrument.
  - piano-transcription-inference (opt-in via [heavy] extra): piano-specialized,
    higher accuracy, PyTorch-based, larger download.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

import pretty_midi


class Transcriber(Protocol):
    """A model that turns an audio file into a PrettyMIDI object."""

    def transcribe(self, audio_path: Path) -> pretty_midi.PrettyMIDI: ...


class BasicPitchTranscriber:
    def transcribe(self, audio_path: Path) -> pretty_midi.PrettyMIDI:
        from basic_pitch import ICASSP_2022_MODEL_PATH
        from basic_pitch.inference import predict

        _model_output, midi_data, _note_events = predict(
            str(audio_path), ICASSP_2022_MODEL_PATH
        )
        return midi_data


class BytedanceTranscriber:
    def __init__(self) -> None:
        try:
            from piano_transcription_inference import PianoTranscription
        except ImportError as exc:
            raise RuntimeError(
                "The 'bytedance' transcriber requires the [heavy] extra. "
                "Install with: pip install -e '.[heavy]'"
            ) from exc
        self._transcriptor = PianoTranscription(device="cpu")

    def transcribe(self, audio_path: Path) -> pretty_midi.PrettyMIDI:
        import librosa

        audio, _sr = librosa.load(str(audio_path), sr=16000, mono=True)
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
            midi_path = Path(tmp.name)
        try:
            self._transcriptor.transcribe(audio, str(midi_path))
            return pretty_midi.PrettyMIDI(str(midi_path))
        finally:
            midi_path.unlink(missing_ok=True)


_BACKENDS: dict[str, type[Transcriber]] = {
    "basic-pitch": BasicPitchTranscriber,
    "bytedance": BytedanceTranscriber,
}


def get_transcriber(name: str) -> Transcriber:
    try:
        return _BACKENDS[name]()
    except KeyError as exc:
        available = ", ".join(_BACKENDS)
        raise ValueError(
            f"Unknown transcriber '{name}'. Available: {available}"
        ) from exc
