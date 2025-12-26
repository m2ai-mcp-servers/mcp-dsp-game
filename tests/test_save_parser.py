"""Tests for SaveFileParser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.data_sources.save_parser import SaveFileParser


class TestSaveFileParser:
    """Tests for SaveFileParser class."""

    def test_init_without_auto_detect(self):
        """Parser initializes without auto-detect."""
        parser = SaveFileParser(auto_detect_path=False)
        assert parser.save_dir is None

    def test_detect_save_directory_not_found(self):
        """Parser handles missing save directory."""
        with patch.object(Path, 'exists', return_value=False):
            parser = SaveFileParser(auto_detect_path=True)
            assert parser.save_dir is None

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self):
        """parse_file raises FileNotFoundError for missing file."""
        parser = SaveFileParser(auto_detect_path=False)

        with pytest.raises(FileNotFoundError):
            await parser.parse_file("/nonexistent/path/save.dsv")

    @pytest.mark.asyncio
    async def test_parse_file_wrong_extension(self, tmp_path):
        """parse_file raises ValueError for non-.dsv files."""
        # Create a temp file with wrong extension
        wrong_file = tmp_path / "save.txt"
        wrong_file.write_text("not a save file")

        parser = SaveFileParser(auto_detect_path=False)

        with pytest.raises(ValueError, match="expected .dsv"):
            await parser.parse_file(str(wrong_file))

    @pytest.mark.asyncio
    async def test_get_latest_state_no_directory(self):
        """get_latest_state raises FileNotFoundError when no save dir."""
        parser = SaveFileParser(auto_detect_path=False)

        with pytest.raises(FileNotFoundError, match="save directory not found"):
            await parser.get_latest_state()

    @pytest.mark.asyncio
    async def test_get_latest_state_no_files(self, tmp_path):
        """get_latest_state raises FileNotFoundError when no save files."""
        parser = SaveFileParser(auto_detect_path=False)
        parser.save_dir = tmp_path

        with pytest.raises(FileNotFoundError, match="No save files found"):
            await parser.get_latest_state()

    def test_list_save_files_no_directory(self):
        """list_save_files returns empty list when no save dir."""
        parser = SaveFileParser(auto_detect_path=False)
        assert parser.list_save_files() == []

    def test_list_save_files_empty_directory(self, tmp_path):
        """list_save_files returns empty list when directory is empty."""
        parser = SaveFileParser(auto_detect_path=False)
        parser.save_dir = tmp_path
        assert parser.list_save_files() == []

    def test_list_save_files_with_files(self, tmp_path):
        """list_save_files returns info about save files."""
        # Create some fake .dsv files
        (tmp_path / "save1.dsv").write_bytes(b"x" * 1000)
        (tmp_path / "save2.dsv").write_bytes(b"x" * 2000)
        (tmp_path / "not_a_save.txt").write_text("ignore me")

        parser = SaveFileParser(auto_detect_path=False)
        parser.save_dir = tmp_path

        files = parser.list_save_files()

        assert len(files) == 2
        assert all(f["name"] in ["save1", "save2"] for f in files)
        assert all("size_mb" in f for f in files)
        assert all("modified" in f for f in files)


class TestSaveFileParserIntegration:
    """Integration tests requiring the dsp_save_parser library."""

    def test_import_game_save(self):
        """GameSave class can be imported from vendor."""
        parser = SaveFileParser(auto_detect_path=False)

        # This should not raise
        game_save_class = parser._get_game_save_class()
        assert game_save_class is not None
        assert hasattr(game_save_class, 'parse')

    @pytest.mark.asyncio
    async def test_parse_minimal_dsv(self, tmp_path):
        """
        Test parsing a minimal .dsv file structure.

        Note: This test requires a valid .dsv file to work properly.
        It's marked as expected to fail without a real save file.
        """
        # Create a minimal fake .dsv file (this won't parse correctly
        # but tests the code path)
        fake_dsv = tmp_path / "test.dsv"
        # DSV files start with "VFSAVE" magic bytes
        fake_dsv.write_bytes(b"VFSAVE" + b"\x00" * 100)

        parser = SaveFileParser(auto_detect_path=False)

        # This will fail because the file isn't a valid DSV
        # but it tests that the parsing path is invoked
        with pytest.raises(Exception):
            await parser.parse_file(str(fake_dsv))
