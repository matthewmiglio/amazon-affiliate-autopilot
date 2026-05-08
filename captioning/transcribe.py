"""WhisperX-based word-level transcription helpers.

Extracts mono 16 kHz PCM audio from a video, runs WhisperX to get
segment-level text, then aligns it to produce per-word timestamps. The
result is the segment list consumed by :func:`render.build_ass`.

CUDA is used automatically when available; otherwise the module falls back
to CPU with ``int8`` compute so it stays runnable without a GPU.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


def extract_audio(video: Path, out_wav: Path) -> None:
    """Demux ``video`` to a mono 16 kHz PCM wav at ``out_wav`` via ffmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", str(out_wav),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_video(video: Path, model_size: str = "large-v3") -> list[dict]:
    """Transcribe ``video`` and return word-aligned segments.

    Args:
        video: Path to any media file ffmpeg can read.
        model_size: WhisperX/Whisper model identifier (e.g. ``"large-v3"``,
            ``"medium"``, ``"small"``). Larger = slower, more accurate.

    Returns:
        A list of segment dicts shaped as
        ``{"text": str, "start": float, "end": float,
        "words": [{"word": str, "start": float, "end": float}, ...]}``.
        Word entries missing alignment timestamps are dropped.
    """
    import whisperx

    device = "cuda"
    try:
        import torch
        if not torch.cuda.is_available():
            device = "cpu"
    except Exception:
        device = "cpu"

    compute_type = "float16" if device == "cuda" else "int8"

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = Path(tmp) / "audio.wav"
        extract_audio(video, audio_path)

        model = whisperx.load_model(model_size, device, compute_type=compute_type)
        audio = whisperx.load_audio(str(audio_path))
        result = model.transcribe(audio, batch_size=8)

        align_model, metadata = whisperx.load_align_model(
            language_code=result["language"], device=device
        )
        aligned = whisperx.align(
            result["segments"], align_model, metadata, audio, device,
            return_char_alignments=False,
        )

    segments: list[dict] = []
    for seg in aligned["segments"]:
        words = []
        for w in seg.get("words", []):
            if "start" in w and "end" in w:
                words.append({
                    "word": w.get("word", "").strip(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                })
        segments.append({
            "text": seg.get("text", "").strip(),
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "words": words,
        })
    return segments
