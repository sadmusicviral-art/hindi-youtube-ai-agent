import os
import json
import re
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gtts import gTTS

API_KEY = os.getenv("GEMINI_API_KEY")
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
MAX_ATTEMPTS_PER_MODEL = 2
TIMEOUT_SECONDS = 120
REFERENCE_IMAGE = "Gemini_Generated_Image_7ahjea7ahjea7ahj.png"


def generate_video_script():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in GitHub Secrets")
    prompt = """
हिंदी में गोलू-सोनू की एक मौलिक, मजेदार कार्टून कहानी लिखो।
किरदार हर सीन में एक जैसे रहें:
गोलू: गोल-मटोल, भोला, खाने का शौकीन; पीली burger-print टी-शर्ट और नीली शॉर्ट्स।
सोनू: दुबला-पतला, चश्मा, होशियार और शरारती; हरी polo टी-शर्ट और भूरी शॉर्ट्स।
कहानी: जादुई समोसा। 5 छोटे सीन लिखो। हर सीन को "सीन 1", "सीन 2" ... से शुरू करो।
हर सीन में जगह/घटना, Narrator की लाइन और गोलू-सोनू के छोटे अलग-अलग संवाद हों।
हर सीन के अंत में "Image Prompt:" लिखकर एक छोटी English 3D cartoon image prompt दो।
आसान, स्वाभाविक और बोलचाल वाली हिंदी रखो। मजेदार घटनाएँ और अंत में अप्रत्याशित ट्विस्ट हो।
कहानी ओरिजिनल और संक्षिप्त रखो ताकि आवाज़ 1-2 मिनट की बने।
"""
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 1800}
    }
    last_error = None
    for model in MODELS:
        url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent?key=" + API_KEY
        request = urllib.request.Request(
            url, data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
            try:
                print(f"Trying {model}, attempt {attempt}/{MAX_ATTEMPTS_PER_MODEL}...")
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"{model} returned no candidates: {str(result)[:1000]}")
                parts = candidates[0].get("content", {}).get("parts", [])
                story = "\n".join(p["text"] for p in parts if "text" in p).strip()
                if not story:
                    raise RuntimeError(f"{model} response did not contain text.")
                Path("video_script.txt").write_text(story + "\n", encoding="utf-8")
                print(f"SUCCESS: Story generated with {model}")
                return story
            except urllib.error.HTTPError as error:
                details = error.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"{model} HTTP {error.code}: {details[:800]}")
                print(f"{model} API error: HTTP {error.code}")
                if error.code in (429, 500, 502, 503, 504):
                    break
                raise RuntimeError(f"Gemini API HTTP {error.code}: {details[:1200]}") from error
            except (TimeoutError, urllib.error.URLError) as error:
                last_error = error
                print(f"{model} network/timeout error: {error}")
                break
            if attempt < MAX_ATTEMPTS_PER_MODEL:
                time.sleep(8 * attempt)
    raise RuntimeError("All free Gemini models failed. Last error: " + str(last_error))


def get_font(size):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagariUI-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def split_scenes(story):
    chunks = re.split(r"(?=सीन\s*[0-9०-९]+)", story, flags=re.IGNORECASE)
    scenes = [chunk.strip() for chunk in chunks if chunk.strip()]
    return scenes[:6] if scenes else [story.strip()]


def spoken_text(story):
    lines = []
    for line in story.splitlines():
        value = line.strip()
        if not value:
            continue
        if re.match(r"^(image\s*prompt|इमेज\s*प्रॉम्प्ट)\s*:", value, re.IGNORECASE):
            continue
        if re.search(r"\b(3d cartoon|cinematic|high quality|character design|render)\b", value, re.IGNORECASE):
            continue
        value = re.sub(r"[*#_\x60]", "", value)
        lines.append(value)
    return "\n".join(lines)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    rows, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                rows.append(current)
            current = word
    if current:
        rows.append(current)
    return rows


def make_scene_card(reference, scene, index, total):
    width, height = 1280, 720
    source = Image.open(reference).convert("RGB")
    bg = source.resize((width, height), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(18))
    bg = Image.blend(bg, Image.new("RGB", (width, height), (20, 20, 28)), 0.48)
    foreground = source.copy()
    foreground.thumbnail((900, 650), Image.Resampling.LANCZOS)
    x = (width - foreground.width) // 2
    y = 20 + (650 - foreground.height) // 2
    bg.paste(foreground, (x, y))
    draw = ImageDraw.Draw(bg, "RGBA")
    draw.rounded_rectangle((35, 35, 1245, 685), radius=28, fill=(0, 0, 0, 105), outline=(255, 255, 255, 150), width=3)
    title_font = get_font(48)
    small_font = get_font(30)
    draw.text((75, 65), f"GOLU & SONU  |  SCENE {index}/{total}", font=title_font, fill="white", stroke_width=2, stroke_fill="black")
    clean = re.sub(r"(?i)image\s*prompt\s*:[\s\S]*", "", scene)
    clean = re.sub(r"इमेज\s*प्रॉम्प्ट\s*:[\s\S]*", "", clean).strip()
    clean = re.sub(r"[*#_\x60]", "", clean)
    rows = wrap_text(draw, clean, small_font, 1080)[:5]
    panel_top = 480
    draw.rounded_rectangle((60, panel_top, 1220, 650), radius=18, fill=(0, 0, 0, 190))
    yy = panel_top + 18
    for row in rows:
        draw.text((88, yy), row, font=small_font, fill="white", stroke_width=1, stroke_fill="black")
        yy += 34
    output = f"scene_{index:02d}.jpg"
    bg.convert("RGB").save(output, quality=88)
    return output


