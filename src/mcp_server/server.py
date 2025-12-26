"""Dyson-MCP: MCP server for Dyson Sphere Program factory optimization."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .data_sources.router import DataSourceRouter, DataSourceMode, get_router
from .data_sources.save_parser import SaveFileParser
from .tools.bottleneck_analyzer import BottleneckAnalyzer
from .tools.power_analyzer import PowerAnalyzer
from .tools.logistics_analyzer import LogisticsAnalyzer
from .models.factory_state import FactoryState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Dyson Sphere Program Optimizer")

# Initialize data source router (manages real-time and save file sources)
router = get_router()

# Initialize analyzers
bottleneck_analyzer = BottleneckAnalyzer()
power_analyzer = PowerAnalyzer()
logistics_analyzer = LogisticsAnalyzer()


async def _get_factory_state(
    require_fresh: bool = False,
    force_realtime: bool = False,
) -> tuple[FactoryState, str]:
    """
    Helper to get factory state from best available source.

    Args:
        require_fresh: Require fresh real-time data (blocks until available)
        force_realtime: Force real-time mode (raises if unavailable)

    Returns:
        Tuple of (FactoryState, source_description)
    """
    force_mode = DataSourceMode.REALTIME if force_realtime else None

    try:
        state, mode = await router.get_factory_state_with_source(
            force_mode=force_mode,
            require_fresh=require_fresh,
        )
        source = f"real-time (latency: {router.realtime_stream.latency_ms:.0f}ms)" \
            if mode == DataSourceMode.REALTIME else "save file"
        return state, source
    except Exception as e:
        logger.error(f"Failed to get factory state: {e}")
        raise


@mcp.tool()
async def get_connection_status() -> Dict[str, Any]:
    """
    Get current data source connection status.

    Returns detailed information about:
    - Current data source mode (realtime/save_file/disconnected)
    - WebSocket connection health
    - Available save files
    - Latency metrics
    """
    return router.get_status()


@mcp.tool()
async def connect_to_game(
    host: str = "localhost",
    port: int = 8470,
) -> Dict[str, Any]:
    """
    Attempt to connect to running game with DysonMCP plugin.

    Args:
        host: Game host address (default: localhost)
        port: WebSocket port (default: 8470)

    Returns:
        Connection result with status
    """
    # Update router connection settings
    router.realtime_stream.host = host
    router.realtime_stream.port = port
    router.realtime_stream.uri = f"ws://{host}:{port}"

    success = await router.connect_realtime()

    if success:
        return {
            "status": "connected",
            "message": f"Connected to game at {host}:{port}",
            "latency_ms": router.realtime_stream.latency_ms,
        }
    else:
        return {
            "status": "failed",
            "message": f"Could not connect to game at {host}:{port}. "
                      "Ensure DSP is running with DysonMCP plugin enabled.",
            "fallback": "Save file analysis is still available via load_save_analysis.",
        }


@mcp.tool()
async def analyze_production_bottlenecks(
    planet_id: Optional[int] = None,
    target_item: Optional[str] = None,
    time_window: int = 60,
    include_downstream: bool = True,
    require_realtime: bool = False,
) -> Dict[str, Any]:
    """
    Identify production chain bottlenecks causing throughput limitations.

    Args:
        planet_id: Specific planet to analyze (None = all planets)
        target_item: Focus analysis on specific product (e.g., "green-circuit")
        time_window: Analysis window in seconds for real-time mode
        include_downstream: Trace impact to final products
        require_realtime: Require real-time data (fail if game not connected)

    Returns:
        Bottleneck analysis with root causes and recommendations
    """
    logger.info(f"Analyzing bottlenecks: planet={planet_id}, item={target_item}")

    try:
        factory_state, source = await _get_factory_state(
            force_realtime=require_realtime
        )
        result = await bottleneck_analyzer.analyze(
            factory_state=factory_state,
            planet_id=planet_id,
            target_item=target_item,
            time_window=time_window,
            include_downstream=include_downstream,
        )
        result["data_source"] = source
        return result
    except ConnectionError as e:
        logger.error(f"Data source unavailable: {e}")
        return {
            "error": "data_unavailable",
            "message": str(e),
            "suggestion": "Use connect_to_game to connect, or load_save_analysis for offline analysis.",
        }
    except Exception as e:
        logger.exception("Unexpected error in bottleneck analysis")
        return {"error": "analysis_failed", "message": str(e)}


@mcp.tool()
async def analyze_power_grid(
    planet_id: Optional[int] = None,
    include_accumulator_cycles: bool = True,
    require_realtime: bool = False,
) -> Dict[str, Any]:
    """
    Evaluate power generation, consumption, and distribution efficiency.

    Args:
        planet_id: Specific planet to analyze (None = all planets)
        include_accumulator_cycles: Include charge/discharge pattern analysis
        require_realtime: Require real-time data (fail if game not connected)

    Returns:
        Power grid analysis with deficit warnings and recommendations
    """
    logger.info(f"Analyzing power grid: planet={planet_id}")

    try:
        factory_state, source = await _get_factory_state(
            force_realtime=require_realtime
        )
        result = await power_analyzer.analyze(
            factory_state=factory_state,
            planet_id=planet_id,
            include_accumulator_cycles=include_accumulator_cycles,
        )
        result["data_source"] = source
        return result
    except ConnectionError as e:
        return {
            "error": "data_unavailable",
            "message": str(e),
            "suggestion": "Use connect_to_game to connect, or load_save_analysis for offline analysis.",
        }
    except Exception as e:
        logger.exception("Error in power analysis")
        return {"error": "analysis_failed", "message": str(e)}


@mcp.tool()
async def analyze_logistics_saturation(
    planet_id: Optional[int] = None,
    item_filter: Optional[List[str]] = None,
    saturation_threshold: float = 95.0,
    require_realtime: bool = False,
) -> Dict[str, Any]:
    """
    Detect belt/logistics bottlenecks and flow inefficiencies.

    Args:
        planet_id: Specific planet to analyze
        item_filter: Only analyze belts carrying these items
        saturation_threshold: % of max throughput to flag (default 95%)
        require_realtime: Require real-time data (fail if game not connected)

    Returns:
        Saturated belts and logistics station bottlenecks
    """
    logger.info(f"Analyzing logistics: planet={planet_id}, threshold={saturation_threshold}%")

    try:
        factory_state, source = await _get_factory_state(
            force_realtime=require_realtime
        )
        result = await logistics_analyzer.analyze(
            factory_state=factory_state,
            planet_id=planet_id,
            item_filter=item_filter,
            saturation_threshold=saturation_threshold,
        )
        result["data_source"] = source
        return result
    except ConnectionError as e:
        return {
            "error": "data_unavailable",
            "message": str(e),
            "suggestion": "Use connect_to_game to connect, or load_save_analysis for offline analysis.",
        }
    except Exception as e:
        logger.exception("Error in logistics analysis")
        return {"error": "analysis_failed", "message": str(e)}


@mcp.tool()
async def get_factory_snapshot(
    planet_id: Optional[int] = None,
    item_filter: Optional[List[str]] = None,
    require_realtime: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve current production state for all items.

    Args:
        planet_id: Specific planet (None = all planets)
        item_filter: Only return data for these items
        require_realtime: Require real-time data (fail if game not connected)

    Returns:
        Production, consumption, and storage for each item
    """
    logger.info(f"Getting factory snapshot: planet={planet_id}")

    try:
        factory_state, source = await _get_factory_state(
            force_realtime=require_realtime
        )

        # Filter and format data
        snapshot: Dict[str, Any] = {
            "timestamp": factory_state.timestamp.isoformat(),
            "data_source": source,
            "planets": {},
        }

        for pid, planet in factory_state.planets.items():
            if planet_id is None or pid == planet_id:
                planet_data: Dict[str, Any] = {
                    "planet_name": planet.planet_name,
                    "items": [],
                    "assembler_count": len(planet.assemblers),
                    "belt_count": len(planet.belts),
                }

                for item_name, metrics in planet.production.items():
                    if item_filter is None or item_name in item_filter:
                        planet_data["items"].append({
                            "name": item_name,
                            "production": metrics.production_rate,
                            "consumption": metrics.consumption_rate,
                            "net": metrics.net_rate,
                            "storage": metrics.current_storage,
                        })

                if planet.power:
                    planet_data["power"] = {
                        "generation_mw": planet.power.generation_mw,
                        "consumption_mw": planet.power.consumption_mw,
                        "surplus_mw": planet.power.surplus_mw,
                        "accumulator_charge": planet.power.accumulator_charge_percent,
                    }

                # Include bottleneck indicators
                starved_assemblers = [a for a in planet.assemblers if a.input_starved]
                blocked_assemblers = [a for a in planet.assemblers if a.output_blocked]
                if starved_assemblers or blocked_assemblers:
                    planet_data["bottleneck_indicators"] = {
                        "input_starved_assemblers": len(starved_assemblers),
                        "output_blocked_assemblers": len(blocked_assemblers),
                    }

                snapshot["planets"][pid] = planet_data

        return snapshot
    except ConnectionError as e:
        return {
            "error": "data_unavailable",
            "message": str(e),
            "suggestion": "Use connect_to_game to connect, or load_save_analysis for offline analysis.",
        }
    except Exception as e:
        logger.exception("Error getting factory snapshot")
        return {"error": "snapshot_failed", "message": str(e)}


