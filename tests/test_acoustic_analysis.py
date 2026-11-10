
import wave
from pathlib import Path

import numpy as np
import pytest

from app.modules.audio.acoustic import AcousticAnalysisError, analyze_acoustics


def write_wav(
    destination: Path,
    samples: np.ndarray,
    sample_rate: int = 16000,
) -> Path:
    pcm = (samples * 32767).astype("<i2")

    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())

    return destination


def test_sine_wave_metrics(tmp_path: Path):
    sample_rate = 16000
    duration = 2.0

    timestamps = np.arange(int(sample_rate * duration)) / sample_rate

    samples = 0.5 * np.sin(
        2 * np.pi * 440 * timestamps
    )

    audio_path = write_wav(
        tmp_path / "synthetic_tone.wav",
        samples,
    )

    result = analyze_acoustics(audio_path)

    assert result.duration_seconds == pytest.approx(2.0)
    assert result.sample_rate == 16000
    assert result.channels == 1
    assert result.rms == pytest.approx(0.3535, abs=0.002)
    assert result.peak_amplitude == pytest.approx(0.5, abs=0.002)
    assert result.silence_ratio == pytest.approx(0.0)
    assert result.clipping_ratio == pytest.approx(0.0)


def test_silence_detection(tmp_path: Path):
    sample_rate = 16000

    first_second = np.zeros(sample_rate)

    second_second = 0.5 * np.sin(
        2 * np.pi * 440 *
        np.arange(sample_rate) / sample_rate
    )

    samples = np.concatenate([
        first_second,
        second_second,
    ])

    audio_path = write_wav(
        tmp_path / "synthetic_silence.wav",
        samples,
    )

    result = analyze_acoustics(audio_path)

    assert result.duration_seconds == pytest.approx(2.0)
    assert result.silence_ratio == pytest.approx(0.5)


def test_invalid_audio_raises_error(tmp_path: Path):
    invalid_file = tmp_path / "invalid.wav"
    invalid_file.write_bytes(b"not a wav file")

    with pytest.raises(AcousticAnalysisError):
        analyze_acoustics(invalid_file)
