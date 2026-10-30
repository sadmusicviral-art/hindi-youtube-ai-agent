import os
import json
import urllib.request

API_KEY = os.getenv("GEMINI_API_KEY")

def generate_video_script():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    prompt = """
एक मजेदार ओरिजिनल हिंदी 3D कार्टून कहानी लिखो।

मुख्य किरदार:
1. गोलू: मोटा, खाने का शौकीन, भोला और मजेदार लड़का।
2. सोनू: दुबला-पतला, होशियार और शरारती लड़का।

कहानी का विषय: गोलू-सोनू और जादुई समोसा।

निर्देश:
- कहानी Motu Patlu जैसी दोस्ताना कॉमेडी वाली हो,
  लेकिन सभी किरदार और कहानी पूरी तरह ओरिजिनल हों।
- 3 से 5 मिनट की कहानी हो।
- हर सीन का अलग विवरण दो।
- गोलू और सोनू के संवाद अलग-अलग लिखो।
- एक महिला Narrator की आवाज के लिए भी लाइनें लिखो।
- मजेदार घटनाएँ, चुटकुले और अंत में बड़ा ट्विस्ट हो।
- हर सीन के लिए 3D Cartoon Image Prompt भी लिखो।
- किरदारों का लुक हर सीन में एक जैसा रहे।
- आसान और शुद्ध हिंदी का उपयोग करो।
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

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    script = result["candidates"][0]["content"]["parts"][0]["text"]

    with open("video_script.txt", "w", encoding="utf-8") as file:
        file.write(script)

    print("Hindi video script created successfully!")

if __name__ == "__main__":
    generate_video_script()
