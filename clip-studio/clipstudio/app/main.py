import os
import json
import shutil
import asyncio
from fastapi import FastAPI, UploadFile, Form, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.models import Job, ClipSettings, ClipResult
from app import media, selector, render

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="Clip Studio")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

JOBS: dict[str, Job] = {}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/jobs")
async def create_job(
    youtube_url: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    settings: str = Form(...),
):
    if not youtube_url and not file:
        raise HTTPException(400, "Geef een YouTube-link of een videobestand op.")

    parsed_settings = ClipSettings(**json.loads(settings))
    job = Job.new()
    JOBS[job.id] = job

    job_dir = os.path.join(STORAGE_DIR, job.id)
    os.makedirs(job_dir, exist_ok=True)

    source_path = None
    if file:
        source_path = os.path.join(job_dir, "source_upload" + os.path.splitext(file.filename)[1])
        with open(source_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

    asyncio.create_task(run_pipeline(job.id, job_dir, youtube_url, source_path, parsed_settings))
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Job niet gevonden.")
    return job


@app.get("/api/clips/{job_id}/{filename}")
def get_clip(job_id: str, filename: str):
    path = os.path.join(STORAGE_DIR, job_id, "clips", filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Clip niet gevonden.")
    return FileResponse(path, media_type="video/mp4", filename=filename)


async def run_pipeline(job_id: str, job_dir: str, youtube_url: str | None, source_path: str | None, settings: ClipSettings):
    job = JOBS[job_id]
    try:
        if youtube_url:
            job.status, job.message = "downloading", "Video downloaden van YouTube..."
            source_path = await asyncio.to_thread(media.download_youtube, youtube_url, job_dir)
        job.progress = 15

        duration = await asyncio.to_thread(media.get_duration_seconds, source_path)
        if duration > 3600:
            raise RuntimeError("Video is langer dan 60 minuten, dat wordt (nog) niet ondersteund.")

        job.status, job.message = "transcribing", "Audio transcriberen..."
        audio_path = await asyncio.to_thread(media.extract_audio, source_path, job_dir)
        transcript = await asyncio.to_thread(media.transcribe, audio_path)
        job.progress = 45

        job.status, job.message = "selecting", "AI kiest de beste momenten..."
        clips_meta = await asyncio.to_thread(selector.select_clips, transcript, settings, duration)
        if not clips_meta:
            raise RuntimeError("De AI kon geen geschikte fragmenten vinden in deze video.")
        job.progress = 60

        job.status, job.message = "rendering", f"0/{len(clips_meta)} clips gerenderd..."
        clips_dir = os.path.join(job_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        words = transcript.get("words", [])
        results = []
        for i, clip in enumerate(clips_meta):
            srt_path = None
            if settings.subtitles and words:
                srt_path = os.path.join(clips_dir, f"clip_{i+1}.srt")
                await asyncio.to_thread(render.build_srt, words, clip["start"], clip["end"], srt_path)

            out_path = os.path.join(clips_dir, f"clip_{i+1}.mp4")
            await asyncio.to_thread(
                render.render_clip,
                source_path, clip["start"], clip["end"], out_path,
                settings.aspect_ratio, settings.resolution,
                srt_path, clip["hook_text"] if settings.hook else None,
                settings.highest_quality,
            )
            results.append(ClipResult(
                filename=os.path.basename(out_path),
                title=clip["title"],
                start=clip["start"],
                end=clip["end"],
                hook_text=clip["hook_text"],
            ))
            job.progress = 60 + int(35 * (i + 1) / len(clips_meta))
            job.message = f"{i+1}/{len(clips_meta)} clips gerenderd..."

        job.clips = results
        job.status, job.message, job.progress = "done", "Klaar!", 100

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.message = f"Fout: {e}"


app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="static")
