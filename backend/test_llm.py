import asyncio
import os
import llm

async def test():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip() or "gemini-flash-lite-latest"
    if not api_key:
        print("Set GEMINI_API_KEY in the backend environment to run this test.")
        return

    transcript = [
        {"start": 10.0, "end": 25.0, "text": "This is a great moment in the video where we talk about AI."},
        {"start": 30.0, "end": 50.0, "text": "And here is another amazing insight that could go viral."},
        {"start": 60.0, "end": 80.0, "text": "Finally, we conclude with a funny joke that everyone loves."}
    ]

    try:
        results = await llm.get_clip_suggestions(
            transcript,
            provider='gemini',
            api_key=api_key,
            model=model,
            video_duration=100.0
        )
        print("FINAL RESULTS:")
        for r in results:
            print(f"- {r}")
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(test())
