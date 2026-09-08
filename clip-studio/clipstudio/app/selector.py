"""
Laat een LLM het transcript lezen en de meest 'viral-waardige' stukken
kiezen: momenten met een duidelijke haak, een punchline, een opvallende
uitspraak, emotie, of een op-zichzelf-staand verhaaltje. De LLM krijgt
het transcript mét tijdstempels en geeft start/eind-tijden + een titel
+ een korte hook-tekst terug in JSON.
"""
import json
import os
from groq import Groq
import anthropic

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Je bent een short-form video editor die lange video's screent \
op zoek naar momenten die viraal kunnen gaan op TikTok/YouTube Shorts/Reels. \
Je kiest self-contained fragmenten: een sterke opening zin (hook), een duidelijke \
kern (grap, inzicht, controverse, emotie, verhaal met twist), en een natuurlijk \
eindpunt. Vermijd fragmenten die halverwege een gedachte beginnen of eindigen.

Je antwoordt UITSLUITEND met geldige JSON, geen uitleg, in dit formaat:
{"clips": [{"start": 12.4, "end": 41.2, "title": "korte titel", "hook_text": "korte pakkende openingstekst voor op het scherm"}]}
"""


def _build_transcript_text(transcript: dict) -> str:
    segments = transcript.get("segments", [])
    lines = []
    for seg in segments:
        lines.append(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text'].strip()}")
    return "\n".join(lines)


def select_clips(transcript: dict, settings, video_duration: float) -> list[dict]:
    transcript_text = _build_transcript_text(transcript)
    user_prompt = f"""Video duur: {video_duration:.0f} seconden.
Kies minimaal {settings.min_clips} en maximaal {settings.max_clips} fragmenten.
Elk fragment mag maximaal {settings.max_clip_seconds} seconden duren, \
streef naar ongeveer {settings.preferred_seconds} seconden per fragment.
Fragmenten mogen niet overlappen.

Transcript met tijdstempels:
{transcript_text}
"""

    if settings.llm_provider == "anthropic" and ANTHROPIC_API_KEY:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = resp.content[0].text
    else:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY ontbreekt. Zet deze als environment variable op Render.")
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        raw = resp.choices[0].message.content

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)
    clips = data.get("clips", [])

    # Basic sanity checks so a bad LLM response can't crash rendering
    clean = []
    for c in clips:
        start, end = float(c["start"]), float(c["end"])
        if end <= start:
            continue
        start = max(0, start)
        end = min(video_duration, end)
        if end - start < 3:
            continue
        clean.append({
            "start": start,
            "end": end,
            "title": c.get("title", "Clip"),
            "hook_text": c.get("hook_text", ""),
        })
    return clean[: settings.max_clips]
