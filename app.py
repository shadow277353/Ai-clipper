import os, json, uuid, subprocess, threading, re
from pathlib import Path
from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string, flash
from werkzeug.utils import secure_filename

BASE = Path(os.getenv("DATA_DIR", "data")).resolve()
UPLOADS, OUTPUTS = BASE / "uploads", BASE / "clips"
for p in (UPLOADS, OUTPUTS): p.mkdir(parents=True, exist_ok=True)
MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "800"))
ALLOWED = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024
jobs, lock = {}, threading.Lock()

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Auto Clipper</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b1020;color:#edf1ff;font:16px/1.5 system-ui,sans-serif}.wrap{max-width:1000px;margin:auto;padding:32px 18px}.top{display:flex;align-items:center;gap:12px}.logo{background:#8b5cf6;border-radius:14px;padding:10px;font-size:24px}h1{margin:0;font-size:clamp(28px,5vw,44px);letter-spacing:-1px}.muted{color:#a9b4d0}.hero{margin:24px 0 20px;padding:26px;border:1px solid #293251;border-radius:22px;background:linear-gradient(130deg,#171d38,#11182c)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}.card{padding:20px;border:1px solid #293251;border-radius:18px;background:#11182b;margin:16px 0}label{display:block;margin:12px 0 5px;font-weight:650}input,select,button{font:inherit}input[type=file],input[type=text],select{width:100%;padding:12px;border:1px solid #384363;border-radius:10px;background:#0b1020;color:#edf1ff}button,.btn{display:inline-block;border:0;border-radius:11px;background:#8b5cf6;color:white;font-weight:750;padding:12px 17px;cursor:pointer;text-decoration:none;margin-top:12px}.secondary{background:#273251}.pill{display:inline-block;background:#222b49;border-radius:30px;padding:4px 10px;font-size:13px}.notice{padding:12px;border-radius:10px;background:#25213d;margin:12px 0}.clip{padding:14px;border:1px solid #303a59;border-radius:12px;margin-top:12px}.clip h3{margin:0 0 6px}.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}small,footer{color:#a9b4d0}footer{padding:24px 0;font-size:13px}a{color:#c4b5fd}</style></head><body><div class="wrap">
<div class="top"><div class="logo">✂</div><div><h1>Auto Clipper</h1><div class="muted">Turn long videos into ready-to-review shorts.</div></div></div>
<div class="hero"><span class="pill">AI-assisted video workflow</span><h2>Find the moments worth clipping.</h2><p class="muted">Upload a video, detect candidate moments, crop to vertical, and optionally create subtitles. You control what gets downloaded or published.</p>
<form action="/upload" method="post" enctype="multipart/form-data"><label for="video">Video file</label><input id="video" name="video" type="file" accept="video/*" required><div class="grid"><div><label for="count">Number of clips</label><select id="count" name="count"><option>3</option><option selected>5</option><option>8</option><option>10</option></select></div><div><label for="duration">Clip length (seconds)</label><select id="duration" name="duration"><option>20</option><option selected>30</option><option>45</option><option>60</option></select></div><div><label for="subs">Subtitles</label><select id="subs" name="subs"><option value="off">Off (faster)</option><option value="on">Whisper subtitles (needs extra RAM)</option></select></div></div><button type="submit">Upload &amp; analyze</button></form></div>
{% with messages = get_flashed_messages() %}{% for m in messages %}<div class="notice">{{m}}</div>{% endfor %}{% endwith %}
{% if job %}<section class="card"><div class="row"><h2 style="margin:0">Job {{job.id[:8]}}</h2><span class="pill">{{job.status}}</span></div><p class="muted">{{job.message}}</p>{% if job.error %}<div class="notice">{{job.error}}</div>{% endif %}
{% for clip in job.clips %}<div class="clip"><h3>{{clip.name}}</h3><p class="muted">Start {{clip.start}}s · {{clip.duration}}s</p><div class="row"><a class="btn" href="/download/{{job.id}}/{{clip.name}}">Download MP4</a>{% if clip.srt %}<a class="btn secondary" href="/download/{{job.id}}/{{clip.srt}}">Download subtitles</a>{% endif %}</div><form action="/youtube/{{job.id}}/{{clip.name}}" method="post"><label>Optional YouTube title</label><input name="title" type="text" maxlength="100" value="{{clip.name[:-4]}}"><label>Visibility</label><select name="privacy"><option value="private">Private</option><option value="unlisted">Unlisted</option><option value="public">Public</option></select><button class="secondary" type="submit">Publish this clip to YouTube</button></form></div>{% endfor %}</section>{% endif %}
<section class="grid"><div class="card"><h3>How it works</h3><p class="muted">Uses FFmpeg scene changes and audio activity to suggest segments. This baseline finds candidates but cannot guarantee viral moments.</p></div><div class="card"><h3>Privacy first</h3><p class="muted">Uploads are stored on the server. Use private deployment and persistent storage for personal footage.</p></div><div class="card"><h3>YouTube publishing</h3><p class="muted">Requires your own Google OAuth credentials and YouTube Data API enabled. Uploads require a manual click and default to private.</p></div></section><footer>Auto Clipper · Review generated clips and confirm you have permission to publish source material.</footer></div></body></html>"""

def run(cmd, timeout=1800):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout or "Command failed")[-1800:])
    return p.stdout

def duration_seconds(path):
    return max(0.0, float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],120).strip()))

def candidates(path, count, length):
    total=duration_seconds(path)
    if total < 3: raise ValueError("The video is too short to clip.")
    length=min(float(length),max(3.0,total))
    centers=[total*(i+1)/(count+1) for i in range(count)]
    try:
        p=subprocess.run(["ffmpeg","-hide_banner","-i",str(path),"-vf","select=gt(scene\,0.28),showinfo","-an","-f","null","-"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=600)
        stamps=[float(x) for x in re.findall(r"pts_time:([0-9.]+)",p.stderr)]
        picked=[]
        for s in sorted(stamps,key=lambda s:min(abs(s-c) for c in centers)):
            if all(abs(s-old)>length*.7 for old in picked): picked.append(s)
            if len(picked)>=count: break
        if picked: centers=picked
    except Exception: pass
    starts=[]
    for center in sorted(centers):
        start=max(0,min(total-length,center-length/2))
        if all(abs(start-old)>=length*.65 for old in starts): starts.append(start)
    return total,[(s,min(length,total-s)) for s in sorted(starts)[:count]]

def stamp(t):
    ms=int(max(0,t)*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); sec,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"

def render_clip(src,dst,start,dur):
    run(["ffmpeg","-y","-hide_banner","-ss",str(start),"-i",str(src),"-t",str(dur),"-vf","scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,setsar=1","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart",str(dst)],1200)

def transcribe(src,dst,start,dur,jobdir):
    from faster_whisper import WhisperModel
    model=WhisperModel(os.getenv("WHISPER_MODEL","base"),device="cpu",compute_type="int8")
    segments,_=model.transcribe(str(src),vad_filter=True)
    srt=jobdir/(dst.stem+".srt"); lines=[]; idx=1
    for seg in segments:
        a=max(seg.start,start); b=min(seg.end,start+dur)
        if b>a: lines += [str(idx),f"{stamp(a-start)} --> {stamp(b-start)}",seg.text.strip(),""]; idx+=1
    srt.write_text("\n".join(lines),encoding="utf-8")
    if lines:
        escaped=str(srt).replace("\\","/").replace(":","\\:")
        run(["ffmpeg","-y","-hide_banner","-i",str(src),"-ss",str(start),"-t",str(dur),"-vf",f"scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,subtitles='{escaped}':force_style='FontSize=18,Outline=2,Shadow=1,Alignment=2,MarginV=70'","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-movflags","+faststart",str(dst)],1200)
    else: render_clip(src,dst,start,dur)
    return srt.name if lines else None

def process(jid,source,count,clip_len,subs):
    jobdir=OUTPUTS/jid; jobdir.mkdir(parents=True,exist_ok=True)
    try:
        with lock: jobs[jid].update(status="Processing",message="Analyzing video and rendering clips…")
        total,segments=candidates(source,count,clip_len); clips=[]
        for i,(start,dur) in enumerate(segments,1):
            name=f"clip-{i:02d}.mp4"; dst=jobdir/name; srt=None
            if subs:
                try: srt=transcribe(source,dst,start,dur,jobdir)
                except Exception as e:
                    with lock: jobs[jid]["message"]="Subtitles unavailable; rendering clips without them. "+str(e)[:140]
                    render_clip(source,dst,start,dur)
            else: render_clip(source,dst,start,dur)
            clips.append({"name":name,"start":round(start,1),"duration":round(dur,1),"srt":srt})
            with lock: jobs[jid]["clips"]=clips.copy()
        with lock: jobs[jid].update(status="Complete",message=f"Rendered {len(clips)} clips from a {round(total,1)} second video.")
    except Exception as e:
        with lock: jobs[jid].update(status="Error",message="Processing failed.",error=str(e)[-1800:])

@app.get("/")
def index():
    return render_template_string(HTML,job=jobs.get(request.args.get("job")))

@app.post("/upload")
def upload():
    f=request.files.get("video")
    if not f or not f.filename: flash("Choose a video file first."); return redirect(url_for("index"))
    ext=Path(secure_filename(f.filename)).suffix.lower()
    if ext not in ALLOWED: flash("Unsupported file type. Use MP4, MOV, MKV, WEBM, M4V or AVI."); return redirect(url_for("index"))
    jid=uuid.uuid4().hex; path=UPLOADS/(jid+ext); f.save(path)
    with lock: jobs[jid]={"id":jid,"status":"Queued","message":"Upload received.","error":"","clips":[]}
    threading.Thread(target=process,args=(jid,path,int(request.form.get("count",5)),int(request.form.get("duration",30)),request.form.get("subs")=="on"),daemon=True).start()
    return redirect(url_for("index",job=jid),code=303)

@app.get("/download/<jid>/<path:name>")
def download(jid,name):
    folder=(OUTPUTS/jid).resolve()
    if folder.parent!=OUTPUTS.resolve() or not (folder/name).is_file(): return "File not found",404
    return send_from_directory(folder,name,as_attachment=True)

@app.post("/youtube/<jid>/<path:name>")
def youtube_upload(jid,name):
    if not (OUTPUTS/jid/name).is_file(): flash("Clip not found."); return redirect(url_for("index",job=jid))
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        token=os.getenv("YOUTUBE_TOKEN_JSON")
        if not token: raise RuntimeError("Set YOUTUBE_TOKEN_JSON with a valid OAuth token JSON.")
        creds=Credentials.from_authorized_user_info(json.loads(token),scopes=["https://www.googleapis.com/auth/youtube.upload"])
        yt=build("youtube","v3",credentials=creds)
        title=(request.form.get("title") or name)[:100]; privacy=request.form.get("privacy","private")
        if privacy not in ("private","unlisted","public"): privacy="private"
        body={"snippet":{"title":title,"description":"Created with Auto Clipper.","categoryId":"22"},"status":{"privacyStatus":privacy}}
        response=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(OUTPUTS/jid/name),chunksize=-1,resumable=True)).execute()
        flash("YouTube upload complete: https://www.youtube.com/watch?v="+response["id"])
    except Exception as e: flash("YouTube upload failed: "+str(e)[:300])
    return redirect(url_for("index",job=jid))

@app.errorhandler(413)
def too_large(_): return f"Upload too large. Limit is {MAX_MB} MB.",413

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
