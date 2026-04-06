"""Multimodal input module for image, file, and audio processing."""

from miru.input.audio import (
    AudioFileNotFoundError,
    TranscriptionError,
    UnsupportedAudioFormatError,
    WhisperNotInstalledError,
    is_whisper_available,
    transcribe,
)
from miru.input.file import (
    FileExtractionError,
    UnsupportedFileTypeError,
    estimate_tokens,
    extract_text,
    format_for_prompt,
)
from miru.input.image import (
    ImageFormatError,
    ImageNotFoundError,
    encode_image,
    encode_images,
)

__all__ = [
    "encode_image",
    "encode_images",
    "ImageNotFoundError",
    "ImageFormatError",
    "extract_text",
    "format_for_prompt",
    "estimate_tokens",
    "FileExtractionError",
    "UnsupportedFileTypeError",
    "transcribe",
    "is_whisper_available",
    "WhisperNotInstalledError",
    "AudioFileNotFoundError",
    "UnsupportedAudioFormatError",
]
