
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np


class AcousticAnalysisError(ValueError):
    """Raised when acoustic analysis cannot process an audio file."""


@dataclass(frozen=True)
class AcousticAnalysis:
    duration_seconds: float
    sample_rate: int
    channels: int
    rms: float
    peak_amplitude: float
    silence_ratio: float
    clipping_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_acoustics(
    audio_path: Path,
    silence_threshold: float = 0.01,
    window_ms: int = 100,
) -> AcousticAnalysis:
    if not 0 <= silence_threshold <= 1:
        raise AcousticAnalysisError(
            "Silence threshold must be between 0 and 1."
        )

    if window_ms <= 0:
        raise AcousticAnalysisError(
            "Window size must be positive."
        )

    try:
        with wave.open(str(audio_path), "rb") as wav:
            channels = wav.getnchannels()
            sample_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frame_count = wav.getnframes()
            compression = wav.getcomptype()

            if compression != "NONE" or sample_width != 2:
                raise AcousticAnalysisError(
                    "Only uncompressed 16-bit PCM WAV is supported."
                )

            raw_audio = wav.readframes(frame_count)

    except (OSError, EOFError, wave.Error) as exc:
        raise AcousticAnalysisError(
            f"Invalid or unreadable WAV file: {exc}"
        ) from exc

    if sample_rate <= 0 or channels <= 0 or frame_count <= 0:
        raise AcousticAnalysisError("Audio contains no valid frames.")

    samples = np.frombuffer(raw_audio, dtype="<i2")

    if samples.size != frame_count * channels:
        raise AcousticAnalysisError(
            "Audio sample count does not match WAV metadata."
        )

    normalized = samples.astype(np.float64) / 32768.0

    frames = normalized.reshape(-1, channels)

    # Average channels to calculate window-level energy.
    mono = frames.mean(axis=1)

    rms = float(np.sqrt(np.mean(normalized**2)))
    peak = float(np.max(np.abs(normalized)))

    # Each window represents approximately 100 ms by default.
    window_samples = max(1, int(sample_rate * window_ms / 1000))

    silent_windows = 0
    total_windows = 0

    for start in range(0, len(mono), window_samples):
        window = mono[start:start + window_samples]

        window_rms = float(np.sqrt(np.mean(window**2)))

        total_windows += 1
        if window_rms < silence_threshold:
            silent_windows += 1

    silence_ratio = silent_windows / total_windows

    clipping_ratio = float(
        np.mean(np.abs(normalized) >= 0.999)
    )

    return AcousticAnalysis(
        duration_seconds=round(frame_count / sample_rate, 3),
        sample_rate=sample_rate,
        channels=channels,
        rms=round(rms, 6),
        peak_amplitude=round(peak, 6),
        silence_ratio=round(silence_ratio, 6),
        clipping_ratio=round(clipping_ratio, 6),
    )
