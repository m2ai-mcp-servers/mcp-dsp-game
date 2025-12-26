"""Data source router with intelligent fallback."""

import asyncio
import logging
from enum import Enum
from typing import Any, Dict, Optional

from .realtime_stream import RealTimeStream
from .save_parser import SaveFileParser
from ..models.factory_state import FactoryState

logger = logging.getLogger(__name__)


class DataSourceMode(Enum):
    """Current data source mode."""
    REALTIME = "realtime"
    SAVE_FILE = "save_file"
    DISCONNECTED = "disconnected"


class DataSourceRouter:
    """
    Intelligent router between real-time and save file data sources.

    Features:
    - Automatic fallback from real-time to save file when game not running
    - Connection health monitoring
    - Latency-based source selection
    - Graceful degradation
    """

    # Latency threshold for considering real-time "healthy"
    MAX_ACCEPTABLE_LATENCY_MS = 200

    def __init__(
        self,
        realtime_host: str = "localhost",
        realtime_port: int = 8470,
        auto_fallback: bool = True,
    ) -> None:
        """
        Initialize the data source router.

        Args:
            realtime_host: Host for WebSocket connection
            realtime_port: Port for WebSocket connection
            auto_fallback: Automatically fall back to save file when game not running
        """
        self.realtime_stream = RealTimeStream(host=realtime_host, port=realtime_port)
        self.save_parser = SaveFileParser()
        self.auto_fallback = auto_fallback
        self._preferred_mode: Optional[DataSourceMode] = None
        self._last_realtime_attempt: float = 0
        self._realtime_attempt_interval: float = 30.0  # Retry real-time every 30s

    @property
    def current_mode(self) -> DataSourceMode:
        """Get the current data source mode."""
        if self.realtime_stream.is_connected():
            return DataSourceMode.REALTIME
        elif self.save_parser.save_dir is not None:
            return DataSourceMode.SAVE_FILE
        else:
            return DataSourceMode.DISCONNECTED

    @property
    def is_realtime_available(self) -> bool:
        """Check if real-time data is available."""
        return self.realtime_stream.is_connected()

    @property
    def is_save_file_available(self) -> bool:
        """Check if save file data is available."""
        return self.save_parser.save_dir is not None

    def set_preferred_mode(self, mode: DataSourceMode) -> None:
        """
        Set preferred data source mode.

        Args:
            mode: Preferred mode (REALTIME or SAVE_FILE)
        """
        self._preferred_mode = mode
        logger.info(f"Preferred data source mode set to: {mode.value}")

    async def connect_realtime(self) -> bool:
        """
        Attempt to connect to real-time data source.

        Returns:
            True if connection successful
        """
        import time
        self._last_realtime_attempt = time.time()
        return await self.realtime_stream.connect()

    async def get_factory_state(
        self,
        force_mode: Optional[DataSourceMode] = None,
        require_fresh: bool = False,
        max_age_ms: float = 1000,
    ) -> FactoryState:
        """
        Get factory state from the best available source.

        Priority order:
        1. Forced mode (if specified)
        2. Preferred mode (if set and available)
        3. Real-time (if connected and healthy)
        4. Save file (fallback)

        Args:
            force_mode: Force specific data source
            require_fresh: Require fresh real-time data (blocks until fresh)
            max_age_ms: Maximum age for "fresh" data

        Returns:
            FactoryState from the selected source

        Raises:
            ConnectionError: If no data source is available
        """
        import time

        # Determine which mode to use
        mode = force_mode or self._preferred_mode or self._select_best_mode()

        if mode == DataSourceMode.REALTIME:
            try:
                if require_fresh:
                    return await self.realtime_stream.wait_for_fresh_state(
                        max_age_ms=max_age_ms
                    )
                else:
                    return await self.realtime_stream.get_current_state()
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"Real-time data unavailable: {e}")
                if self.auto_fallback and self.is_save_file_available:
                    logger.info("Falling back to save file data")
                    return await self.save_parser.get_latest_state()
                raise

        elif mode == DataSourceMode.SAVE_FILE:
            return await self.save_parser.get_latest_state()

        else:
            # Try to connect to real-time if we haven't tried recently
            if time.time() - self._last_realtime_attempt > self._realtime_attempt_interval:
                if await self.connect_realtime():
                    return await self.realtime_stream.get_current_state()

            # Fall back to save file
            if self.is_save_file_available:
                return await self.save_parser.get_latest_state()

            raise ConnectionError(
                "No data source available. Ensure DSP is running with DysonMCP plugin, "
                "or provide a save file path."
            )

    def _select_best_mode(self) -> DataSourceMode:
        """Select the best available data source mode."""
        # Prefer real-time if connected and healthy
        if self.realtime_stream.is_healthy():
            return DataSourceMode.REALTIME

        # Fall back to real-time if connected (even if not healthy)
        if self.realtime_stream.is_connected():
            return DataSourceMode.REALTIME

        # Use save file if available
        if self.is_save_file_available:
            return DataSourceMode.SAVE_FILE

        return DataSourceMode.DISCONNECTED

    async def get_factory_state_with_source(
        self,
        force_mode: Optional[DataSourceMode] = None,
    ) -> tuple[FactoryState, DataSourceMode]:
        """
        Get factory state along with the source mode used.

        Returns:
            Tuple of (FactoryState, DataSourceMode)
        """
        state = await self.get_factory_state(force_mode=force_mode)
        return state, self.current_mode

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of all data sources.

        Returns:
            Status dictionary with connection info
        """
        return {
            "current_mode": self.current_mode.value,
            "preferred_mode": self._preferred_mode.value if self._preferred_mode else None,
            "auto_fallback": self.auto_fallback,
            "realtime": {
                "available": self.is_realtime_available,
                **self.realtime_stream.get_connection_status(),
            },
            "save_file": {
                "available": self.is_save_file_available,
                "save_dir": str(self.save_parser.save_dir) if self.save_parser.save_dir else None,
                "save_files": len(self.save_parser.list_save_files()),
            },
        }

    async def close(self) -> None:
        """Close all data source connections."""
        await self.realtime_stream.close()

    async def __aenter__(self) -> "DataSourceRouter":
        """Async context manager entry."""
        await self.connect_realtime()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


# Singleton instance for the MCP server
_router: Optional[DataSourceRouter] = None


def get_router() -> DataSourceRouter:
    """Get the singleton data source router."""
    global _router
    if _router is None:
        _router = DataSourceRouter()
    return _router


async def get_factory_state() -> FactoryState:
    """
    Convenience function to get factory state from the best source.

    This is the main entry point for MCP tools.
    """
    return await get_router().get_factory_state()
