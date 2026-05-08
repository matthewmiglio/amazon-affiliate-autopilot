"""Pick the best caption preset for a given video by sampling its background colors.

Workflow:
  1. ``sample_frame_avgs(video)`` extracts a per-region average RGB at
     three evenly-spaced timestamps. ffmpeg does the heavy lifting:
     crop to the region, scale to 1x1, dump rgb24 — those 3 bytes are
     the region's mean color at that moment.
  2. ``region_avg`` collapses the 3 frame samples per region into one
     final (r,g,b).
  3. ``score_preset`` returns max(WCAG contrast of text vs bg, outline
     vs bg). Outline matters because that's what's read against busy
     backgrounds.
  4. ``pick_best`` randomly selects one of the top-K scoring presets
     (default 3) so the same product can re-roll a different style on
     ``--overwrite``.

No third-party deps — just ffmpeg + ffprobe + stdlib.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

# Region bands as fractions of (W, H). x_lo, x_hi, y_lo, y_hi.
REGION_BANDS: dict[str, tuple[float, float, float, float]] = {
    "top":    (0.10, 0.90, 0.05, 0.20),
    "middle": (0.10, 0.90, 0.43, 0.57),
    "bottom": (0.10, 0.90, 0.80, 0.95),
}

FFMPEG_CANDIDATES = [r"C:\ffmpeg\bin\ffmpeg.exe", "ffmpeg"]
FFPROBE_CANDIDATES = [r"C:\ffmpeg\bin\ffprobe.exe", "ffprobe"]


def _resolve(candidates: list[str]) -> str:
    for c in candidates:
        if Path(c).exists() or shutil.which(c):
            return c
    raise RuntimeError(f"none of {candidates} found")


def find_ffmpeg() -> str:
    return _resolve(FFMPEG_CANDIDATES)


def find_ffprobe() -> str:
    return _resolve(FFPROBE_CANDIDATES)


def probe_dims_duration(video: Path) -> tuple[int, int, float]:
    """Return (width, height, duration_seconds) using ffprobe."""
    ffprobe = find_ffprobe()
    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration",
        "-of", "json", str(video),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(r.stdout)
    s = data["streams"][0]
    return int(s["width"]), int(s["height"]), float(data["format"]["duration"])


def _sample_one(ffmpeg: str, video: Path, t: float,
                x: int, y: int, w: int, h: int) -> tuple[int, int, int]:
    """Crop to region at ``t`` seconds, scale to 1x1, return its (r,g,b)."""
    vf = f"crop={w}:{h}:{x}:{y},scale=1:1"
    cmd = [
        ffmpeg, "-v", "error",
        "-ss", f"{t:.3f}", "-i", str(video),
        "-vf", vf,
        "-frames:v", "1",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-",
    ]
    r = subprocess.run(cmd, capture_output=True, check=True)
    if len(r.stdout) < 3:
        raise RuntimeError(f"ffmpeg returned {len(r.stdout)} bytes for {video.name} @ {t}s")
    return r.stdout[0], r.stdout[1], r.stdout[2]


def sample_frame_avgs(video: Path, n_frames: int = 3,
                      regions: Iterable[str] = ("top", "middle")
                      ) -> dict[str, list[tuple[int, int, int]]]:
    """Per-region list of (r,g,b) averages, one per sampled timestamp."""
    ffmpeg = find_ffmpeg()
    width, height, duration = probe_dims_duration(video)
    # Spread samples evenly across the middle of the duration (avoid t=0 and t=end).
    if n_frames < 1:
        raise ValueError("n_frames >= 1")
    if n_frames == 1:
        ts = [duration / 2]
    else:
        margin = duration * 0.1
        usable = duration - 2 * margin
        ts = [margin + (i / (n_frames - 1)) * usable for i in range(n_frames)]

    out: dict[str, list[tuple[int, int, int]]] = {r: [] for r in regions}
    for r in regions:
        x_lo, x_hi, y_lo, y_hi = REGION_BANDS[r]
        x = int(x_lo * width)
        y = int(y_lo * height)
        w = max(2, int((x_hi - x_lo) * width))
        h = max(2, int((y_hi - y_lo) * height))
        # ffmpeg requires even dimensions for many filter chains; force even.
        w -= w % 2
        h -= h % 2
        for t in ts:
            out[r].append(_sample_one(ffmpeg, video, t, x, y, w, h))
    return out


def region_avg(samples: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    n = len(samples)
    r = sum(s[0] for s in samples) // n
    g = sum(s[1] for s in samples) // n
    b = sum(s[2] for s in samples) // n
    return r, g, b


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rel_lum(rgb: tuple[int, int, int]) -> float:
    """WCAG 2.x relative luminance for sRGB."""
    def chan(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def wcag_contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = _rel_lum(a), _rel_lum(b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def score_preset(style, region_avg_rgb: tuple[int, int, int]) -> float:
    """Best of (text-vs-bg, outline-vs-bg) — outline carries readability on busy bg."""
    text = _hex_to_rgb(style.color)
    outline = _hex_to_rgb(style.outline_color)
    return max(wcag_contrast(text, region_avg_rgb),
               wcag_contrast(outline, region_avg_rgb))


def pick_best(presets: list[tuple[str, object]],
              region_avgs: dict[str, tuple[int, int, int]],
              top_k: int = 3,
              rng: random.Random | None = None) -> tuple[str, object, float]:
    """Score every preset against the avg color at its placement, then pick
    randomly from the top ``top_k``. Returns (name, style, score).

    Skips presets whose placement isn't sampled in ``region_avgs``.
    """
    rng = rng or random
    scored = []
    for name, style in presets:
        if style.alignment not in region_avgs:
            continue
        bg = region_avgs[style.alignment]
        scored.append((score_preset(style, bg), name, style))
    if not scored:
        raise RuntimeError("no presets scored — empty list or unsupported placements")
    scored.sort(key=lambda t: t[0], reverse=True)
    pool = scored[:max(1, top_k)]
    score, name, style = rng.choice(pool)
    return name, style, score
