import os
import json
import urllib.request

API_KEY = os.getenv("GEMINI_API_KEY")

def generate_video_script():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured")

    prompt = """
    हिंदी में एक ओरिजिनल YouTube वीडियो स्क्रिप्ट लिखो।
    विषय: प्रेरणादायक मोटिवेशन और रोचक फैक्ट्स।
    भाषा आसान और आकर्षक हो।
    शुरुआत में दमदार Hook हो।
    अंत में दर्शकों से Subscribe करने को कहो।
    केवल स्क्रिप्ट लिखो।
    """

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-2.5-flash:generateContent?key=" + API_KEY
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

    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))

    script = result["candidates"][0]["content"]["parts"][0]["text"]

    with open("video_script.txt", "w", encoding="utf-8") as file:
        file.write(script)

    print("Hindi video script created successfully!")

if __name__ == "__main__":
    generate_video_script()
