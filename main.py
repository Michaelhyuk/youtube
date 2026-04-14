from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import os
import uuid
import threading
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Almacena el progreso de cada descarga
progress_store = {}

class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"          # video | audio | playlist | subs
    quality: str = "1080"        # max | 2160 | 1440 | 1080 | 720 | 480 | 360
    video_format: str = "mp4"    # mp4 | webm | mkv | mov | avi
    audio_format: str = "mp3"    # mp3 | aac | flac | wav | ogg | opus | m4a
    audio_bitrate: str = "192"   # 320 | 256 | 192 | 128 | 96 | 64
    vcodec: str = "auto"         # auto | h264 | h265 | av1 | vp9
    audio_track: str = "original"
    include_subs: bool = False
    sub_lang: str = "es"
    sub_format: str = "srt"
    hdr: bool = False
    fps60: bool = False
    metadata: bool = True
    trim: str = ""               # "00:01:00-00:03:00"
    playlist_range: str = ""     # "1-10"
    filename_template: str = "%(title)s.%(ext)s"

@app.get("/")
def root():
    return {"status": "ok", "service": "YT Vault API"}

@app.post("/info")
def get_info(req: DownloadRequest):
    """Obtiene información del video sin descargar"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if "entries" in info:
                # Es una playlist
                return {
                    "type": "playlist",
                    "title": info.get("title"),
                    "count": len(info["entries"]),
                    "entries": [
                        {"title": e.get("title"), "duration": e.get("duration")}
                        for e in info["entries"][:10]
                    ]
                }
            return {
                "type": "video",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader"),
                "view_count": info.get("view_count"),
                "formats": [
                    {"format_id": f.get("format_id"), "ext": f.get("ext"),
                     "height": f.get("height"), "filesize": f.get("filesize")}
                    for f in info.get("formats", [])
                    if f.get("height")
                ][-8:]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
def download(req: DownloadRequest):
    """Inicia descarga y devuelve un job_id para rastrear progreso"""
    job_id = str(uuid.uuid4())[:8]
    progress_store[job_id] = {"status": "starting", "percent": 0, "speed": "", "eta": "", "filename": ""}

    def run():
        out_path = os.path.join(DOWNLOAD_DIR, job_id)
        os.makedirs(out_path, exist_ok=True)

        def progress_hook(d):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "0%").strip().replace("%","")
                progress_store[job_id].update({
                    "status": "downloading",
                    "percent": float(pct) if pct else 0,
                    "speed": d.get("_speed_str", ""),
                    "eta": d.get("_eta_str", ""),
                    "filesize": d.get("_total_bytes_str", ""),
                })
            elif d["status"] == "finished":
                progress_store[job_id]["status"] = "processing"
                progress_store[job_id]["filename"] = d.get("filename", "")

        # Construir opciones según modo
        ydl_opts = {
            "outtmpl": os.path.join(out_path, req.filename_template),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if req.mode == "audio":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": req.audio_format,
                "preferredquality": req.audio_bitrate,
            }]
            if req.metadata:
                ydl_opts["postprocessors"].append({"key": "FFmpegMetadata"})
                ydl_opts["postprocessors"].append({"key": "EmbedThumbnail"})
                ydl_opts["writethumbnail"] = True

        elif req.mode == "subs":
            ydl_opts["skip_download"] = True
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = [req.sub_lang]
            ydl_opts["subtitlesformat"] = req.sub_format

        else:
            # Video
            quality = req.quality
            if quality == "max":
                fmt = "bestvideo+bestaudio/best"
            else:
                fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
            
            if req.fps60:
                fmt = fmt.replace("bestvideo", "bestvideo[fps>=50]")
            if not req.hdr:
                fmt = fmt.replace("bestvideo", "bestvideo[vcodec!*=av01]")

            ydl_opts["format"] = fmt
            ydl_opts["merge_output_format"] = req.video_format

            if req.vcodec != "auto":
                codec_map = {"h264": "avc1", "h265": "hev1", "av1": "av01", "vp9": "vp9"}
                ydl_opts["format"] = fmt + f"[vcodec*={codec_map.get(req.vcodec, '')}]" if req.vcodec in codec_map else fmt

            if req.include_subs:
                ydl_opts["writesubtitles"] = True
                ydl_opts["subtitleslangs"] = [req.sub_lang]

            if req.metadata:
                ydl_opts["postprocessors"] = [{"key": "FFmpegMetadata"}]

        if req.playlist_range:
            parts = req.playlist_range.split("-")
            if len(parts) == 2:
                ydl_opts["playliststart"] = int(parts[0])
                ydl_opts["playlistend"] = int(parts[1])

        if req.trim:
            parts = req.trim.replace(" ", "").split("-")
            if len(parts) == 2:
                ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(parts[0], parts[1])])
                ydl_opts["force_keyframes_at_cuts"] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([req.url])
            
            # Buscar archivo descargado
            files = os.listdir(out_path)
            if files:
                filename = files[0]
                progress_store[job_id].update({
                    "status": "done",
                    "percent": 100,
                    "download_url": f"/file/{job_id}/{filename}",
                    "filename": filename,
                })
            else:
                progress_store[job_id]["status"] = "error"
                progress_store[job_id]["error"] = "No se generó archivo"
        except Exception as e:
            progress_store[job_id]["status"] = "error"
            progress_store[job_id]["error"] = str(e)

        # Limpiar archivos viejos (>1 hora)
        def cleanup():
            time.sleep(3600)
            import shutil
            shutil.rmtree(out_path, ignore_errors=True)
            progress_store.pop(job_id, None)
        threading.Thread(target=cleanup, daemon=True).start()

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}

@app.get("/progress/{job_id}")
def get_progress(job_id: str):
    if job_id not in progress_store:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return progress_store[job_id]

@app.get("/file/{job_id}/{filename}")
def serve_file(job_id: str, filename: str):
    from fastapi.responses import FileResponse
    path = os.path.join(DOWNLOAD_DIR, job_id, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, filename=filename)
