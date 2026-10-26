import argparse
import numpy as np
from pocket_tts import TTSModel
import sounddevice as sd


class LocalTTSWorker:
    def __init__(self, voice="cosette"):
        # 1. Initialize the heavy model once at startup
        print("Loading TTS Model...")
        self.model = TTSModel.load_model()
        self.voice_state = self.model.get_state_for_audio_prompt(voice)
        print("TTS Model ready.")

    def play_audio(self, text):
        """Synchronous function to handle generation, normalization, and playback."""
        try:
            print(f"Speaking: '{text}'")
            # 1. Generate audio
            audio_tensor = self.model.generate_audio(self.voice_state, text)
            audio_data = audio_tensor.numpy()

            # 2. Normalize and Amplify
            max_val = np.abs(audio_data).max()
            if max_val > 0:
                audio_data = (audio_data / max_val) * 0.6
                
            # 3. Play
            sd.play(audio_data, samplerate=self.model.sample_rate)
            sd.wait() 
            print("Playback finished.")
        except Exception as e:
            print(f"❌ Audio Playback Error: {e}")


def main():
    # Set up argument parsing for command line input
    parser = argparse.ArgumentParser(description="Run local text-to-speech.")
    parser.add_argument("text", type=str, help="The text string you want to convert to voice")
    parser.add_argument("--voice", type=str, default="cosette", help="The voice name to use (default: cosette)")
    
    args = parser.parse_args()

    # Initialize worker and play the provided text
    worker = LocalTTSWorker(voice=args.voice)
    worker.play_audio(args.text)


if __name__ == "__main__":
    main()
