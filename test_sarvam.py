
import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

api_key = os.getenv("SARVAM_API_KEY")

if not api_key:
    print("API key missing. Check your .env file.")
else:
    try:
        client = SarvamAI(
            api_subscription_key=api_key
        )

        response = client.chat.completions(
            model="sarvam-105b",
            messages=[
                {
                    "role": "user",
                    "content": "Introduce yourself briefly."
                }
            ],
            max_tokens=200,
        )

        print(response.choices[0].message.content)

    except Exception as error:
        print("Request failed:", type(error).__name__)
        print(error)
