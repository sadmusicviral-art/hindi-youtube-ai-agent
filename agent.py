import os, json, re, time, math, wave, struct, random, subprocess, urllib.request, urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS

API_KEY = os.getenv("GEMINI_API_KEY")
OUTPUT = "original_hindi_song.mp4"
THEMES = ["अधूरा प्यार और जुदाई", "पहली मोहब्बत की याद", "धोखे के बाद नई शुरुआत", "माँ का प्यार", "दोस्ती और यारी", "मेहनत और सपने", "बारिश में पुरानी यादें", "देसी स्वैग और आत्मविश्वास", "गाँव की मिट्टी और बचपन"]

def generate_song():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY GitHub Secret missing")
    theme = random.choice(THEMES)
    prompt = f"""आज का विषय: {theme}
एक नया, पूरी तरह मौलिक हिंदी गीत लिखो। किसी मौजूदा गाने/गायक की नकल नहीं।
सरल बोल, स्वाभाविक तुक, याद रहने वाला मुखड़ा। संरचना [Intro], [Verse 1], [Pre-Chorus], [Chorus], [Verse 2], [Chorus], [Bridge], [Final Chorus], [Outro]।
पहली पंक्ति 'शीर्षक: ...' हो। हर पंक्ति छोटी और साफ हो। केवल शीर्षक और गीत के बोल दो।"""
    payload = {"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.85,"maxOutputTokens":5000}}
    errors=[]
    for model in ["gemini-3.8-flash", "gemini-3.5-flash-lite"]:
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        req=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Content-Type":"application/json"},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=120) as res: data=json.loads(res.read().decode())
            parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
            text="\n".join(p.get("text","") for p in parts).strip()
            if len(text)<250: raise RuntimeError("Gemini returned too little lyric text")
            Path("song_lyrics.txt").write_text(text+"\n",encoding="utf-8")
            print("Generated original lyrics on theme:",theme)
            return text,theme
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            errors.append(f"{model}: HTTP {e.code}: {detail[:600]}")
            print(errors[-1])
        except Exception as e:
            errors.append(f"{model}: {type(e).__name__}: {e}")
            print(errors[-1])
    raise RuntimeError("Song writing failed: "+" | ".join(errors))

def font(size):
    for p in ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf","/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def lyric_sections(text):
    title="आज का नया हिंदी गाना"
    m=re.search(r"शीर्षक\s*[:：-]\s*(.+)",text)
    if m: title=m.group(1).strip()
    sections=[]
    current="गीत"
    lines=[]
    for raw in text.splitlines():
        s=raw.strip()
        if not s: continue
        if re.match(r"शीर्षक\s*[:：-]",s): continue
        if s.startswith("[") and s.endswith("]"):
            if lines: sections.append((current,lines)); lines=[]
            current=s.strip("[] ")
        elif not s.startswith("#"):
            s=re.sub(r"[*_\x60]","",s).strip()
            if s: lines.append(s)
    if lines: sections.append((current,lines))
    if not sections: raise RuntimeError("Lyrics had no usable sections")
    return title,sections

def render_card(title,section,lines,index):
    W,H=1280,720
    im=Image.new("RGB",(W,H),(18+(index*13)%35,22+(index*9)%28,55+(index*17)%55))
    d=ImageDraw.Draw(im,"RGBA")
    for r in range(5):
        d.ellipse((80+r*30,80+r*22,1200-r*30,640-r*22),outline=(255,210,150,35),width=3)
    d.rounded_rectangle((65,55,1215,665),radius=35,fill=(5,8,24,155),outline=(255,255,255,100),width=2)
    d.text((100,85),title[:48],font=font(42),fill=(255,220,150))
    d.text((100,165),section.upper(),font=font(30),fill=(120,220,255))
    y=245
    for line in lines[:7]:
        # Keep each line readable; wrap by character count.
        chunks=[line[i:i+34] for i in range(0,len(line),34)]
        for chunk in chunks:
            d.text((105,y),chunk,font=font(34),fill="white",stroke_width=1,stroke_fill=(0,0,0))
            y+=52
    path=f"lyric_{index:02d}.jpg"
    im.save(path,quality=92)
    return path

def make_instrumental(duration):
    # Original, simple synthesized chord-and-pulse backing; not a commercial-quality recorded band.
    sr=44100
    chords=[(261.63,329.63,392.00),(220.00,261.63,329.63),(174.61,220.00,261.63),(196.00,246.94,293.66)]
    total=int(duration*sr)
    with wave.open("instrumental.wav","wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        buf=bytearray()
        for n in range(total):
            t=n/sr
            chord=chords[int(t/4)%len(chords)]
            fade=min(1.0,t/2,(duration-t)/2 if duration-t>0 else 0.0)
            v=sum(math.sin(2*math.pi*f*t) for f in chord)*0.035
            # soft rhythmic pulse
            beat=0.025*math.sin(2*math.pi*90*t)*math.exp(-((t%0.5)/0.12)*3)
            sample=max(-1,min(1,(v+beat)*max(0,fade)))
            buf.extend(struct.pack("<h",int(sample*32767)))
            if len(buf)>=65536:
                wf.writeframes(buf); buf.clear()
        if buf: wf.writeframes(buf)

def build_video(song):
    title,sections=lyric_sections(song)
    clean=[]
    for name,lines in sections:
        clean.extend(lines)
    narration="। ".join(clean)
    if len(narration)<100: raise RuntimeError("Lyrics too short for narration")
    print("Creating Hindi spoken vocal using gTTS (this is speech, NOT singing).")
    gTTS(text=narration,lang="hi",slow=False).save("narration.mp3")
    probe=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1","narration.mp3"],text=True)
    duration=float(probe)
    weights=[max(1,sum(len(x) for x in lines)) for _,lines in sections]
    total=sum(weights)
    clips=[]
    for i,((name,lines),weight) in enumerate(zip(sections,weights),1):
        img=render_card(title,name,lines,i)
        seconds=max(2.5,duration*weight/total)
        clip=f"part_{i:02d}.mp4"
        vf="scale=1280:720,zoompan=z='min(zoom+0.00025,1.06)':d=1:s=1280x720:fps=24,format=yuv420p"
        subprocess.run(["ffmpeg","-y","-loop","1","-i",img,"-t",str(seconds),"-vf",vf,"-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",clip],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        clips.append(clip)
    with open("parts.txt","w") as f:
        for c in clips: f.write(f"file '{c}'\n")
    make_instrumental(duration+2)
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i","parts.txt","-i","narration.mp3","-i","instrumental.wav","-filter_complex","[2:a]volume=0.20[m];[1:a]volume=1.0[v];[v][m]amix=inputs=2:duration=first:dropout_transition=2,alimiter=limit=0.95[a]","-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",OUTPUT],check=True)
    Path("song_title.txt").write_text(title,encoding="utf-8")
    print("Rendered lyric video:",OUTPUT,"duration:",round(duration,1),"seconds")

def upload_to_youtube():
    required=["YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN"]
    missing=[x for x in required if not os.getenv(x)]
    if missing: raise RuntimeError("Missing YouTube secrets: "+", ".join(missing))
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds=Credentials(None,refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],token_uri="https://oauth2.googleapis.com/token",client_id=os.environ["YOUTUBE_CLIENT_ID"],client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],scopes=["https://www.googleapis.com/auth/youtube.upload"])
    creds.refresh(Request())
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    title=Path("song_title.txt").read_text(encoding="utf-8").strip()
    yt_title=(title+" | Original Hindi Lyrics Video")[:100]
    desc=f"{title}\n\nएक नया मौलिक हिंदी गीत। इस वीडियो में हिंदी टेक्स्ट-टू-स्पीच आवाज़ और कंप्यूटर से बनाया गया साधारण बैकग्राउंड संगीत है; यह पेशेवर गायकी की रिकॉर्डिंग नहीं है।\n\n#HindiSong #OriginalSong #HindiMusic #LyricsVideo"
    body={"snippet":{"title":yt_title,"description":desc,"tags":["Hindi Song","Original Hindi Song","Hindi Lyrics","Original Song","Lyrics Video"],"categoryId":"10"},"status":{"privacyStatus":"private","selfDeclaredMadeForKids":False}}
    media=MediaFileUpload(OUTPUT,mimetype="video/mp4",resumable=True)
    result=yt.videos().insert(part="snippet,status",body=body,media_body=media).execute()
    print("UPLOAD SUCCESS. Video ID:",result.get("id"))
    print("Uploaded PRIVATE for review.")

if __name__=="__main__":
    song,theme=generate_song()
    build_video(song)
    upload_to_youtube()
