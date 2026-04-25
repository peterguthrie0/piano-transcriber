# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install (Python 3.10 or 3.11 only — basic-pitch's TF dep has no macOS wheels for 3.12)
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install -e '.[heavy]'   # adds PyTorch + bytedance piano model (~165 MB)
pip install -e '.[dev]'     # adds pytest

# Run the CLI
piano-transcribe path/to/audio.wav -o score.pdf
piano-transcribe in.wav -o out.pdf --model bytedance --quantize 4,3 --keep-musicxml debug.xml

# Tests
pytest                                               # all tests
pytest tests/test_pipeline.py::test_grand_staff_split  # single test
```

System dependencies (not pip-installable): `ffmpeg` (non-WAV decoding) and `cairo` (`cairosvg` is a CFFI wrapper, not pure Python). On macOS: `brew install ffmpeg cairo`.

## Architecture

Three swappable stages behind one orchestrator:

```
audio ──Stage 1──► PrettyMIDI ──Stage 2──► MusicXML ──Stage 3──► PDF
       transcribe.py            notate.py             render.py
                          pipeline.transcribe_to_pdf()
                                    cli.py
```

Key design contracts to preserve when extending:

- **`pipeline.transcribe_to_pdf()` is the single public entrypoint.** Both `cli.py` and any future web handler (FastAPI/Flask on uploaded bytes) must call it; do not put orchestration logic in `cli.py`. `__init__.py` re-exports only this function.
- **Stage 1 backends conform to a `Protocol`** (`transcribe.py:Transcriber`), not an ABC. Add a new backend by creating a class with `transcribe(audio_path) -> pretty_midi.PrettyMIDI` and registering it in `_BACKENDS`. Heavy imports (torch, librosa, piano-transcription-inference) live *inside* `__init__`/`transcribe` so the default light path never pays their import cost — keep it that way.
- **Stage 2 (`notate.py`) goes MIDI → temp `.mid` file → `music21.converter.parse` → `Score`.** This round-trip through disk is intentional; music21's MIDI ingestion is the path with the most correct timing/duration handling. Quantization uses the grid `DEFAULT_QUANTIZATION = (4, 3)` (16th-note + 8th-triplet). Staff splitting is a hard middle-C threshold (`SPLIT_PITCH = 60`) — a known limitation, not a bug to fix casually.
- **Stage 3 (`render.py`) is Verovio per-page SVG → cairosvg per-page PDF → pypdf concat.** All three engraving deps are pure-Python with no external app required, which is why the pipeline can run inside a web server. Don't introduce a binary like `musescore` or `lilypond` without a strong reason — it would break that property.

## Testing notes

`tests/test_pipeline.py` deliberately **skips Stage 1**: it builds a `PrettyMIDI` arpeggio in memory and feeds it directly to `notate` + `render`. The reason (documented at the top of the test file) is that basic-pitch on synthesized waveforms produces noisy output, and the ML inference is slow. Do not "fix" this by adding audio synthesis upstream of the test — Stage 1 is integration-tested manually against `samples/sine_arpeggio.wav`.

## Known limitations (don't treat as bugs)

Listed in README.md: simple middle-C staff split, no pedal/dynamics/articulations, heuristic time-signature detection, polyphony confusion in dense passages. These are scope choices, not defects.