def create_character_narration(story):
    """Create separate character-style voices using free Hindi TTS plus pitch shaping."""
    audio_files = []
    lines = [line.strip() for line in story.splitlines() if line.strip()]
    print("Creating separate Hindi voices for Golu and Sonu...")
    for line_number, line in enumerate(lines, start=1):
        clean = re.sub(r"[*#_`]", "", line).strip()
        if re.match(r"^सीन\s*[0-9०-९]+\s*$", clean, re.IGNORECASE):
            continue
        if re.match(r"^(image\s*prompt|इमेज\s*प्रॉम्प्ट)\s*:", clean, re.IGNORECASE):
            continue
        speaker = "narrator"
        text = clean
        match = re.match(r"^(गोलू|सोनू|नैरेटर|Narrator)\s*[:：-]\s*(.+)$", clean, re.IGNORECASE)
        if match:
            name = match.group(1).lower()
            text = match.group(2).strip()
            if name == "गोलू":
                speaker = "golu"
            elif name == "सोनू":
                speaker = "sonu"
        if not text:
            continue
        raw_file = f"voice_raw_{line_number:03d}.mp3"
        out_file = f"voice_{line_number:03d}.mp3"
        gTTS(text=text, lang="hi", slow=False).save(raw_file)
        pitch = {"golu": 0.90, "sonu": 1.12, "narrator": 1.0}[speaker]
        if pitch == 1.0:
            subprocess.run(["ffmpeg", "-y", "-i", raw_file, "-c:a", "libmp3lame", "-q:a", "4", out_file],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        else:
            audio_filter = f"asetrate=44100*{pitch},aresample=44100,atempo={1.0/pitch:.6f}"
            subprocess.run(["ffmpeg", "-y", "-i", raw_file, "-af", audio_filter,
                            "-c:a", "libmp3lame", "-q:a", "4", out_file],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        audio_files.append(out_file)
    if not audio_files:
        raise RuntimeError("No spoken dialogue found for narration.")
    with open("audio_clips.txt", "w", encoding="utf-8", newline="\n") as file:
        for audio_file in audio_files:
            file.write(f"file '{audio_file}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "audio_clips.txt",
                    "-c:a", "libmp3lame", "-q:a", "4", "narration.mp3"],
                   check=True)
    print(f"SUCCESS: Created {len(audio_files)} voice segments.")


def build_video(story):
    if not os.path.exists(REFERENCE_IMAGE):
        raise FileNotFoundError(f"Character reference image not found: {REFERENCE_IMAGE}")
    speech = spoken_text(story)
    if len(speech) < 40:
        raise RuntimeError("Story text is too short to create narration.")
    create_character_narration(story)
    scenes = split_scenes(story)
    images = [make_scene_card(REFERENCE_IMAGE, scene, i + 1, len(scenes)) for i, scene in enumerate(scenes)]
    probe = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", "narration.mp3"
    ], text=True).strip()
    total_duration = float(probe)
    weights = [max(1, len(spoken_text(scene))) for scene in scenes]
    durations = [total_duration * weight / sum(weights) for weight in weights]
    clip_names = []
    print("Rendering each scene for its full duration...")
    for index, (image, duration) in enumerate(zip(images, durations), start=1):
        clip_name = f"clip_{index:02d}.mp4"
        motion_filter = (
            "zoompan=z='min(zoom+0.00035,1.10)':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            "d=1:s=1280x720:fps=24,"
            "fade=t=in:st=0:d=0.30,format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-framerate", "24",
            "-t", f"{duration:.3f}", "-i", image,
            "-vf", motion_filter, "-t", f"{duration:.3f}",
            "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-r", "24", clip_name
        ], check=True)
        clip_names.append(clip_name)

    with open("clips.txt", "w", encoding="utf-8") as file:
        for clip_name in clip_names:
            file.write(f"file '{clip_name}'\n")

    print("Joining full-length scenes with Hindi narration...")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "clips.txt",
        "-i", "narration.mp3", "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-movflags", "+faststart", "golu_sonu_cartoon.mp4"
    ], check=True)
    print("SUCCESS: Video created: golu_sonu_cartoon.mp4")


if __name__ == "__main__":
    story = generate_video_script()
    build_video(story)
