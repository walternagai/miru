"""Audio transcription module."""

from pathlib import Path


def transcribe_audio(audio_path: str, language: str | None = None) -> str:
    """
    Transcribe audio file to text using OpenAI Whisper.

    Args:
        audio_path: Path to audio file
        language: Optional language code (e.g., "pt", "en")

    Returns:
        Transcribed text

    Raises:
        FileNotFoundError: If audio file does not exist
        ValueError: If transcription fails or library not installed
    """
    path = Path(audio_path)

    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    if not path.is_file():
        raise ValueError(f"Not a file: {audio_path}")

    try:
        import openai
    except ImportError:
        raise ValueError(
            "Audio transcription requires the openai library. "
            "Install with: pip install openai"
        )

    valid_extensions = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(
            f"Unsupported audio format: {path.suffix}. "
            f"Supported formats: {', '.join(valid_extensions)}"
        )

    try:
        with open(path, "rb") as audio_file:
            client = openai.OpenAI()

            if language:
                response = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language=language
                )
            else:
                response = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            return response.text
    except Exception as e:
        raise ValueError(f"Failed to transcribe audio: {e}") from e