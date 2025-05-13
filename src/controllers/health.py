from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from langchain_core.language_models import BaseChatModel
from src.services.stt import SpeechToTextCollection
from src.services.tts import TextToSpeechCollection


STATIC_AUDIO_PATH = Path(__file__).parents[2] / "static" / "audio"


class HealthTestAttempt(BaseModel):
    start: datetime
    end: datetime
    duration: timedelta
    result: Any

class HealthOverview(BaseModel):
    total_attempts: int
    test_attempts: List[HealthTestAttempt]
    average_duration: timedelta
    total_duration: timedelta
    description: Optional[str] = None


def health_router(
    model: BaseChatModel,
    stt_coll: SpeechToTextCollection,
    tts_coll: TextToSpeechCollection,
):
    router = APIRouter(prefix="/api/v1/health", tags=["health"])

    @router.get("/test-model")
    async def test_model(total_attempts: int = 3, show_result: bool = True) -> HealthOverview:
        total_attempts = max(min(total_attempts, 5), 1)
        attempts: List[HealthTestAttempt] = []
        total_duration = timedelta(0)

        for _ in range(total_attempts):
            _start_time = datetime.now(timezone.utc)

            try:
                _result = await model.ainvoke("Hi what are you")
            except Exception as e:
                _result = {"error": str(e)}

            _end_time = datetime.now(timezone.utc)
            _duration = _end_time - _start_time
            total_duration += _duration

            attempts.append(
                HealthTestAttempt(
                    start=_start_time,
                    end=_end_time,
                    duration=_duration,
                    result=_result if show_result else f"...[{len(_result)} data]..."
                )
            )

        average_duration = total_duration / total_attempts

        return HealthOverview(
            total_attempts=total_attempts,
            test_attempts=attempts,
            average_duration=average_duration,
            total_duration=total_duration,
            description="Model responsiveness test completed"
        )

    @router.get("/test-stt")
    async def test_stt(total_attempts: int = 3, use_local: bool = True, show_result: bool = True) -> HealthOverview:
        total_attempts = max(min(total_attempts, 5), 1)
        attempts: List[HealthTestAttempt] = []
        total_duration = timedelta(0)

        audio_bytes_data = (STATIC_AUDIO_PATH / "test.wav").read_bytes()
        for _ in range(total_attempts):
            _start_time = datetime.now(timezone.utc)

            try:

                _result = await stt_coll.transcribe_raw_async(
                    audio_bytes_data,
                    force_local=use_local,
                )
            except Exception as e:
                _result = {"error": str(e)}

            _end_time = datetime.now(timezone.utc)
            _duration = _end_time - _start_time
            total_duration += _duration

            attempts.append(
                HealthTestAttempt(
                    start=_start_time,
                    end=_end_time,
                    duration=_duration,
                    result=_result if show_result else f"...[{len(_result)} data]..."
                )
            )

        average_duration = total_duration / total_attempts

        return HealthOverview(
            total_attempts=total_attempts,
            test_attempts=attempts,
            average_duration=average_duration,
            total_duration=total_duration,
            description="Speech to Text responsiveness test completed"
        )

    @router.get("/test-tts")
    async def test_tts(total_attempts: int = 3, use_local: bool = True, show_result: bool = True) -> HealthOverview:
        total_attempts = max(min(total_attempts, 5), 1)
        attempts: List[HealthTestAttempt] = []
        total_duration = timedelta(0)

        for _ in range(total_attempts):
            _start_time = datetime.now(timezone.utc)

            try:
                _result = str(await tts_coll.synthesize_async(
                    text="Halo semuanya, nama saya Andi",
                    force_local=use_local,
                ))
            except Exception as e:
                _result = {"error": str(e)}

            _end_time = datetime.now(timezone.utc)
            _duration = _end_time - _start_time
            total_duration += _duration

            attempts.append(
                HealthTestAttempt(
                    start=_start_time,
                    end=_end_time,
                    duration=_duration,
                    result=_result if show_result else f"...[{len(_result)} data]..."
                )
            )

        average_duration = total_duration / total_attempts

        return HealthOverview(
            total_attempts=total_attempts,
            test_attempts=attempts,
            average_duration=average_duration,
            total_duration=total_duration,
            description="Text to Speech responsiveness test completed"
        )

    return router