@mcp.tool()
async def load_save_analysis(
    save_file_path: str,
    analysis_type: str = "full",
) -> Dict[str, Any]:
    """
    Parse .dsv save file and extract factory state for offline analysis.

    Args:
        save_file_path: Path to .dsv save file
        analysis_type: Type of analysis (production|power|logistics|full)

    Returns:
        Comprehensive save state or focused analysis
    """
    logger.info(f"Loading save file: {save_file_path}, type={analysis_type}")

    # Use a dedicated parser for explicit save file loading
    save_parser = SaveFileParser(auto_detect_path=False)

    try:
        factory_state = await save_parser.parse_file(save_file_path)

        result: Dict[str, Any] = {
            "data_source": f"save file: {save_file_path}",
        }

        if analysis_type == "production":
            result["production"] = await bottleneck_analyzer.analyze(factory_state)
        elif analysis_type == "power":
            result["power"] = await power_analyzer.analyze(factory_state)
        elif analysis_type == "logistics":
            result["logistics"] = await logistics_analyzer.analyze(factory_state)
        else:  # full
            result["production"] = await bottleneck_analyzer.analyze(factory_state)
            result["power"] = await power_analyzer.analyze(factory_state)
            result["logistics"] = await logistics_analyzer.analyze(factory_state)

        return result
    except FileNotFoundError as e:
        return {"error": "file_not_found", "message": str(e)}
    except Exception as e:
        logger.exception("Error loading save file")
        return {"error": "parse_failed", "message": str(e)}


@mcp.tool()
async def list_save_files() -> Dict[str, Any]:
    """
    List available save files in the DSP save directory.

    Returns:
        List of save files with metadata (name, size, modified time)
    """
    save_parser = SaveFileParser()
    files = save_parser.list_save_files()

    return {
        "save_directory": str(save_parser.save_dir) if save_parser.save_dir else None,
        "files": files,
        "count": len(files),
    }


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
