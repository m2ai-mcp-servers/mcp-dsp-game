"""WebSocket client for real-time game data streaming."""

import asyncio
import json
import logging
import time
from typing import Callable, Optional

from ..models.factory_state import FactoryState

logger = logging.getLogger(__name__)


class RealTimeStream:
    """
    WebSocket client for real-time game data streaming.

    Features:
    - Automatic reconnection with exponential backoff
    - Connection health monitoring
    - Latency tracking
    - Graceful degradation
    """

    # Reconnection settings
    INITIAL_RECONNECT_DELAY = 1.0  # seconds
    MAX_RECONNECT_DELAY = 30.0  # seconds
    RECONNECT_BACKOFF_FACTOR = 2.0
    MAX_RECONNECT_ATTEMPTS = 10
    PING_INTERVAL = 10.0  # seconds
    PING_TIMEOUT = 5.0  # seconds

    def __init__(self, host: str = "localhost", port: int = 8470) -> None:
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.websocket: Optional[object] = None
        self.latest_state: Optional[FactoryState] = None
        self._receive_task: Optional[asyncio.Task[None]] = None
        self._reconnect_task: Optional[asyncio.Task[None]] = None
        self._connected = False
        self._should_reconnect = True
        self._reconnect_attempts = 0
        self._current_reconnect_delay = self.INITIAL_RECONNECT_DELAY
        self._last_message_time: float = 0
        self._last_latency_ms: float = 0
        self._on_state_update: Optional[Callable[[FactoryState], None]] = None
        self._connection_lock = asyncio.Lock()

    @property
    def latency_ms(self) -> float:
        """Get estimated latency in milliseconds."""
        return self._last_latency_ms

    @property
    def last_update_age_ms(self) -> float:
        """Get milliseconds since last update."""
        if self._last_message_time == 0:
            return float('inf')
        return (time.time() - self._last_message_time) * 1000

    def set_state_callback(self, callback: Callable[[FactoryState], None]) -> None:
        """Set callback to be called on each state update."""
        self._on_state_update = callback

    async def connect(self) -> bool:
        """
        Establish WebSocket connection to game plugin.

        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self._connected:
                return True

            try:
                import websockets

                logger.info(f"Connecting to game at {self.uri}...")
                connect_start = time.time()

                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.uri,
                        ping_interval=self.PING_INTERVAL,
                        ping_timeout=self.PING_TIMEOUT,
                        close_timeout=5.0,
                    ),
                    timeout=10.0
                )

                connect_time = (time.time() - connect_start) * 1000
                logger.info(f"Connected to game at {self.uri} ({connect_time:.0f}ms)")

                self._connected = True
                self._reconnect_attempts = 0
                self._current_reconnect_delay = self.INITIAL_RECONNECT_DELAY

                # Start receive loop
                self._receive_task = asyncio.create_task(self._receive_loop())

                return True

            except asyncio.TimeoutError:
                logger.warning(f"Connection timeout to {self.uri}")
                self._connected = False
                return False
            except Exception as e:
                logger.warning(f"Could not connect to game: {e}")
                self._connected = False
                return False

    async def _receive_loop(self) -> None:
        """Continuously receive and process game data."""
        try:
            import websockets

            async for message in self.websocket:  # type: ignore
                receive_time = time.time()

                try:
                    data = json.loads(message)

                    # Calculate approximate latency from game timestamp
                    if "timestamp" in data:
                        game_timestamp = data["timestamp"]
                        self._last_latency_ms = (receive_time - game_timestamp) * 1000

                    # Parse into FactoryState
                    self.latest_state = FactoryState.from_realtime_data(data)
                    self._last_message_time = receive_time

                    # Notify callback if set
                    if self._on_state_update:
                        try:
                            self._on_state_update(self.latest_state)
                        except Exception as e:
                            logger.warning(f"State callback error: {e}")

                    logger.debug(f"Received state update: {len(message)} bytes, "
                               f"latency: {self._last_latency_ms:.0f}ms")

                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in message: {e}")

        except asyncio.CancelledError:
            logger.debug("Receive loop cancelled")
        except Exception as e:
            logger.info(f"WebSocket connection closed: {e}")
        finally:
            self._connected = False

            # Schedule reconnection if enabled
            if self._should_reconnect:
                asyncio.create_task(self._schedule_reconnect())

    async def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt with exponential backoff."""
        if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
            logger.warning(f"Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) reached")
            return

        self._reconnect_attempts += 1
        delay = min(self._current_reconnect_delay, self.MAX_RECONNECT_DELAY)

        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts}/"
                   f"{self.MAX_RECONNECT_ATTEMPTS})")

        await asyncio.sleep(delay)
        self._current_reconnect_delay *= self.RECONNECT_BACKOFF_FACTOR

        if self._should_reconnect and not self._connected:
            success = await self.connect()
            if not success and self._should_reconnect:
                await self._schedule_reconnect()

    def is_connected(self) -> bool:
        """Check if WebSocket connection is active and receiving data."""
        if not self._connected:
            return False

        # Consider stale if no data in last 5 seconds
        if self.last_update_age_ms > 5000:
            return False

        return True

    def is_healthy(self) -> bool:
        """Check if connection is healthy (connected with recent data and low latency)."""
        return (
            self.is_connected() and
            self.last_update_age_ms < 2000 and  # Fresh data (< 2s old)
            self._last_latency_ms < 500  # Low latency (< 500ms)
        )

    async def get_current_state(self, timeout: float = 5.0) -> FactoryState:
        """
        Get most recent factory state from stream.

        Args:
            timeout: Maximum seconds to wait for data

        Returns:
            Current FactoryState

        Raises:
            ConnectionError: If cannot connect to game
            TimeoutError: If no data received within timeout
        """
        # Attempt connection if not connected
        if not self._connected:
            if not await self.connect():
                raise ConnectionError(f"Cannot connect to game at {self.uri}")

        # Wait for at least one state update
        elapsed = 0.0
        poll_interval = 0.1

        while self.latest_state is None and elapsed < timeout:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        if self.latest_state is None:
            raise TimeoutError(f"No data received from game within {timeout}s")

        return self.latest_state

    async def wait_for_fresh_state(self, max_age_ms: float = 1000, timeout: float = 5.0) -> FactoryState:
        """
        Wait for a fresh state update (useful for real-time analysis).

        Args:
            max_age_ms: Maximum acceptable age of data in milliseconds
            timeout: Maximum seconds to wait

        Returns:
            FactoryState with data newer than max_age_ms
        """
        if not self._connected:
            if not await self.connect():
                raise ConnectionError(f"Cannot connect to game at {self.uri}")

        elapsed = 0.0
        poll_interval = 0.05  # 50ms polling for fresh data

        while elapsed < timeout:
            if self.latest_state and self.last_update_age_ms < max_age_ms:
                return self.latest_state
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"No fresh data (< {max_age_ms}ms old) within {timeout}s")

    def get_connection_status(self) -> dict:
        """Get detailed connection status for diagnostics."""
        return {
            "connected": self._connected,
            "healthy": self.is_healthy(),
            "uri": self.uri,
            "latency_ms": self._last_latency_ms if self._connected else None,
            "last_update_age_ms": self.last_update_age_ms if self._last_message_time > 0 else None,
            "reconnect_attempts": self._reconnect_attempts,
            "has_data": self.latest_state is not None,
        }

    async def close(self) -> None:
        """Close WebSocket connection and stop reconnection."""
        self._should_reconnect = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            try:
                await self.websocket.close()  # type: ignore
            except Exception:
                pass

        self._connected = False
        logger.info("WebSocket connection closed")

    async def __aenter__(self) -> "RealTimeStream":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
