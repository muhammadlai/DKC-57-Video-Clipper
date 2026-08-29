import asyncio
import os
import database
import llm

async def main():
    await database.init_db()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"

    if not api_key:
        print("Set GEMINI_API_KEY in the backend environment. Cannot test.")
        return

    print(f"Testing Gemini model: '{model}'")
    
    dummy_transcript = [
        {"start": 0.0, "end": 5.0, "text": "Hello and welcome to this amazing video."},
        {"start": 5.0, "end": 10.0, "text": "Today I am going to show you the craziest trick ever."},
        {"start": 10.0, "end": 20.0, "text": "This secret will absolutely blow your mind, make sure to like and subscribe."},
        {"start": 20.0, "end": 30.0, "text": "Okay, here is the secret. It is just water. Yes, just drink water."},
        {"start": 30.0, "end": 40.0, "text": "That's the entire secret. See you next time, thanks for the views."}
    ]
    
    try:
        suggestions = await llm._call_gemini(
            prompt=llm._build_prompt(dummy_transcript, 40.0),
            api_key=api_key,
            model=model or "gemini-1.5-pro"
        )
        print("SUCCESS! Generated suggestions:")
        for s in suggestions:
            print(f" - [{s['start']}-{s['end']}s] {s['title']} (Score {s['viral_score']})")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
