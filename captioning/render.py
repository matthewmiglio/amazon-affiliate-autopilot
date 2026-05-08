"""Render burned-in captions onto a video using ffmpeg + ASS subtitles.

Builds an ASS (Advanced SubStation Alpha) script from word-aligned
segments, then invokes ffmpeg's ``ass`` video filter to burn the styled
captions into a new mp4. Two modes are supported:

* **per-word** (default, karaoke-style): one event per word with tight
  start/end timing — best for short-form vertical video.
* **per-segment**: one event per Whisper segment.

The :class:`CaptionStyle` dataclass owns every visual knob (font, colors,
outline, shadow, alignment, margins, target play resolution, casing) and
emits the ASS ``[V4+ Styles]`` line that drives rendering.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


# ASS alignment numpad: 1=BL 2=BC 3=BR 4=ML 5=MC 6=MR 7=TL 8=TC 9=TR
ALIGNMENT_MAP = {
    "bottom-left": 1, "bottom": 2, "bottom-center": 2, "bottom-right": 3,
    "middle-left": 4, "middle": 5, "middle-center": 5, "center": 5, "middle-right": 6,
    "top-left": 7, "top": 8, "top-center": 8, "top-right": 9,
}


def hex_to_ass_color(hex_str: str, alpha: int = 0) -> str:
    """Convert #RRGGBB or RRGGBB → ASS &HAABBGGRR& (alpha 0=opaque, 255=transparent)."""
    s = hex_str.lstrip("#").strip()
    if len(s) != 6:
        raise ValueError(f"Color must be 6-digit hex, got: {hex_str!r}")
    r, g, b = s[0:2], s[2:4], s[4:6]
    a = f"{max(0, min(255, alpha)):02X}"
    return f"&H{a}{b.upper()}{g.upper()}{r.upper()}&"


def fmt_ts(seconds: float) -> str:
    """Format ``seconds`` as the ASS timestamp ``H:MM:SS.cs`` (centisecond precision)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - (h * 3600 + m * 60)
    return f"{h:01d}:{m:02d}:{s:05.2f}"


def _bool(v: bool) -> int:
    return -1 if v else 0


@dataclass
class CaptionStyle:
    font: str = "Inter"
    font_size: int = 72
    color: str = "FFFFFF"
    outline_color: str = "000000"
    bg_color: str = "000000"  # only used when border_style=3 (opaque box)
    outline_width: float = 4.0
    shadow: float = 2.0
    bold: bool = True
    italic: bool = False
    underline: bool = False
    box: bool = False  # opaque background box behind text
    bg_alpha: int = 0  # 0 opaque, 255 transparent
    alignment: str = "bottom"
    margin_l: int = 80
    margin_r: int = 80
    margin_v: int = 300
    play_res_x: int = 1080
    play_res_y: int = 1920
    uppercase: bool = True
    per_word: bool = True  # one event per word (karaoke style); False = per segment

    def style_line(self) -> str:
        border_style = 3 if self.box else 1
        primary = hex_to_ass_color(self.color)
        outline = hex_to_ass_color(self.outline_color)
        back = hex_to_ass_color(self.bg_color, alpha=self.bg_alpha)
        align = ALIGNMENT_MAP.get(self.alignment.lower(), 2)
        # Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour,
        # BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle,
        # BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
        return (
            f"Style: Default,{self.font},{self.font_size},"
            f"{primary},&H000000FF&,{outline},{back},"
            f"{_bool(self.bold)},{_bool(self.italic)},{_bool(self.underline)},0,"
            f"100,100,0,0,"
            f"{border_style},{self.outline_width},{self.shadow},{align},"
            f"{self.margin_l},{self.margin_r},{self.margin_v},1"
        )

    def header(self) -> str:
        return (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {self.play_res_x}\n"
            f"PlayResY: {self.play_res_y}\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"{self.style_line()}\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
            "Effect, Text\n"
        )


_PUNCT = re.compile(r"[,.!?;:\"]")


def _clean(text: str, uppercase: bool) -> str:
    text = _PUNCT.sub("", text).strip()
    return text.upper() if uppercase else text


def build_ass(segments: list[dict], style: CaptionStyle) -> str:
    """Render ``segments`` (from :func:`transcribe.transcribe_video`) to an ASS script string."""
    lines = [style.header()]
    for seg in segments:
        words = seg.get("words") or []
        if style.per_word and words:
            for w in words:
                start = fmt_ts(w["start"])
                end = fmt_ts(max(w["end"], w["start"] + 0.05))
                text = _clean(w["word"], style.uppercase)
                if not text:
                    continue
                lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        else:
            start = fmt_ts(seg["start"])
            end = fmt_ts(seg["end"])
            text = _clean(seg.get("text", ""), style.uppercase)
            if not text:
                continue
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
    return "\n".join(lines)


def render(video: Path, segments: list[dict], output: Path, style: CaptionStyle) -> None:
    """Burn captions described by ``segments`` + ``style`` onto ``video``, writing ``output``.

    Audio is stream-copied; the video stream is re-encoded by ffmpeg's
    ``ass`` filter using a temp ASS file so the subtitle path stays free
    of Windows backslash quirks.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    video_abs = str(video.resolve())
    output_abs = str(output.resolve())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ass_file = tmp_path / "captions.ass"
        ass_file.write_text(build_ass(segments, style), encoding="utf-8")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_abs,
            "-vf", "ass=captions.ass",
            "-c:a", "copy",
            output_abs,
        ]
        subprocess.run(cmd, check=True, cwd=str(tmp_path))
