"""Audio transcription module using OpenAI Whisper via subprocess."""

import shutil
import subprocess
import tempfile
from pathlib import Path


class WhisperNotInstalledError(Exception):
    """Raised when whisper is not found in PATH."""

    INSTALL_CMD = "pip install openai-whisper"
    FALLBACK_MSG = "Ou transcreva manualmente e use: miru run <model> '<prompt>' --file transcricao.txt"

    def __init__(self) -> None:
        msg = "Whisper não encontrado. Instale com: pip install openai-whisper"
        super().__init__(msg)


class AudioFileNotFoundError(Exception):
    """Raised when audio file is not found."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Arquivo de áudio não encontrado: {path}")


class UnsupportedAudioFormatError(Exception):
    """Raised when audio format is not supported."""

    SUPPORTED = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"]

    def __init__(self, path: str, extension: str) -> None:
        self.path = path
        self.extension = extension
        msg = f"Formato de áudio não suportado: {extension}. "
        msg += f"Suportados: {', '.join(self.SUPPORTED)}"
        super().__init__(msg)


class TranscriptionError(Exception):
    """Raised when transcription fails."""

    def __init__(self, path: str, stderr: str) -> None:
        self.path = path
        self.stderr = stderr
        msg = f"Falha na transcrição de {path}"
        if stderr:
            msg += f": {stderr}"
        super().__init__(msg)


def is_whisper_available() -> bool:
    """
    Check if whisper command is available in PATH.

    Returns:
        True if whisper is found, False otherwise
    """
    return shutil.which("whisper") is not None


def transcribe(path: str | Path) -> str:
    """
    Transcribe audio file using local Whisper via subprocess.

    Args:
        path: Path to audio file

    Returns:
        Transcribed text

    Raises:
        WhisperNotInstalledError: whisper not found in PATH
        AudioFileNotFoundError: file does not exist
        UnsupportedAudioFormatError: format not supported
        TranscriptionError: whisper failed during transcription
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise AudioFileNotFoundError(str(path))

    if not path_obj.is_file():
        raise AudioFileNotFoundError(str(path))

    suffix = path_obj.suffix.lower()
    if suffix not in UnsupportedAudioFormatError.SUPPORTED:
        raise UnsupportedAudioFormatError(str(path), suffix)

    if not is_whisper_available():
        raise WhisperNotInstalledError()

    tmp_dir = None
    try:
        tmp_dir = tempfile.mkdtemp(prefix="miru_whisper_")

        result = subprocess.run(
            ["whisper", str(path_obj), "--output_format", "txt", "--output_dir", tmp_dir],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise TranscriptionError(str(path), result.stderr)

        base_name = path_obj.stem
        txt_file = Path(tmp_dir) / f"{base_name}.txt"

        if not txt_file.exists():
            raise TranscriptionError(str(path), "Output file not created")

        text = txt_file.read_text(encoding="utf-8").strip()
        return text

    except subprocess.TimeoutExpired:
        raise TranscriptionError(str(path), "Timeout (5 minutos)")
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(str(path), str(e)) from e
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)