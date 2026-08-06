import json
import subprocess
from pathlib import Path
from typing import Protocol


class AudioDurationProbe(Protocol):
    def get_duration_seconds(self, audio_path: Path) -> float: ...


class FFprobeAudioDurationProbe:
    def __init__(self, executable: str = "ffprobe") -> None:
        self.executable = executable

    def get_duration_seconds(self, audio_path: Path) -> float:
        command = [
            self.executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(audio_path),
        ]
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            duration = float(json.loads(completed.stdout)["format"]["duration"])
        except (FileNotFoundError, subprocess.CalledProcessError, KeyError, ValueError) as error:
            raise AudioProbeError(f"Could not read audio duration: {audio_path}") from error
        if duration <= 0:
            raise AudioProbeError(f"Audio has invalid duration: {audio_path}")
        return duration


class AudioProbeError(Exception):
    pass
