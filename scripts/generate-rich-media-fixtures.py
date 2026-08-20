"""Generate the deterministic PCM audio acceptance fixture."""

import argparse
import math
import struct
import wave
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR.parent / "book" / "media" / "reference-tone.wav"


def generate(path):
    sample_rate = 8_000
    duration_seconds = 1
    frequency = 440
    amplitude = 12_000
    frames = bytearray()
    for index in range(sample_rate * duration_seconds):
        sample = round(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
        frames.extend(struct.pack("<h", sample))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    generate(arguments.output)


if __name__ == "__main__":
    main()
