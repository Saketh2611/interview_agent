import os

try:
    from groq import Groq
except ImportError:  # pragma: no cover - runtime fallback
    Groq = None

# Only needed for microphone capture; transcription itself goes through the Groq API
try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - runtime fallback
    sr = None


class STTService:
    _instance = None

    def __new__(cls):
        # Singleton pattern to ensure only one instance of the client exists
        if cls._instance is None:
            cls._instance = super(STTService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the Groq client for Whisper transcription."""
        print("Initializing Speech-to-Text Service (Groq Whisper Turbo)...")
        self.client = None
        self.model = "whisper-large-v3-turbo"

        groq_api_key = os.getenv("GROQ_API_KEY")

        if Groq is not None and groq_api_key:
            try:
                self.client = Groq(api_key=groq_api_key)
            except Exception as exc:
                print(f"STT initialization failed: {exc}")
        elif Groq is None:
            print("groq package is not installed; using fallback transcription.")
        else:
            print("GROQ_API_KEY not set; using fallback transcription.")

        # Recognizer is only used to capture microphone audio into a file-like buffer;
        # actual transcription happens via the Groq API
        self.recognizer = None
        if sr is not None:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.energy_threshold = 400
            except Exception as exc:
                print(f"Microphone recognizer initialization failed: {exc}")

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribes a saved audio file (wav, mp3, m4a, flac, ogg, webm, etc.)
        using Groq's Whisper Large v3 Turbo model.
        """
        if self.client is None:
            return "Fallback transcription: speech recognition is unavailable."

        try:
            ext = os.path.splitext(file_path)[1].lower() or ".wav"
            content_types = {
                ".wav": "audio/wav",
                ".mp3": "audio/mpeg",
                ".m4a": "audio/mp4",
                ".flac": "audio/flac",
                ".ogg": "audio/ogg",
                ".webm": "audio/webm",
            }
            content_type = content_types.get(ext, "audio/wav")
            filename = f"audio{ext}"

            with open(file_path, "rb") as audio_file:
                audio_data = audio_file.read()

            if len(audio_data) < 100:
                return ""

            print(f"Transcribing audio ({len(audio_data)} bytes, {content_type}) via Groq Whisper Turbo...")
            transcription = self.client.audio.transcriptions.create(
                file=(filename, audio_data, content_type),
                model=self.model,
                response_format="text",
            )
            return transcription if isinstance(transcription, str) else transcription.text

        except FileNotFoundError:
            return ""
        except Exception as e:
            print(f"STT error: {e}")
            return ""

    def transcribe_microphone(self, timeout: int = 5, phrase_time_limit: int = 15) -> str:
        """
        Listens to the default microphone, captures the audio, and transcribes it
        using Groq's Whisper Large v3 Turbo model.
        Requires 'pyaudio' to be installed for microphone capture.
        """
        if self.client is None:
            return "Fallback transcription: speech recognition is unavailable."

        if self.recognizer is None:
            return "Error: microphone capture is unavailable (speech_recognition not installed)."

        try:
            with sr.Microphone() as source:
                print("Adjusting for ambient noise... please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                print("Listening... (Speak now)")
                audio_data = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                print("Sending audio to Groq Whisper Turbo...")
                wav_bytes = audio_data.get_wav_data()
                transcription = self.client.audio.transcriptions.create(
                    file=("microphone.wav", wav_bytes),
                    model=self.model,
                    response_format="text",
                )
                return transcription if isinstance(transcription, str) else transcription.text

        except sr.WaitTimeoutError:
            return "Error: Listening timed out while waiting for phrase to start."
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

# Instantiate the service once here.
# Other files will import THIS instance.
stt_client = STTService()