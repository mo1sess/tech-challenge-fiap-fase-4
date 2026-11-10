
from pathlib import Path

from app.core.config import get_settings
from app.modules.audio.azure_speech import transcribe_wav

audio_path = Path("storage/test_audio.wav")

result = transcribe_wav(
    audio_path=audio_path,
    settings=get_settings(),
)

print(result)
