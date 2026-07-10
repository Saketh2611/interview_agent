import asyncio
import base64
import json
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.LLM import llm_client
from src.STT import stt_client
from src.TTS import tts_client

router = APIRouter()

STRICT_INTERVIEW_SYSTEM_PROMPT = (
    "You are a strict technical interviewer. Ask exactly one challenging interview question at a time. "
    "Do not give hints, examples, or solutions. Keep each response brief, professional, and direct. "
    "After the candidate answers, evaluate the answer briefly and then ask the next question."
)


async def _generate_audio_payload(text: str) -> Optional[str]:
    if not text:
        return None

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        output_path = tmp_file.name

    try:
        await tts_client.generate_audio_async(text, output_path)
        with open(output_path, "rb") as audio_file:
            encoded = base64.b64encode(audio_file.read()).decode("utf-8")
        return encoded
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


@router.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket, session_id: str | None = None):
    await websocket.accept()
    session = session_id or "default"

    initial_question = await asyncio.to_thread(
        llm_client.chat,
        "Start the interview by asking the first strict question.",
        session_id=session,
        system_prompt=STRICT_INTERVIEW_SYSTEM_PROMPT,
    )
    await websocket.send_json({"type": "assistant", "text": initial_question, "audio": None})

    try:
        while True:
            raw_message = await websocket.receive_text()
            payload = json.loads(raw_message)
            message_type = payload.get("type", "text")

            if message_type == "audio":
                audio_bytes = base64.b64decode(payload.get("data", ""))
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                    tmp_file.write(audio_bytes)
                    temp_path = tmp_file.name

                try:
                    transcript = await asyncio.to_thread(stt_client.transcribe_file, temp_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                user_text = transcript
            else:
                user_text = payload.get("text", "")

            if not user_text:
                continue

            await websocket.send_json({"type": "user_transcript", "text": user_text})

            assistant_reply = await asyncio.to_thread(
                llm_client.chat,
                user_text,
                session_id=session,
                system_prompt=STRICT_INTERVIEW_SYSTEM_PROMPT,
            )
            audio_payload = await _generate_audio_payload(assistant_reply)
            await websocket.send_json({
                "type": "assistant",
                "text": assistant_reply,
                "audio": audio_payload,
            })
    except WebSocketDisconnect:
        await websocket.close()
    except json.JSONDecodeError:
        await websocket.send_json({"type": "error", "text": "Please send valid JSON."})
