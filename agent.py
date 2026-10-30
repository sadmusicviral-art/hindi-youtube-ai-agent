import os
import json
import time
import urllib.request
import urllib.error

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.8-flash"
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 120


def generate_video_script():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in GitHub Secrets")

    prompt = """
हिंदी में गोलू-सोनू की एक मौलिक, मजेदार कार्टून कहानी लिखो।
किरदार हर सीन में एक जैसे रहें:
गोलू: गोल-मटोल, भोला, खाने का शौकीन; पीली burger-print टी-शर्ट और नीली शॉर्ट्स।
सोनू: दुबला-पतला, चश्मा, होशियार और शरारती; हरी polo टी-शर्ट और भूरी शॉर्ट्स।

कहानी: जादुई समोसा। 5 छोटे सीन लिखो। हर सीन में:
1) जगह और क्या हो रहा है (2-3 वाक्य)
2) Narrator की लाइन
3) गोलू और सोनू के अलग-अलग छोटे संवाद
4) उस सीन के लिए English 3D cartoon image prompt, जिसमें दोनों किरदारों का वही लुक बना रहे।

आसान, स्वाभाविक और बोलचाल वाली हिंदी रखो। मजेदार घटनाएँ, साफ कहानी और अंत में अप्रत्याशित ट्विस्ट हो।
कहानी ओरिजिनल हो। जवाब बहुत लंबा न हो ताकि जल्दी जनरेट हो सके।
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        + "models/" + MODEL + ":generateContent?key=" + API_KEY
    )

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 1800
        }
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(f"Gemini request attempt {attempt}/{MAX_ATTEMPTS}...")
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                result = json.loads(response.read().decode("utf-8"))

            candidates = result.get("candidates", [])
            if not candidates:
                raise RuntimeError(
                    "Gemini returned no candidates: "
                    + json.dumps(result, ensure_ascii=False)[:1500]
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [part["text"] for part in parts if "text" in part]
            if not texts:
                raise RuntimeError("Gemini response did not contain text.")

            script = "\n".join(texts).strip()
            if not script:
                raise RuntimeError("Gemini returned an empty script.")

            with open("video_script.txt", "w", encoding="utf-8") as file:
                file.write(script + "\n")

            print("SUCCESS: Golu-Sonu story saved to video_script.txt")
            return

        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            # Retry temporary server/rate-limit errors; stop for invalid key/model/request.
            if error.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(
                    f"Gemini API HTTP {error.code}: {details[:1500]}"
                ) from error
            last_error = RuntimeError(f"Gemini API HTTP {error.code}: {details[:1000]}")
            print(f"Temporary Gemini API error: HTTP {error.code}")

        except (TimeoutError, urllib.error.URLError) as error:
            last_error = error
            print(f"Temporary network/timeout error: {error}")

        if attempt < MAX_ATTEMPTS:
            wait_seconds = 10 * attempt
            print(f"Retrying in {wait_seconds} seconds...")
            time.sleep(wait_seconds)

    raise RuntimeError(
        f"Gemini failed after {MAX_ATTEMPTS} attempts. Last error: {last_error}"
    )


if __name__ == "__main__":
    generate_video_script()
