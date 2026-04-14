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
COOKIES_FILE = "/tmp/yt_cookies.txt"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Escribir cookies de YouTube al iniciar
COOKIES_CONTENT = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.youtube.com	TRUE	/	TRUE	1803074247	LOGIN_INFO	AFmmF2swRgIhAKPj28pJ3Bj5B7MOOEhKRKOiUN0MUayCtUVkONTljEBlAiEAjFHPfevbcs8KYc57w6uiVwFuBqiWuIFHJzTogJVbu5w:QUQ3MjNmdzg1VG1Eam1nX1F3U3lGNHZ3ZF9mOGJ5ZHVOTlRFamJsNDg2SWJqcUkzdy1yeXhqZlh6Y0RWaWJDNC1NcW8za2FQbmYtLUxING1SZGlHVU9zaVNyUzREaTAzdFRtN0kxUjhEemxwdFk1dC1od24xVlhfY0xWN004OHM1bVdId25tVXZKM1UwbkRVS0FwbUJnQmc1Yi1mMVFaY2lR
.youtube.com	TRUE	/	TRUE	1810694537	PREF	f6=40000000&f7=100&tz=America.Mexico_City&f5=30000
.youtube.com	TRUE	/	TRUE	1791148588	__Secure-BUCKET	CNYD
.youtube.com	TRUE	/	FALSE	1810477158	SID	g.a0008wjz5v6sAcSctPBwwBvX0b8Vba3vIUgV3h6nIPQSlbm4MwgOck5Pu7nIhNm_HsypJ0OHVgACgYKASYSARcSFQHGX2MiM7BTOIVuEBlGDqSHNufDvBoVAUF8yKoHtxa_-y_NwvbVBpzH4c_T0076
.youtube.com	TRUE	/	TRUE	1810477158	__Secure-1PSID	g.a0008wjz5v6sAcSctPBwwBvX0b8Vba3vIUgV3h6nIPQSlbm4MwgOmWHSTtZ3ny3H20S-4ZFBXAACgYKAUYSARcSFQHGX2MilvP5Vl4Ipqwf615kvkOdahoVAUF8yKqnoiyfOk07Pig473e570KX0076
.youtube.com	TRUE	/	TRUE	1810477158	__Secure-3PSID	g.a0008wjz5v6sAcSctPBwwBvX0b8Vba3vIUgV3h6nIPQSlbm4MwgORTVEZ8NTaSEMqF_Jwa64AQACgYKAccSARcSFQHGX2MiLiP5BxYajVFUHjAbO0zlaRoVAUF8yKpf_qMLNRWDTwHLgxY3X6at0076
.youtube.com	TRUE	/	FALSE	1810477158	HSID	AGOIuZUgGwqQmR6Sm
.youtube.com	TRUE	/	TRUE	1810477158	SSID	AL4zHw4qyDSEEBaYS
.youtube.com	TRUE	/	FALSE	1810477158	APISID	io6g1InSUCQo43dI/A5cOrgCYzBFu3vHvE
.youtube.com	TRUE	/	TRUE	1810477158	SAPISID	zEViDp5mfO7rCSrM/AdALkB62nnc5CFzLl
.youtube.com	TRUE	/	TRUE	1810477158	__Secure-1PAPISID	zEViDp5mfO7rCSrM/AdALkB62nnc5CFzLl
.youtube.com	TRUE	/	TRUE	1810477158	__Secure-3PAPISID	zEViDp5mfO7rCSrM/AdALkB62nnc5CFzLl
.youtube.com	TRUE	/	TRUE	1807670540	__Secure-1PSIDTS	sidts-CjABWhotCer4ZmQ7AXjTzJA1DXXQUBFu1YqwAS7Tg1y2-Q0L5M31KfzFU_GPkzT4NFwQAA
.youtube.com	TRUE	/	TRUE	1807670540	__Secure-3PSIDTS	sidts-CjABWhotCer4ZmQ7AXjTzJA1DXXQUBFu1YqwAS7Tg1y2-Q0L5M31KfzFU_GPkzT4NFwQAA
.youtube.com	TRUE	/	FALSE	1807670540	SIDCC	AKEyXzVXAjhipRkPf2PVdjw5gzbpAgLNQio-1qiz_vQ1GKZ3MLWsamCTsaWCEQ7HuQkR2L3t2Q
.youtube.com	TRUE	/	TRUE	1807670540	__Secure-1PSIDCC	AKEyXzX1g_lXF6B91--Ry4iF4pEpPu8DL_mcIWs2vOtOH2OBGONYcg_f2WD7nCRFC61xyuqSux4
.youtube.com	TRUE	/	TRUE	1807670540	__Secure-3PSIDCC	AKEyXzW4V7n8-mDWqFY0otiYCBE0uu3gzV11vttQJiPR2mYryyBwtLt8z3qvKo3JI5M3AA1Gww
.youtube.com	TRUE	/	TRUE	1791686536	VISITOR_INFO1_LIVE	ZHdzu7Y_sS0
.youtube.com	TRUE	/	TRUE	1791686536	VISITOR_PRIVACY_METADATA	CgJNWBIEGgAgIA%3D%3D
.youtube.com	TRUE	/	TRUE	1791686534	__Secure-YNID	17.YT=Hd1FqTBRylxoizdMunAgsFMiik4PDmX1_6r_HpGhn39igigq-8TU-kP99vc1YPF7AwUc8zCRVZaboQSE30P_RmSyxXu3b9Qc3brhA24lU3NoaOVzkBhaDYbdF6dxbaJ_w7lkWXJYJzAPRdycz1LHaEy9Q9RoyNa1NHuVMnY30lC26d1UWAWTcETMxYgsAggSabMokYo3wqeXcpZd2m5pPftn7S0VdmAcEOX1vaHXol5OU3zU2HgPG4i6GUcTfqdwQBg9LkGeboIALMJ8PIYAvwisfUYU25t9wyPtCfEESNmxjNVnkJfSHy0RqSIhyd5ImoRQdFO_zoypFkny7QExwg
.youtube.com	TRUE	/	TRUE	0	YSC	XxoQt2PxAUo
.youtube.com	TRUE	/	TRUE	1791686534	__Secure-ROLLOUT_TOKEN	CKuyuq7YxOj8dRCa2M7DwI6SAxi-tq3gqOyTAw%3D%3D
"""

with open(COOKIES_FILE, "w") as f:
    f.write(COOKIES_CONTENT)

progress_store = {}

class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"
    quality: str = "1080"
    video_format: str = "mp4"
    audio_format: str = "mp3"
    audio_bitrate: str = "192"
    vcodec: str = "auto"
    audio_track: str = "original"
    include_subs: bool = False
    sub_lang: str = "es"
    sub_format: str = "srt"
    hdr: bool = False
    fps60: bool = False
    metadata: bool = True
    trim: str = ""
    playlist_range: str = ""
    filename_template: str = "%(title)s.%(ext)s"

@app.get("/")
def root():
    return {"status": "ok", "service": "YT Vault API"}

@app.post("/info")
def get_info(req: DownloadRequest):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "cookiefile": COOKIES_FILE,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(req.url, download=False)
            if "entries" in info:
                return {
                    "type": "playlist",
                    "title": info.get("title"),
                    "count": len(info["entries"]),
                }
            return {
                "type": "video",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
                "uploader": info.get("uploader"),
                "view_count": info.get("view_count"),
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/download")
def download(req: DownloadRequest):
    job_id = str(uuid.uuid4())[:8]
    progress_store[job_id] = {"status": "starting", "percent": 0, "speed": "", "eta": "", "filename": ""}

    def run():
        out_path = os.path.join(DOWNLOAD_DIR, job_id)
        os.makedirs(out_path, exist_ok=True)

        def progress_hook(d):
            if d["status"] == "downloading":
                pct = d.get("_percent_str", "0%").strip().replace("%", "")
                try:
                    progress_store[job_id].update({
                        "status": "downloading",
                        "percent": float(pct),
                        "speed": d.get("_speed_str", ""),
                        "eta": d.get("_eta_str", ""),
                        "filesize": d.get("_total_bytes_str", ""),
                    })
                except:
                    pass
            elif d["status"] == "finished":
                progress_store[job_id]["status"] = "processing"

        ydl_opts = {
            "outtmpl": os.path.join(out_path, req.filename_template),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "cookiefile": COOKIES_FILE,
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

        elif req.mode == "subs":
            ydl_opts["skip_download"] = True
            ydl_opts["writesubtitles"] = True
            ydl_opts["writeautomaticsub"] = True
            ydl_opts["subtitleslangs"] = [req.sub_lang]
            ydl_opts["subtitlesformat"] = req.sub_format

        else:
            quality = req.quality
            fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]" if quality != "max" else "bestvideo+bestaudio/best"
            ydl_opts["format"] = fmt
            ydl_opts["merge_output_format"] = req.video_format
            if req.include_subs:
                ydl_opts["writesubtitles"] = True
                ydl_opts["subtitleslangs"] = [req.sub_lang]
            if req.metadata:
                ydl_opts["postprocessors"] = [{"key": "FFmpegMetadata"}]

        if req.playlist_range:
            parts = req.playlist_range.split("-")
            if len(parts) == 2:
                try:
                    ydl_opts["playliststart"] = int(parts[0])
                    ydl_opts["playlistend"] = int(parts[1])
                except:
                    pass

        if req.trim:
            parts = req.trim.replace(" ", "").split("-")
            if len(parts) == 2:
                ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(parts[0], parts[1])])
                ydl_opts["force_keyframes_at_cuts"] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([req.url])

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
