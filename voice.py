"""Main voice loop: speak → transcribe → LLM → print response."""

from stt import transcribe
from llm import query


def voice_loop():
    """Run the continuous voice interaction loop."""
    print("Jarvis Voice Mode — say something (Ctrl+C to quit)")
    print("-" * 50)

    while True:
        try:
            text = transcribe()
            if not text:
                print("(no speech detected, try again)")
                continue

            print(f"\nYou: {text}")
            print("Jarvis: ", end="", flush=True)
            query(text, stream=True)
            print()

        except KeyboardInterrupt:
            print("\nExiting voice mode.")
            break


if __name__ == "__main__":
    voice_loop()
