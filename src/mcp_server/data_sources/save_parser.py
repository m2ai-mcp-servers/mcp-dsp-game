"""Parse DSP .dsv save files for offline analysis."""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

# Add vendor directory to path for dsp_save_parser
_vendor_path = Path(__file__).parent.parent / "vendor"
if str(_vendor_path) not in sys.path:
    sys.path.insert(0, str(_vendor_path))

from ..models.factory_state import FactoryState

logger = logging.getLogger(__name__)


def _import_game_save() -> Any:
    """Lazy import of GameSave to avoid import errors if library unavailable."""
    try:
        from dsp_save_parser import GameSave
        return GameSave
    except ImportError as e:
        logger.error(f"Failed to import dsp_save_parser: {e}")
        raise ImportError(
            "dsp_save_parser not available. "
            "Ensure the vendor/dsp_save_parser directory exists."
        ) from e


class SaveFileParser:
    """Parse DSP .dsv save files for offline analysis."""

    def __init__(self, auto_detect_path: bool = True) -> None:
        self.save_dir: Optional[Path] = None
        self._game_save_class: Optional[Any] = None
        if auto_detect_path:
            self._detect_save_directory()

    def _detect_save_directory(self) -> None:
        """Auto-detect DSP save directory."""
        # Windows: %USERPROFILE%\Documents\Dyson Sphere Program\Save
        # Linux: ~/.config/unity3d/Youthcat Studio/Dyson Sphere Program/Save
        windows_path = Path.home() / "Documents" / "Dyson Sphere Program" / "Save"
        linux_path = (
            Path.home()
            / ".config"
            / "unity3d"
            / "Youthcat Studio"
            / "Dyson Sphere Program"
            / "Save"
        )

        if windows_path.exists():
            self.save_dir = windows_path
            logger.info(f"Found save directory: {windows_path}")
        elif linux_path.exists():
            self.save_dir = linux_path
            logger.info(f"Found save directory: {linux_path}")
        else:
            logger.warning("DSP save directory not found")

    def _get_game_save_class(self) -> Any:
        """Get GameSave class, importing lazily."""
        if self._game_save_class is None:
            self._game_save_class = _import_game_save()
        return self._game_save_class

    async def parse_file(self, file_path: str) -> FactoryState:
        """
        Parse specific .dsv save file.

        Args:
            file_path: Path to the .dsv save file

        Returns:
            FactoryState with extracted factory data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a .dsv file
            Exception: If parsing fails
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Save file not found: {file_path}")

        if not path.suffix.lower() == ".dsv":
            raise ValueError(f"Invalid file type: {path.suffix} (expected .dsv)")

        logger.info(f"Parsing save file: {path.name} ({path.stat().st_size / 1024 / 1024:.2f} MB)")

        try:
            GameSave = self._get_game_save_class()

            # Parse the save file
            with open(path, 'rb') as f:
                game_save = GameSave.parse(f)

            logger.info(f"Save parsed successfully. Game version: "
                       f"{game_save.majorGameVersion}.{game_save.minorGameVersion}."
                       f"{game_save.releaseGameVersion}")

            # Transform to FactoryState
            factory_state = FactoryState.from_save_data(game_save)

            logger.info(f"Extracted {len(factory_state.planets)} planets")
            return factory_state

        except ImportError:
            raise
        except Exception as e:
            logger.error(f"Failed to parse save file: {e}")
            raise RuntimeError(f"Save file parsing failed: {e}") from e

    async def get_latest_state(self) -> FactoryState:
        """
        Parse most recent save file in save directory.

        Returns:
            FactoryState from the most recently modified save file

        Raises:
            FileNotFoundError: If save directory or files not found
        """
        if not self.save_dir or not self.save_dir.exists():
            raise FileNotFoundError("DSP save directory not found")

        # Find most recent .dsv file
        save_files = list(self.save_dir.glob("*.dsv"))
        if not save_files:
            raise FileNotFoundError("No save files found")

        latest_save = max(save_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Loading latest save: {latest_save.name}")
        return await self.parse_file(str(latest_save))

    def list_save_files(self) -> list[dict[str, Any]]:
        """
        List all available save files.

        Returns:
            List of save file info dicts with name, path, size, modified time
        """
        if not self.save_dir or not self.save_dir.exists():
            return []

        save_files = []
        for path in self.save_dir.glob("*.dsv"):
            stat = path.stat()
            save_files.append({
                "name": path.stem,
                "path": str(path),
                "size_mb": round(stat.st_size / 1024 / 1024, 2),
                "modified": stat.st_mtime,
            })

        # Sort by modification time, newest first
        save_files.sort(key=lambda x: x["modified"], reverse=True)
        return save_files
