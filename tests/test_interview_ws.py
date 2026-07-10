from fastapi.testclient import TestClient

from main import app
from src import interview_router


class DummyLLM:
    def __init__(self):
        self.calls = []

    def chat(self, prompt, session_id="default", system_prompt=None):
        self.calls.append((prompt, session_id, system_prompt))
        return "Please tell me about your experience."


class DummyTTS:
    async def generate_audio_async(self, text, output_file, voice=None, rate="+0%", volume="+0%"):
        with open(output_file, "wb") as fh:
            fh.write(b"fake-audio")
        return f"Success: Audio saved to {output_file}"


class DummySTT:
    def transcribe_file(self, file_path):
        return "I have five years of experience."


def test_interview_websocket_starts_with_a_question(monkeypatch):
    monkeypatch.setattr(interview_router, "llm_client", DummyLLM())
    monkeypatch.setattr(interview_router, "tts_client", DummyTTS())
    monkeypatch.setattr(interview_router, "stt_client", DummySTT())

    with TestClient(app) as client:
        with client.websocket_connect("/ws/interview") as websocket:
            message = websocket.receive_json()
            assert message["type"] == "assistant"
            assert "experience" in message["text"].lower()
