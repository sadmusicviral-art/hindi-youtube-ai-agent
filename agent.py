import os
import json
import time
import urllib.request
import urllib.error

API_KEY = os.getenv("GEMINI_API_KEY")
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
MAX_ATTEMPTS_PER_MODEL = 2
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

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 1800
        }
    }

    last_error = None

    for model in MODELS:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model + ":generateContent?key=" + API_KEY
        )
        request = urllib.request.Request(
            url,
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        for attempt in range(1, MAX_ATTEMPTS_PER_MODEL + 1):
            try:
                print(f"Trying {model}, attempt {attempt}/{MAX_ATTEMPTS_PER_MODEL}...")
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    result = json.loads(response.read().decode("utf-8"))

                candidates = result.get("candidates", [])
                if not candidates:
                    raise RuntimeError(
                        f"{model} returned no candidates: "
                        + json.dumps(result, ensure_ascii=False)[:1500]
                    )

                parts = candidates[0].get("content", {}).get("parts", [])
                texts = [part["text"] for part in parts if "text" in part]
                if not texts:
                    raise RuntimeError(f"{model} response did not contain text.")

                script = "\n".join(texts).strip()
                if not script:
                    raise RuntimeError(f"{model} returned an empty script.")

                with open("video_script.txt", "w", encoding="utf-8") as file:
                    file.write(script + "\n")

                print(f"SUCCESS: Story generated with {model} and saved to video_script.txt")
                return

            except urllib.error.HTTPError as error:
                details = error.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"{model} HTTP {error.code}: {details[:1000]}")
                print(f"{model} API error: HTTP {error.code}")

                # Try the backup model for unavailable/busy service or quota errors.
                if error.code in (429, 500, 502, 503, 504):
                    break
                raise RuntimeError(
                    f"Gemini API HTTP {error.code}: {details[:1500]}"
                ) from error

            except (TimeoutError, urllib.error.URLError) as error:
                last_error = error
                print(f"{model} network/timeout error: {error}")
                break

            if attempt < MAX_ATTEMPTS_PER_MODEL:
                time.sleep(8 * attempt)

    raise RuntimeError(
        "All free Gemini models failed. Last error: " + str(last_error)
    )


if __name__ == "__main__":
    generate_video_script()
