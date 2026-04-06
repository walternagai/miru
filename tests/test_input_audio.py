"""Tests for miru/input/audio.py."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from miru.input.audio import (
    AudioFileNotFoundError,
    TranscriptionError,
    UnsupportedAudioFormatError,
    WhisperNotInstalledError,
    is_whisper_available,
    transcribe,
)


class TestIsWhisperAvailable:
    """Tests for is_whisper_available function."""

    def test_whisper_available(self) -> None:
        """Should return True when whisper is found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/whisper"
            
            result = is_whisper_available()
            
            assert result is True
            mock_which.assert_called_once_with("whisper")

    def test_whisper_not_available(self) -> None:
        """Should return False when whisper is not found."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = None
            
            result = is_whisper_available()
            
            assert result is False


class TestTranscribe:
    """Tests for transcribe function."""

    def test_transcribe_nonexistent_file(self) -> None:
        """Should raise AudioFileNotFoundError for missing file."""
        with pytest.raises(AudioFileNotFoundError) as exc_info:
            transcribe("nonexistent.mp3")
        
        assert "nonexistent.mp3" in str(exc_info.value)

    def test_transcribe_unsupported_format(self, tmp_path: Path) -> None:
        """Should raise UnsupportedAudioFormatError for unsupported format."""
        audio_file = tmp_path / "test.bmp"
        audio_file.write_bytes(b"fake content")

        with pytest.raises(UnsupportedAudioFormatError) as exc_info:
            transcribe(audio_file)

        assert ".bmp" in str(exc_info.value)
        assert ".mp3" in str(exc_info.value)

    def test_transcribe_whisper_not_installed(self, tmp_path: Path) -> None:
        """Should raise WhisperNotInstalledError when whisper not available."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            mock_available.return_value = False

            with pytest.raises(WhisperNotInstalledError) as exc_info:
                transcribe(audio_file)

            assert "Whisper não encontrado" in str(exc_info.value)
            assert hasattr(exc_info.value, "INSTALL_CMD")
            assert hasattr(exc_info.value, "FALLBACK_MSG")

    def test_transcribe_success(self, tmp_path: Path) -> None:
        """Should successfully transcribe audio file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        tmp_dir = tmp_path / "whisper_output"
        tmp_dir.mkdir()

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            with patch("miru.input.audio.subprocess.run") as mock_run:
                with patch("miru.input.audio.tempfile.mkdtemp") as mock_mkdtemp:
                    mock_available.return_value = True
                    mock_run.return_value = MagicMock(returncode=0, stderr="")
                    mock_mkdtemp.return_value = str(tmp_dir)

                    txt_file = tmp_dir / "test.txt"
                    txt_file.write_text("Transcribed text content")

                    result = transcribe(audio_file)

                    assert result == "Transcribed text content"
                    mock_run.assert_called_once()

    def test_transcribe_whisper_failure(self, tmp_path: Path) -> None:
        """Should raise TranscriptionError when whisper fails."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            with patch("miru.input.audio.subprocess.run") as mock_run:
                mock_available.return_value = True
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stderr="Error: Failed to transcribe"
                )

                with pytest.raises(TranscriptionError) as exc_info:
                    transcribe(audio_file)

                assert "Falha na transcrição" in str(exc_info.value)

    def test_transcribe_timeout(self, tmp_path: Path) -> None:
        """Should raise TranscriptionError on timeout."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            with patch("miru.input.audio.subprocess.run") as mock_run:
                import subprocess
                
                mock_available.return_value = True
                mock_run.side_effect = subprocess.TimeoutExpired("whisper", 300)

                with pytest.raises(TranscriptionError) as exc_info:
                    transcribe(audio_file)

                assert "Timeout" in str(exc_info.value)

    def test_transcribe_cleanup_on_exception(self, tmp_path: Path) -> None:
        """Should clean up temp directory even on exception."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio content")

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            with patch("miru.input.audio.subprocess.run") as mock_run:
                with patch("miru.input.audio.shutil.rmtree") as mock_rmtree:
                    mock_available.return_value = True
                    mock_run.return_value = MagicMock(returncode=1, stderr="Error")

                    with patch("miru.input.audio.tempfile.mkdtemp") as mock_mkdtemp:
                        mock_mkdtemp.return_value = "/tmp/fake_whisper_dir"

                        with pytest.raises(TranscriptionError):
                            transcribe(audio_file)

                        mock_rmtree.assert_called_once_with(
                            "/tmp/fake_whisper_dir",
                            ignore_errors=True
                        )


class TestAudioExceptions:
    """Tests for custom exceptions."""

    def test_whisper_not_installed_error(self) -> None:
        """Should create WhisperNotInstalledError with correct attributes."""
        error = WhisperNotInstalledError()

        assert "Whisper não encontrado" in str(error)
        assert error.INSTALL_CMD == "pip install openai-whisper"
        assert "transcreva manualmente" in error.FALLBACK_MSG

    def test_audio_file_not_found_error(self) -> None:
        """Should create AudioFileNotFoundError with correct message."""
        error = AudioFileNotFoundError("test.mp3")

        assert "áudio não encontrado" in str(error).lower()
        assert error.path == "test.mp3"

    def test_unsupported_audio_format_error(self) -> None:
        """Should create UnsupportedAudioFormatError with formats list."""
        error = UnsupportedAudioFormatError("test.bmp", ".bmp")

        assert ".bmp" in str(error)
        assert ".mp3" in str(error)
        assert ".wav" in str(error)
        assert error.SUPPORTED == [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"]

    def test_transcription_error(self) -> None:
        """Should create TranscriptionError with stderr."""
        error = TranscriptionError("test.mp3", "Failed to transcribe")

        assert error.path == "test.mp3"
        assert error.stderr == "Failed to transcribe"
        assert "Falha na transcrição" in str(error)

    def test_transcription_error_no_stderr(self) -> None:
        """Should create TranscriptionError without stderr."""
        error = TranscriptionError("test.mp3", "")

        assert "test.mp3" in str(error)


class TestAudioFormats:
    """Tests for supported audio formats."""

    @pytest.mark.parametrize("ext", [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".mp4"])
    def test_supported_formats(self, tmp_path: Path, ext: str) -> None:
        """Should accept all supported audio formats."""
        audio_file = tmp_path / f"test{ext}"
        audio_file.write_bytes(b"fake audio")

        whisper_tmp = tmp_path / "whisper_output"
        whisper_tmp.mkdir()

        with patch("miru.input.audio.is_whisper_available") as mock_available:
            with patch("miru.input.audio.subprocess.run") as mock_run:
                with patch("miru.input.audio.tempfile.mkdtemp") as mock_mkdtemp:
                    mock_available.return_value = True
                    mock_run.return_value = MagicMock(returncode=0, stderr="")
                    mock_mkdtemp.return_value = str(whisper_tmp)

                    txt_file = whisper_tmp / "test.txt"
                    txt_file.write_text("text")

                    result = transcribe(audio_file)

                    assert result == "text"