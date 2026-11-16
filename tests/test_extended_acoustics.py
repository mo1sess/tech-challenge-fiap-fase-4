import wave
import numpy as np
import pytest
from app.modules.audio.acoustic import analyze_acoustics


def test_pause_energy_deterministic(tmp_path):
    path = tmp_path / "synthetic.wav"
    # 200 ms de tom, 300 ms de silêncio, 200 ms de tom, 100 ms de silêncio.
    tone = (.4 * np.sin(2 * np.pi * 200 * np.arange(3200) / 16000) * 32767).astype('<i2')
    samples = np.concatenate([tone, np.zeros(4800, dtype='<i2'), tone, np.zeros(1600, dtype='<i2')])
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
        wav.writeframes(samples.tobytes())
    result = analyze_acoustics(path).to_dict()
    assert result['pause_count'] == 2
    assert result['longest_pause_seconds'] == pytest.approx(.3)
    assert len(result['window_energy']) == 8
    assert result['intensity_std'] > 0
    assert result['silence_ratio'] == .5
