import asyncio
import json
import redis.asyncio as redis
from pocket_tts import TTSModel
import sounddevice as sd
import numpy as np


#I might want another channel for this, also not sure what module should handle the tts send, maybe hte one that has the list?

class RedisTTSWorker:
    def __init__(self, channel="nina:speech", voice="cosette"):
        self.channel = channel
        # 1. Initialize the heavy model once at startup
        print("Loading TTS Model...")
        self.model = TTSModel.load_model()
        self.voice_state = self.model.get_state_for_audio_prompt(voice)
        print("TTS Model ready.")




    def _play_audio(self, text):
        """Synchronous function to handle generation, normalization, and playback."""
        try:
            # 1. Generate audio
            audio_tensor = self.model.generate_audio(self.voice_state, text)
            audio_data = audio_tensor.numpy()

            # 2. Normalize and Amplify
            # Find the loudest point in the audio (absolute value)
            max_val = np.abs(audio_data).max()
            
            if max_val > 0:
                # Scale the entire array so the peak hits 0.9 (90% volume)
                audio_data = (audio_data / max_val) * 0.9
                
            # 3. Play
            sd.play(audio_data, samplerate=self.model.sample_rate)
            sd.wait() 
        except Exception as e:
            print(f"❌ Audio Playback Error: {e}")





    async def listen(self, r_client):
        """Listens for text on Redis and speaks it."""
        pubsub = r_client.pubsub()
        await pubsub.subscribe(self.channel)
        print(f"TTS Listener active on '{self.channel}'. Waiting for text...")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    raw_payload = message["data"].decode('utf-8')
                    
                    # Try to parse as JSON in case you send complex data
                    try:
                        data = json.loads(raw_payload)
                        text_to_speak = data.get("text", "")
                    except json.JSONDecodeError:
                        # Fallback: if it's not JSON, treat the whole string as text
                        text_to_speak = raw_payload

                    if text_to_speak:
                        print(f"Speaking: {text_to_speak}")
                        # Move the blocking audio code to a separate thread
                        await asyncio.to_thread(self._play_audio, text_to_speak)

                except Exception as e:
                    print(f"❌ Error in TTS loop: {e}")

async def main():
    # Connect to your Redis server
    r_client = redis.Redis(host='localhost', port=6379, db=0)
    worker = RedisTTSWorker()
    await worker.listen(r_client)

if __name__ == "__main__":
    asyncio.run(main())
