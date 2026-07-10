try:
    import speech_recognition as sr
except ImportError:  # pragma: no cover - runtime fallback
    sr = None


class STTService:
    _instance = None

    def __new__(cls):
        # Singleton pattern to ensure only one instance of the recognizer exists
        if cls._instance is None:
            cls._instance = super(STTService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initializes the Speech Recognizer with default settings."""
        print("Initializing Speech-to-Text Service...")
        self.recognizer = None
        if sr is not None:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.energy_threshold = 400
            except Exception as exc:
                print(f"STT initialization failed: {exc}")
        else:
            print("speech_recognition is not available; using fallback transcription.")

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribes a saved audio file (WAV, AIFF, or FLAC).
        """
        if self.recognizer is None:
            return "Fallback transcription: speech recognition is unavailable."

        try:
            with sr.AudioFile(file_path) as source:
                print(f"Reading audio from {file_path}...")
                audio_data = self.recognizer.record(source)

                # Using the free Google Web Speech API (requires internet)
                # To go completely offline, you can change this to: self.recognizer.recognize_whisper(audio_data)
                text = self.recognizer.recognize_google(audio_data)
                return text

        except sr.UnknownValueError:
            return "Error: Speech was unintelligible."
        except sr.RequestError as e:
            return f"Error: Could not request results; {e}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

    def transcribe_microphone(self, timeout: int = 5, phrase_time_limit: int = 15) -> str:
        """
        Listens to the default microphone and transcribes the speech.
        Requires 'pyaudio' to be installed.
        """
        if self.recognizer is None:
            return "Fallback transcription: speech recognition is unavailable."

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

                print("Processing speech...")
                text = self.recognizer.recognize_google(audio_data)
                return text

        except sr.WaitTimeoutError:
            return "Error: Listening timed out while waiting for phrase to start."
        except sr.UnknownValueError:
            return "Error: Speech was unintelligible."
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

# Instantiate the service once here.
# Other files will import THIS instance.
stt_client = STTService()