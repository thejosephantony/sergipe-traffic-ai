from sergipe_traffic_ai.visual.audio import synth_tone


def test_synth_tone_returns_pcm_bytes():
    tone = synth_tone(
        frequency_hz=440.0,
        duration_s=0.1,
        volume=0.1,
        sample_rate=1_000,
    )

    # 100 frames * 2 bytes (signed 16-bit PCM).
    assert isinstance(tone, bytes)
    assert len(tone) == 200


def test_synth_tone_clamps_volume():
    quiet = synth_tone(440.0, 0.05, volume=0.0, sample_rate=1_000)
    loud = synth_tone(440.0, 0.05, volume=5.0, sample_rate=1_000)

    assert quiet != loud
    assert len(quiet) == len(loud)
