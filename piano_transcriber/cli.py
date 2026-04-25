"""Argparse shim. The real work lives in piano_transcriber.pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from piano_transcriber.pipeline import transcribe_to_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="piano-transcribe",
        description="Transcribe a piano audio recording to PDF sheet music.",
    )
    parser.add_argument("audio", type=Path, help="Input audio file (wav, mp3, flac, ...).")
    parser.add_argument(
        "-o", "--output", type=Path, required=True, help="Output PDF path."
    )
    parser.add_argument(
        "--model",
        choices=["basic-pitch", "bytedance"],
        default="basic-pitch",
        help="Transcription backend. 'bytedance' requires the [heavy] extra.",
    )
    parser.add_argument(
        "--quantize",
        type=str,
        default="4,3",
        help="Comma-separated quantization grid (default: 4,3 = 16th + 8th-triplet).",
    )
    parser.add_argument(
        "--keep-musicxml",
        type=Path,
        default=None,
        help="If set, save the intermediate MusicXML to this path.",
    )
    args = parser.parse_args(argv)

    if not args.audio.exists():
        print(f"error: audio file not found: {args.audio}", file=sys.stderr)
        return 2

    try:
        quantization = tuple(int(x) for x in args.quantize.split(","))
    except ValueError:
        print(f"error: --quantize must be comma-separated integers, got: {args.quantize}", file=sys.stderr)
        return 2

    print(f"Transcribing {args.audio} with model '{args.model}'...", file=sys.stderr)
    transcribe_to_pdf(
        args.audio,
        args.output,
        model=args.model,
        quantization=quantization,
        musicxml_path=args.keep_musicxml,
    )
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
