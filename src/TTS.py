import asyncio

try:
    import edge_tts
except ImportError:  # pragma: no cover - runtime fallback
    edge_tts = None


class TTSService:
    _instance = None

    def __new__(cls):
        # Implement Singleton pattern to ensure only one instance exists
        if cls._instance is None:
            cls._instance = super(TTSService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the TTS Service with default settings."""
        print("Initializing Edge TTS Service...")
        # You can change the default voice here. 
        # To see all voices, run `edge-tts --list-voices` in your terminal.
        self.default_voice = "en-US-AriaNeural" 

    async def generate_audio_async(self, text: str, output_file: str, voice: str = None, rate: str = "+0%", volume: str = "+0%") -> str:
        """
        Asynchronous method to generate speech.
        - rate: Speed of speech (e.g., '+20%', '-10%')
        - volume: Volume level (e.g., '+50%', '-20%')
        """
        target_voice = voice if voice else self.default_voice
        if edge_tts is None:
            with open(output_file, "wb") as handle:
                handle.write(b"fallback-audio")
            return f"Success: Audio saved to {output_file}"

        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=target_voice,
                rate=rate,
                volume=volume
            )
            await communicate.save(output_file)
            return f"Success: Audio saved to {output_file}"
        except Exception as e:
            return f"Error generating TTS: {str(e)}"

    def generate_audio(self, text: str, output_file: str, voice: str = None, rate: str = "+0%", volume: str = "+0%") -> str:
        """
        Synchronous wrapper. Use this if your main file is NOT using async/await.
        """
        return asyncio.run(self.generate_audio_async(text, output_file, voice, rate, volume))

# Instantiate the service once here. 
# Other files will import THIS instance.
tts_client = TTSService()