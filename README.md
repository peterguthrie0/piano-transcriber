# piano-transcriber

A small CLI for experimenting with audio-to-sheet-music: feed it a piano recording, get back a PDF score.

The pipeline is three swappable stages — audio → MIDI (ML model) → MusicXML (music21) → PDF (Verovio + cairosvg + pypdf) — wrapped behind a single `transcribe_to_pdf()` function. The CLI is a thin shell over that function so the same code can sit behind a web handler later.

> Modern audio-to-score is genuinely hard. Expect plausible-but-wrong rhythms, awkward staff splits, and missed ornaments — especially on dense or pedaled passages. This is for tinkering, not production.

## Install

Requires Python **3.10 or 3.11** (basic-pitch's TensorFlow dep doesn't have macOS wheels for 3.12 yet), plus two system libraries:

- `ffmpeg` — for decoding non-WAV inputs (`brew install ffmpeg`)
- `cairo` — `cairosvg` is a CFFI wrapper, not pure Python (`brew install cairo`, or `apt-get install libcairo2` on Linux)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Optional: heavier, more accurate piano-specialized model (PyTorch + ~165MB checkpoint)
pip install -e '.[heavy]'
```

## Usage

```bash
piano-transcribe path/to/recording.wav -o score.pdf
```

Flags:

- `--model {basic-pitch,bytedance}` — transcription backend. Default `basic-pitch` (Spotify; light, CPU). `bytedance` (ByteDance piano-specialized model) needs the `[heavy]` extra and is more accurate on solo piano.
- `--quantize 4,3` — comma-separated quantization grid passed to `music21.stream.quantize`. Default `4,3` snaps to the 16th-note + 8th-triplet grid.
- `--keep-musicxml path.xml` — also save the intermediate MusicXML for inspection or hand-editing.

## Architecture

```
piano_transcriber/
├── transcribe.py   # Stage 1: audio → pretty_midi.PrettyMIDI (pluggable backends)
├── notate.py       # Stage 2: PrettyMIDI → MusicXML (music21)
├── render.py       # Stage 3: MusicXML → PDF (Verovio + cairosvg + pypdf)
├── pipeline.py     # Top-level transcribe_to_pdf() orchestrator
└── cli.py          # argparse shim
```

Future web app: import `transcribe_to_pdf` from FastAPI/Flask and call it on uploaded bytes — no other changes needed. All three engraving deps are pure-Python with no external app required.

## Known limitations

- **Staff splitting** uses a simple middle-C pitch threshold. Left-hand parts that cross above middle C will get assigned to the treble staff.
- **No pedal handling** — sustain pedal information from the model (if any) is dropped during quantization.
- **No dynamics or articulations** — only pitches and rhythms.
- **Time signature detection** is heuristic and often wrong on rubato or non-4/4 pieces.
- **Polyphony confusion** — both backends sometimes invent or merge notes in dense passages.

## Test

```bash
pytest
```

The smoke test synthesizes a short MIDI arpeggio, renders it to audio in-memory, runs the full pipeline, and asserts a non-empty PDF lands at the expected path.
