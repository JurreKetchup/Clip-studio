"""
Knipt het gekozen fragment uit de bronvideo, snijdt/schaalt naar de
gekozen beeldverhouding, en brandt (optioneel) ondertiteling en een
hook-tekst in het beeld.
"""
import subprocess
import os

RESOLUTIONS = {
    ("9:16", "1080"): (1080, 1920),
    ("9:16", "720"): (720, 1280),
    ("1:1", "1080"): (1080, 1080),
    ("1:1", "720"): (720, 720),
    ("16:9", "1080"): (1920, 1080),
    ("16:9", "720"): (1280, 720),
}


def _crop_scale_filter(aspect_ratio: str, resolution: str) -> str:
    target_w, target_h = RESOLUTIONS[(aspect_ratio, resolution)]
    if aspect_ratio == "9:16":
        crop = "crop=ih*9/16:ih"
    elif aspect_ratio == "1:1":
        crop = "crop=ih:ih"
    else:  # 16:9 - crop width instead if source is taller
        crop = "crop=iw:iw*9/16"
    return f"{crop},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"


def _seconds_to_srt_time(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(words: list[dict], clip_start: float, clip_end: float, out_path: str, words_per_line: int = 4):
    """Group whisper word-timestamps into short subtitle lines, offset to clip-relative time."""
    relevant = [w for w in words if clip_start <= w["start"] < clip_end]
    lines = []
    for i in range(0, len(relevant), words_per_line):
        group = relevant[i:i + words_per_line]
        if not group:
            continue
        start = group[0]["start"] - clip_start
        end = group[-1]["end"] - clip_start
        text = " ".join(w["word"].strip() for w in group)
        lines.append((max(0, start), max(0, end), text))

    with open(out_path, "w", encoding="utf-8") as f:
        for idx, (start, end, text) in enumerate(lines, 1):
            f.write(f"{idx}\n{_seconds_to_srt_time(start)} --> {_seconds_to_srt_time(end)}\n{text}\n\n")
    return out_path


def render_clip(
    source_path: str,
    start: float,
    end: float,
    out_path: str,
    aspect_ratio: str,
    resolution: str,
    subtitles_srt: str | None,
    hook_text: str | None,
    highest_quality: bool,
) -> str:
    duration = end - start
    vf_parts = [_crop_scale_filter(aspect_ratio, resolution)]

    if subtitles_srt and os.path.exists(subtitles_srt):
        escaped = subtitles_srt.replace(":", "\\:").replace("'", "\\'")
        vf_parts.append(
            f"subtitles={escaped}:force_style='FontName=Arial,FontSize=16,Bold=1,"
            f"PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Alignment=2,MarginV=80'"
        )

    if hook_text:
        safe_hook = hook_text.replace(":", "\\:").replace("'", "\u2019")
        vf_parts.append(
            f"drawtext=text='{safe_hook}':fontcolor=white:fontsize=42:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y=120:enable='between(t,0,2.5)'"
        )

    vf = ",".join(vf_parts)
    crf = "18" if highest_quality else "23"

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-i", source_path, "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
        "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"Clip renderen mislukt: {result.stderr[-800:]}")
    return out_path
