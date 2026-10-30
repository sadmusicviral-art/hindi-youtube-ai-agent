
import os
import json
import urllib.request
import urllib.error

API_KEY = os.getenv("GEMINI_API_KEY")

def generate_video_script():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    prompt = """
एक मजेदार ओरिजिनल हिंदी 3D कार्टून कहानी लिखो।

मुख्य किरदार:
1. गोलू: मोटा, खाने का शौकीन, भोला और मजेदार लड़का।
2. सोनू: दुबला-पतला, होशियार और शरारती लड़का।

कहानी: गोलू-सोनू और जादुई समोसा।

निर्देश:
- कहानी 3 से 5 मिनट की हो।
- गोलू और सोनू के अलग-अलग संवाद हों।
- महिला Narrator की लाइनें भी हों।
- मजेदार घटनाएँ और अंत में बड़ा ट्विस्ट हो।
- हर सीन का विवरण और 3D Cartoon Image Prompt दो।
- किरदारों का लुक हर सीन में एक जैसा रहे।
- सभी किरदार और कहानी ओरिजिनल हों।
- आसान हिंदी का उपयोग करो।
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent?key=" + API_KEY
    )

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates", [])

        if not candidates:
            raise RuntimeError(
                "Gemini ne script nahi di: " +
                json.dumps(result, ensure_ascii=False)[:2000]
            )

        parts = candidates[0].get("content", {}).get("parts", [])

        texts = [
            part["text"]
            for part in parts
            if "text" in part
        ]

        if not texts:
            raise RuntimeError("Gemini response mein text nahi mila.")

        script = "\n".join(texts)

        with open("video_script.txt", "w", encoding="utf-8") as file:
            file.write(script)

        print("Golu Sonu cartoon story created successfully!")

    except urllib.error.HTTPError as error:
        print("Gemini API Error:", error.code)
        print(error.read().decode("utf-8"))
        raise

if __name__ == "__main__":
    generate_video_script()
    
