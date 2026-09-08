"""
Alles wat met het brontbestand te maken heeft: YouTube downloaden,
audio eruit trekken, en die audio laten transcriberen (met woord-timestamps
zodat we later ondertiteling exact kunnen synchroniseren).
"""
import subprocess
import os
from groq import Groq

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


def download_youtube(url: str, out_dir: str) -> str:
    """Download a YouTube video as mp4 using yt-dlp. Returns the local path."""
    out_path = os.path.join(out_dir, "source.mp4")
    cmd = [
        "yt-dlp",
        "-f", "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format", "mp4",
        "-o", out_path,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(f"YouTube download mislukt: {result.stderr[-800:]}")
    return out_path


def extract_audio(video_path: str, out_dir: str) -> str:
    """Pull a mono 16kHz wav track out of the video for transcription."""
    audio_path = os.path.join(out_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError(f"Audio uitpakken mislukt: {result.stderr[-800:]}")
    return audio_path


def get_duration_seconds(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def transcribe(audio_path: str) -> dict:
    """
    Transcribeert met Groq's Whisper endpoint en vraagt woord-niveau
    timestamps op, zodat we ondertiteling exact kunnen laten meelopen.
    Groq is gebruikt (i.p.v. lokaal Whisper draaien) omdat dat geen
    zware GPU/CPU nodig heeft op de Render server.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY ontbreekt. Zet deze als environment variable op Render.")
    client = Groq(api_key=GROQ_API_KEY)
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f.read()),
            model="whisper-large-v3-turbo",
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
        )
    return transcript.model_dump()
