"""Command-line entry point for the captioning tool.

Wires :mod:`transcribe` (WhisperX word-level ASR) to :mod:`render`
(ffmpeg + ASS subtitle burn-in). Parses style flags, optionally reuses a
cached transcription JSON, then writes a captioned mp4 to ``--out``.

Run ``caption --help`` after install, or ``python cli.py --help`` when
invoking the module directly from this folder.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from render import CaptionStyle, render
from transcribe import transcribe_video


def _add_style_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("style")
    g.add_argument("--font", default="Inter", help="font family name (must be installed on system)")
    g.add_argument("--font-size", type=int, default=72)
    g.add_argument("--color", default="FFFFFF", help="text color hex (RRGGBB)")
    g.add_argument("--outline-color", default="000000", help="text outline color hex")
    g.add_argument("--outline-width", type=float, default=4.0)
    g.add_argument("--shadow", type=float, default=2.0, help="drop-shadow distance in px")
    g.add_argument("--bg-color", default="000000", help="background box color hex (used with --box)")
    g.add_argument("--bg-alpha", type=int, default=0, help="bg alpha 0=opaque, 255=transparent")
    g.add_argument("--box", action="store_true", help="draw an opaque background box behind text")
    g.add_argument("--bold", dest="bold", action="store_true", default=True)
    g.add_argument("--no-bold", dest="bold", action="store_false")
    g.add_argument("--italic", action="store_true")
    g.add_argument("--underline", action="store_true")
    g.add_argument(
        "--alignment", default="bottom",
        choices=list(_alignments()),
        help="caption position",
    )
    g.add_argument("--margin-l", type=int, default=80)
    g.add_argument("--margin-r", type=int, default=80)
    g.add_argument("--margin-v", type=int, default=300, help="vertical margin from edge")
    g.add_argument("--play-res-x", type=int, default=1080)
    g.add_argument("--play-res-y", type=int, default=1920)
    g.add_argument("--uppercase", dest="uppercase", action="store_true", default=True)
    g.add_argument("--no-uppercase", dest="uppercase", action="store_false")
    g.add_argument("--per-segment", dest="per_word", action="store_false", default=True,
                   help="show whole segment instead of one word at a time")


def _alignments() -> list[str]:
    from render import ALIGNMENT_MAP
    return sorted(ALIGNMENT_MAP.keys())


def _style_from_args(args: argparse.Namespace) -> CaptionStyle:
    return CaptionStyle(
        font=args.font,
        font_size=args.font_size,
        color=args.color,
        outline_color=args.outline_color,
        bg_color=args.bg_color,
        bg_alpha=args.bg_alpha,
        outline_width=args.outline_width,
        shadow=args.shadow,
        bold=args.bold,
        italic=args.italic,
        underline=args.underline,
        box=args.box,
        alignment=args.alignment,
        margin_l=args.margin_l,
        margin_r=args.margin_r,
        margin_v=args.margin_v,
        play_res_x=args.play_res_x,
        play_res_y=args.play_res_y,
        uppercase=args.uppercase,
        per_word=args.per_word,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="caption",
        description="Burn styled, word-level captions onto an mp4 using WhisperX.",
    )
    p.add_argument("--video", required=True, help="input video (mp4)")
    p.add_argument("--out", required=True, help="output captioned mp4")
    p.add_argument("--model", default="large-v3", help="WhisperX model size")
    p.add_argument("--timestamps", help="reuse a JSON of segments (skip transcription)")
    p.add_argument("--save-timestamps", help="write transcription JSON to this path")
    _add_style_args(p)
    args = p.parse_args(argv)

    video = Path(args.video)
    out = Path(args.out)
    if not video.exists():
        print(f"video not found: {video}", file=sys.stderr)
        return 2

    if args.timestamps:
        segments = json.loads(Path(args.timestamps).read_text(encoding="utf-8"))
        if isinstance(segments, dict) and "segments" in segments:
            segments = segments["segments"]
    else:
        print(f"[caption] transcribing {video.name} with WhisperX ({args.model})...")
        segments = transcribe_video(video, model_size=args.model)
        if args.save_timestamps:
            Path(args.save_timestamps).parent.mkdir(parents=True, exist_ok=True)
            Path(args.save_timestamps).write_text(
                json.dumps({"segments": segments}, indent=2), encoding="utf-8"
            )
            print(f"[caption] saved timestamps → {args.save_timestamps}")

    style = _style_from_args(args)
    print(f"[caption] rendering → {out}")
    render(video, segments, out, style)
    print(f"[caption] done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
