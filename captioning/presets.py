"""Caption-style presets selected by triage benchmark.

These 8 presets survived the round-3 yes/no triage in
``captioning-benchmarking/decisions.json``. Each one's kwargs encode
the final placement (top vs middle), the +20% size bump applied across
the board, plus per-style customizations the user requested
interactively (32_hot_pink → white/pink invert, 34_cream_subtle → +30%
extra size, etc.).

Use ``PRESETS`` for the full list, or ``by_placement("top")`` /
``by_placement("middle")`` to filter.
"""
from __future__ import annotations

from render import CaptionStyle


PRESETS: list[tuple[str, CaptionStyle]] = [
    ("classic_white_black", CaptionStyle(
        color="FFFFFF", outline_color="000000",
        outline_width=4, shadow=2, font_size=86,
        alignment="top", margin_v=200,
    )),
    ("tiktok_yellow", CaptionStyle(
        color="FFE600", outline_color="000000",
        outline_width=5, shadow=3, font_size=94,
        alignment="middle", margin_v=0,
    )),
    ("top_aligned_default", CaptionStyle(
        font_size=86,
        alignment="top", margin_v=200,
    )),
    ("thick_outline", CaptionStyle(
        outline_width=8, shadow=0, font_size=94,
        alignment="top", margin_v=200,
    )),
    ("gold_luxury", CaptionStyle(
        color="FFD24A", outline_color="3B2300",
        outline_width=4, shadow=2, font_size=91,
        alignment="middle", margin_v=0,
    )),
    ("lime_green_punch", CaptionStyle(
        color="C6FF00", outline_color="0A2A00",
        outline_width=5, shadow=2, font_size=94,
        alignment="top", margin_v=200,
    )),
    ("hot_pink_outline", CaptionStyle(
        color="FFFFFF", outline_color="FF1F8E",
        outline_width=5, shadow=2, font_size=91,
        alignment="middle", margin_v=0,
    )),
    ("cream_subtle_xl", CaptionStyle(
        color="F5E6C8", outline_color="2A1F12",
        outline_width=3, shadow=2, font_size=103,
        uppercase=False,
        alignment="top", margin_v=200,
    )),
]


def by_placement(placement: str) -> list[tuple[str, CaptionStyle]]:
    """Return only presets whose alignment matches ``placement`` ('top' | 'middle' | 'bottom')."""
    return [(name, s) for name, s in PRESETS if s.alignment == placement]
