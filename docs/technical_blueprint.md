# Technical Blueprint: Dyson Sphere Program MCP Integration

## System Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Layer 3: AI Client (Claude)                          │
│  Natural Language Queries → MCP Protocol → Structured Responses         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
                           MCP Protocol (stdio/SSE)
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                 Layer 2: MCP Server (Python/FastMCP)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │  Data Sources    │  │  Analysis Engine │  │  Optimization      │   │
│  ├──────────────────┤  ├──────────────────┤  ├────────────────────┤   │
│  │ RealTimeStream   │  │ Bottleneck       │  │ Blueprint Generator│   │
│  │ SaveFileParser   │  │ Power Analyzer   │  │ Recipe Optimizer   │   │
│  │ DataSourceRouter │  │ Logistics        │  │ Dependency Graph   │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MCP Tools (FastMCP)                          │   │
│  │  - analyze_production_bottlenecks                               │   │
│  │  - analyze_power_grid                                           │   │
│  │  - analyze_logistics_saturation                                 │   │
│  │  - generate_optimized_blueprint                                 │   │
│  │  - get_factory_snapshot                                         │   │
│  │  - load_save_analysis                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
         ↑ WebSocket (ws://localhost:8470)      ↑ File I/O
         │                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│            Layer 1: Game Instrumentation (C# BepInEx Plugin)            │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │ Harmony Patches  │  │ Data Collectors  │  │  Export Layer      │   │
│  ├──────────────────┤  ├──────────────────┤  ├────────────────────┤   │
│  │ GameData         │  │ ProductionMetrics│  │ WebSocketServer    │   │
│  │ PlanetFactory    │  │ PowerMonitor     │  │ JSONSerializer     │   │
│  │ PowerSystem      │  │ BeltThroughput   │  │ ConfigManager      │   │
│  │ CargoTraffic     │  │ LogisticsTracker │  │                    │   │
│  └──────────────────┘  └──────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
         ↑ Harmony IL Patching (Runtime)
         │
┌─────────────────────────────────────────────────────────────────────────┐
│                 Layer 0: Dyson Sphere Program (Unity)                   │
│  Game Loop → Factory Updates → Production Calculations                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Real-Time Analysis Flow

```
┌─────────┐
│  Claude │  "What's bottlenecking my green circuits?"
└────┬────┘
     │ MCP Request: analyze_production_bottlenecks(targetItem="green-circuit")
     ↓
┌──────────────────┐
│   MCP Server     │
│  ├─ Parse params │
│  ├─ Route to     │
│  │  RealTimeData │
│  └─ Execute      │
│     analyzer     │
└────┬─────────────┘
     │ WebSocket: getCurrentState()
     ↓
┌──────────────────┐
│  BepInEx Plugin  │
│  ├─ Query cached │
│  │  metrics      │
│  ├─ Serialize to │
│  │  JSON         │
│  └─ Send via WS  │
└────┬─────────────┘
     │ JSON: {production: {...}, power: {...}, belts: {...}}
     ↓
┌──────────────────┐
│  MCP Server      │
│  ├─ Deserialize  │
│  ├─ Build model  │
│  ├─ Run analysis │
│  └─ Format result│
└────┬─────────────┘
     │ MCP Response: {bottlenecks: [...], criticalPath: [...]}
     ↓
┌─────────┐
│  Claude │  "Green circuits limited by copper plate input at 420/min shortage"
└─────────┘
```

### Offline Analysis Flow

```
┌─────────┐
│  Claude │  "Analyze my save file for power issues"
└────┬────┘
     │ MCP Request: load_save_analysis(saveFilePath="...", analysisType="power")
     ↓
┌──────────────────┐
│   MCP Server     │
│  ├─ Validate path│
│  ├─ Route to     │
│  │  SaveParser  │
│  └─ Load .dsv    │
└────┬─────────────┘
     │ File I/O: read binary .dsv
     ↓
┌──────────────────┐
│  qhgz2013 Parser │
│  ├─ Binary decode│
│  ├─ Extract      │
│  │  structures   │
│  └─ Return dict  │
└────┬─────────────┘
     │ Python dict: {planets: [...], factories: [...], power: [...]}
     ↓
┌──────────────────┐
│  MCP Server      │
│  ├─ Transform to │
│  │  FactoryState │
│  ├─ Run power    │
│  │  analyzer     │
│  └─ Format result│
└────┬─────────────┘
     │ MCP Response: {totalGeneration: X, deficit: Y, recommendations: [...]}
     ↓
┌─────────┐
│  Claude │  "Power deficit of 420MW during peak, add 3 more fusion plants"
└─────────┘
```

## Component Specifications

### 1. BepInEx Plugin (C#)

#### 1.1 Plugin Entry Point

**File**: `src/bepinex_plugin/Plugin.cs`

```csharp
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
public class DysonMCPPlugin : BaseUnityPlugin
{
    public const string PluginGuid = "com.memyselfai.dysonmcp";
    public const string PluginName = "DysonMCP";
    public const string PluginVersion = "1.0.0";
    
    private static Harmony _harmony;
    private static WebSocketServer _wsServer;
    private static MetricsCollector _collector;
    
    // Configuration
    public static ConfigEntry<int> WebSocketPort;
    public static ConfigEntry<int> MetricsUpdateFrequency;
    public static ConfigEntry<bool> EnableRealTimeStreaming;
    
    void Awake()
    {
        // Load configuration
        WebSocketPort = Config.Bind("Network", "Port", 8470, 
            "WebSocket server port for MCP communication");
        MetricsUpdateFrequency = Config.Bind("Performance", "UpdateFrequency", 1, 
            "Metrics collection frequency in Hz (1-60)");
        EnableRealTimeStreaming = Config.Bind("Features", "RealTimeStreaming", true, 
            "Enable real-time metric streaming");
        
        // Initialize Harmony patches
        _harmony = new Harmony(PluginGuid);
        _harmony.PatchAll();
        
        // Initialize WebSocket server
        if (EnableRealTimeStreaming.Value)
        {
            _wsServer = new WebSocketServer(WebSocketPort.Value);
            _wsServer.Start();
        }
        
        // Initialize metrics collector
        _collector = new MetricsCollector(MetricsUpdateFrequency.Value);
        
        Logger.LogInfo($"{PluginName} {PluginVersion} loaded successfully");
    }
    
    void OnDestroy()
    {
        _wsServer?.Stop();
        _harmony?.UnpatchSelf();
    }
    
    void Update()
    {
        // Collect metrics at configured frequency
        if (Time.frameCount % (60 / MetricsUpdateFrequency.Value) == 0)
        {
            _collector.CollectMetrics();
            if (_wsServer != null && _wsServer.HasClients)
            {
                _wsServer.BroadcastMetrics(_collector.GetCurrentMetrics());
            }
        }
    }
}
```

#### 1.2 Harmony Patches

**File**: `src/bepinex_plugin/Patches/ProductionPatch.cs`

```csharp
using HarmonyLib;

[HarmonyPatch(typeof(AssemblerComponent))]
public class ProductionPatch
{
    // Track production rate per assembler
    [HarmonyPostfix]
    [HarmonyPatch("InternalUpdate")]
    public static void InternalUpdate_Postfix(
        ref AssemblerComponent __instance,
        PlanetFactory factory,
        int timeGene,
        float power)
    {
        if (__instance.recipeId > 0 && power > 0.1f)
        {
            // Calculate actual production rate
            int produced = __instance.produced[__instance.productCursor];
            if (produced > 0)
            {
                MetricsCollector.RecordProduction(
                    factory.planetId,
                    __instance.recipeId,
                    __instance.id,
                    produced,
                    timeGene
                );
            }
        }
    }
}

[HarmonyPatch(typeof(PowerSystem))]
public class PowerPatch
{
    [HarmonyPostfix]
    [HarmonyPatch("GameTick")]
    public static void GameTick_Postfix(
        ref PowerSystem __instance,
        long time)
    {
        // Track power generation and consumption
        long totalGen = 0;
        long totalCon = 0;
        
        for (int i = 1; i < __instance.genCursor; i++)
        {
            totalGen += __instance.nodePool[__instance.genPool[i]].workEnergyPerTick;
        }
        
        for (int i = 1; i < __instance.consumerCursor; i++)
        {
            totalCon += __instance.nodePool[__instance.consumerPool[i]].workEnergyPerTick;
        }
        
        MetricsCollector.RecordPower(
            __instance.planet.id,
            totalGen,
            totalCon,
            time
        );
    }
}

[HarmonyPatch(typeof(CargoPath))]
public class LogisticsPatch
{
    [HarmonyPostfix]
    [HarmonyPatch("Update")]
    public static void Update_Postfix(
        ref CargoPath __instance,
        int timeGene)
    {
        // Track belt throughput
        if (__instance.bufferLength > 0)
        {
            int throughput = __instance.buffer[0].item; // Items passing through
            
            MetricsCollector.RecordBeltThroughput(
                __instance.id,
                throughput,
                __instance.bufferLength,
                timeGene
            );
        }
    }
}
```

#### 1.3 WebSocket Server

**File**: `src/bepinex_plugin/WebSocketServer.cs`

```csharp
using System;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class WebSocketServer
{
    private HttpListener _listener;
    private CancellationTokenSource _cts;
    private List<WebSocket> _clients = new List<WebSocket>();
    
    public bool HasClients => _clients.Count > 0;
    
    public WebSocketServer(int port)
    {
        _listener = new HttpListener();
        _listener.Prefixes.Add($"http://localhost:{port}/");
    }
    
    public void Start()
    {
        _cts = new CancellationTokenSource();
        _listener.Start();
        Task.Run(() => AcceptClients(_cts.Token));
    }
    
    public void Stop()
    {
        _cts?.Cancel();
        _listener?.Stop();
        foreach (var client in _clients)
        {
            client?.Dispose();
        }
        _clients.Clear();
    }
    
    private async Task AcceptClients(CancellationToken token)
    {
        while (!token.IsCancellationRequested)
        {
            try
            {
                HttpListenerContext context = await _listener.GetContextAsync();
                if (context.Request.IsWebSocketRequest)
                {
                    HttpListenerWebSocketContext wsContext = 
                        await context.AcceptWebSocketAsync(null);
                    _clients.Add(wsContext.WebSocket);
                }
            }
            catch (Exception ex)
            {
                DysonMCPPlugin.Logger.LogError($"WebSocket accept error: {ex.Message}");
            }
        }
    }
    
    public void BroadcastMetrics(MetricsSnapshot metrics)
    {
        string json = JsonConvert.SerializeObject(metrics);
        byte[] buffer = Encoding.UTF8.GetBytes(json);
        
        foreach (var client in _clients.ToArray())
        {
            try
            {
                if (client.State == WebSocketState.Open)
                {
                    client.SendAsync(
                        new ArraySegment<byte>(buffer),
                        WebSocketMessageType.Text,
                        true,
                        CancellationToken.None
                    ).Wait();
                }
                else
                {
                    _clients.Remove(client);
                    client.Dispose();
                }
            }
            catch (Exception ex)
            {
                DysonMCPPlugin.Logger.LogError($"Broadcast error: {ex.Message}");
                _clients.Remove(client);
            }
        }
    }
}
```

#### 1.4 Data Models

**File**: `src/bepinex_plugin/DataCollectors/MetricsSnapshot.cs`

```csharp
using System.Collections.Generic;

public class MetricsSnapshot
{
    public long Timestamp { get; set; }
    public Dictionary<int, PlanetMetrics> Planets { get; set; }
}

public class PlanetMetrics
{
    public int PlanetId { get; set; }
    public PowerMetrics Power { get; set; }
    public List<ProductionMetric> Production { get; set; }
    public List<BeltMetric> Belts { get; set; }
}

public class PowerMetrics
{
    public long Generation { get; set; }      // Energy per tick
    public long Consumption { get; set; }     // Energy per tick
    public long Surplus => Generation - Consumption;
    public double SurplusMW => Surplus / 16666.67; // Convert to MW
}

public class ProductionMetric
{
    public int RecipeId { get; set; }
    public int AssemblerId { get; set; }
    public int ItemsProduced { get; set; }
    public double ProductionRate { get; set; } // Items per minute
    public bool InputStarved { get; set; }
    public bool OutputBlocked { get; set; }
}

public class BeltMetric
{
    public int BeltId { get; set; }
    public int ItemType { get; set; }
    public int Throughput { get; set; }        // Items per second
    public int MaxThroughput { get; set; }     // Based on belt tier
    public double SaturationPercent => (Throughput / (double)MaxThroughput) * 100;
}
```

### 2. MCP Server (Python)

#### 2.1 Server Entry Point

**File**: `src/mcp_server/server.py`

```python
from fastmcp import FastMCP
from typing import Optional, List, Dict, Any
import asyncio
import logging

from .data_sources.realtime_stream import RealTimeStream
from .data_sources.save_parser import SaveFileParser
from .tools.bottleneck_analyzer import BottleneckAnalyzer
from .tools.power_analyzer import PowerAnalyzer
from .tools.logistics_analyzer import LogisticsAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Dyson Sphere Program Optimizer")

# Initialize data sources
realtime_stream = RealTimeStream(host="localhost", port=8470)
save_parser = SaveFileParser()

# Initialize analyzers
bottleneck_analyzer = BottleneckAnalyzer()
power_analyzer = PowerAnalyzer()
logistics_analyzer = LogisticsAnalyzer()

@mcp.tool()
async def analyze_production_bottlenecks(
    planet_id: Optional[int] = None,
    target_item: Optional[str] = None,
    time_window: int = 60,
    include_downstream: bool = True
) -> Dict[str, Any]:
    """
    Identify production chain bottlenecks causing throughput limitations.
    
    Args:
        planet_id: Specific planet to analyze (None = all planets)
        target_item: Focus analysis on specific product (e.g., "green-circuit")
        time_window: Analysis window in seconds for real-time mode
        include_downstream: Trace impact to final products
    
    Returns:
        Bottleneck analysis with root causes and recommendations
    """
    logger.info(f"Analyzing bottlenecks: planet={planet_id}, item={target_item}")
    
    # Get factory state from available data source
    if realtime_stream.is_connected():
        factory_state = await realtime_stream.get_current_state()
        logger.info("Using real-time game data")
    else:
        factory_state = await save_parser.get_latest_state()
        logger.info("Using save file data (game not running)")
    
    # Run bottleneck analysis
    result = await bottleneck_analyzer.analyze(
        factory_state=factory_state,
        planet_id=planet_id,
        target_item=target_item,
        time_window=time_window,
        include_downstream=include_downstream
    )
    
    return result

@mcp.tool()
async def analyze_power_grid(
    planet_id: Optional[int] = None,
    include_accumulator_cycles: bool = True
) -> Dict[str, Any]:
    """
    Evaluate power generation, consumption, and distribution efficiency.
    
    Args:
        planet_id: Specific planet to analyze (None = all planets)
        include_accumulator_cycles: Include charge/discharge pattern analysis
    
    Returns:
        Power grid analysis with deficit warnings and recommendations
    """
    logger.info(f"Analyzing power grid: planet={planet_id}")
    
    factory_state = await _get_factory_state()
    
    result = await power_analyzer.analyze(
        factory_state=factory_state,
        planet_id=planet_id,
        include_accumulator_cycles=include_accumulator_cycles
    )
    
    return result

@mcp.tool()
async def analyze_logistics_saturation(
    planet_id: Optional[int] = None,
    item_filter: Optional[List[str]] = None,
    saturation_threshold: float = 95.0
) -> Dict[str, Any]:
    """
    Detect belt/logistics bottlenecks and flow inefficiencies.
    
    Args:
        planet_id: Specific planet to analyze
        item_filter: Only analyze belts carrying these items
        saturation_threshold: % of max throughput to flag (default 95%)
    
    Returns:
        Saturated belts and logistics station bottlenecks
    """
    logger.info(f"Analyzing logistics: planet={planet_id}, threshold={saturation_threshold}%")
    
    factory_state = await _get_factory_state()
    
    result = await logistics_analyzer.analyze(
        factory_state=factory_state,
        planet_id=planet_id,
        item_filter=item_filter,
        saturation_threshold=saturation_threshold
    )
    
    return result

@mcp.tool()
async def get_factory_snapshot(
    planet_id: Optional[int] = None,
    item_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Retrieve current production state for all items.
    
    Args:
        planet_id: Specific planet (None = all planets)
        item_filter: Only return data for these items
    
    Returns:
        Production, consumption, and storage for each item
    """
    logger.info(f"Getting factory snapshot: planet={planet_id}")
    
    factory_state = await _get_factory_state()
    
    # Filter and format data
    snapshot = {
        "timestamp": factory_state.timestamp,
        "planets": {}
    }
    
    for pid, planet in factory_state.planets.items():
        if planet_id is None or pid == planet_id:
            planet_data = {
                "items": []
            }
            
            for item_name, metrics in planet.production.items():
                if item_filter is None or item_name in item_filter:
                    planet_data["items"].append({
                        "name": item_name,
                        "production": metrics.production_rate,
                        "consumption": metrics.consumption_rate,
                        "storage": metrics.current_storage
                    })
            
            snapshot["planets"][pid] = planet_data
    
    return snapshot

@mcp.tool()
async def load_save_analysis(
    save_file_path: str,
    analysis_type: str = "full"
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
    
    factory_state = await save_parser.parse_file(save_file_path)
    
    if analysis_type == "production":
        return await bottleneck_analyzer.analyze(factory_state)
    elif analysis_type == "power":
        return await power_analyzer.analyze(factory_state)
    elif analysis_type == "logistics":
        return await logistics_analyzer.analyze(factory_state)
    else:  # full
        return {
            "production": await bottleneck_analyzer.analyze(factory_state),
            "power": await power_analyzer.analyze(factory_state),
            "logistics": await logistics_analyzer.analyze(factory_state)
        }

async def _get_factory_state():
    """Helper to get factory state from best available source."""
    if realtime_stream.is_connected():
        return await realtime_stream.get_current_state()
    else:
        return await save_parser.get_latest_state()

if __name__ == "__main__":
    mcp.run()
```

#### 2.2 Data Source Abstraction

**File**: `src/mcp_server/data_sources/realtime_stream.py`

```python
import asyncio
import websockets
import json
import logging
from typing import Optional
from ..models.factory_state import FactoryState

logger = logging.getLogger(__name__)

class RealTimeStream:
    """WebSocket client for real-time game data streaming."""
    
    def __init__(self, host: str = "localhost", port: int = 8470):
        self.uri = f"ws://{host}:{port}"
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.latest_state: Optional[FactoryState] = None
        self._receive_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Establish WebSocket connection to game plugin."""
        try:
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=10,
                ping_timeout=5
            )
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"Connected to game at {self.uri}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to game: {e}")
            return False
    
    async def _receive_loop(self):
        """Continuously receive and process game data."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                self.latest_state = FactoryState.from_realtime_data(data)
                logger.debug(f"Received state update: {len(data)} bytes")
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
    
    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        return (
            self.websocket is not None and 
            not self.websocket.closed and
            self.latest_state is not None
        )
    
    async def get_current_state(self) -> FactoryState:
        """Get most recent factory state from stream."""
        if not self.is_connected():
            if not await self.connect():
                raise ConnectionError("Cannot connect to game")
        
        # Wait for at least one state update
        timeout = 5.0
        elapsed = 0.0
        while self.latest_state is None and elapsed < timeout:
            await asyncio.sleep(0.1)
            elapsed += 0.1
        
        if self.latest_state is None:
            raise TimeoutError("No data received from game")
        
        return self.latest_state
    
    async def close(self):
        """Close WebSocket connection."""
        if self._receive_task:
            self._receive_task.cancel()
        if self.websocket:
            await self.websocket.close()
```

**File**: `src/mcp_server/data_sources/save_parser.py`

```python
import os
from pathlib import Path
from typing import Optional
from dsp_save_parser import parse  # qhgz2013 library
from ..models.factory_state import FactoryState

class SaveFileParser:
    """Parse DSP .dsv save files for offline analysis."""
    
    def __init__(self, auto_detect_path: bool = True):
        self.save_dir: Optional[Path] = None
        if auto_detect_path:
            self._detect_save_directory()
    
    def _detect_save_directory(self):
        """Auto-detect DSP save directory."""
        # Windows: %USERPROFILE%\Documents\Dyson Sphere Program\Save
        # Linux: ~/.config/unity3d/Youthcat Studio/Dyson Sphere Program/Save
        windows_path = Path.home() / "Documents" / "Dyson Sphere Program" / "Save"
        linux_path = Path.home() / ".config" / "unity3d" / "Youthcat Studio" / "Dyson Sphere Program" / "Save"
        
        if windows_path.exists():
            self.save_dir = windows_path
        elif linux_path.exists():
            self.save_dir = linux_path
    
    async def parse_file(self, file_path: str) -> FactoryState:
        """Parse specific .dsv save file."""
        save_data = parse(file_path)
        return FactoryState.from_save_data(save_data)
    
    async def get_latest_state(self) -> FactoryState:
        """Parse most recent save file in save directory."""
        if not self.save_dir or not self.save_dir.exists():
            raise FileNotFoundError("DSP save directory not found")
        
        # Find most recent .dsv file
        save_files = list(self.save_dir.glob("*.dsv"))
        if not save_files:
            raise FileNotFoundError("No save files found")
        
        latest_save = max(save_files, key=lambda p: p.stat().st_mtime)
        return await self.parse_file(str(latest_save))
```

#### 2.3 Data Models

**File**: `src/mcp_server/models/factory_state.py`

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class ItemMetrics:
    """Production metrics for a specific item."""
    item_name: str
    production_rate: float      # items/min
    consumption_rate: float     # items/min
    current_storage: int
    net_rate: float = field(init=False)
    
    def __post_init__(self):
        self.net_rate = self.production_rate - self.consumption_rate

@dataclass
class AssemblerMetrics:
    """Metrics for individual assembler/smelter."""
    assembler_id: int
    recipe_id: int
    production_rate: float
    theoretical_max: float
    efficiency: float = field(init=False)
    input_starved: bool = False
    output_blocked: bool = False
    
    def __post_init__(self):
        self.efficiency = (self.production_rate / self.theoretical_max * 100 
                          if self.theoretical_max > 0 else 0)

@dataclass
class PowerMetrics:
    """Power grid metrics for a planet."""
    generation_mw: float
    consumption_mw: float
    surplus_mw: float = field(init=False)
    accumulator_charge_percent: float = 0.0
    
    def __post_init__(self):
        self.surplus_mw = self.generation_mw - self.consumption_mw

@dataclass
class BeltMetrics:
    """Belt throughput metrics."""
    belt_id: int
    item_type: str
    throughput: float           # items/sec
    max_throughput: float       # items/sec (based on tier)
    saturation_percent: float = field(init=False)
    
    def __post_init__(self):
        self.saturation_percent = (self.throughput / self.max_throughput * 100
                                   if self.max_throughput > 0 else 0)

@dataclass
class PlanetState:
    """Complete state for a single planet."""
    planet_id: int
    production: Dict[str, ItemMetrics] = field(default_factory=dict)
    assemblers: List[AssemblerMetrics] = field(default_factory=list)
    power: Optional[PowerMetrics] = None
    belts: List[BeltMetrics] = field(default_factory=list)

@dataclass
class FactoryState:
    """Complete factory state across all planets."""
    timestamp: datetime
    planets: Dict[int, PlanetState] = field(default_factory=dict)
    
    @classmethod
    def from_realtime_data(cls, data: dict) -> 'FactoryState':
        """Construct FactoryState from real-time plugin data."""
        planets = {}
        
        for planet_id, planet_data in data.get("Planets", {}).items():
            planet_state = PlanetState(planet_id=int(planet_id))
            
            # Parse power metrics
            if "Power" in planet_data:
                power_data = planet_data["Power"]
                planet_state.power = PowerMetrics(
                    generation_mw=power_data["SurplusMW"] + power_data["Consumption"] / 16666.67,
                    consumption_mw=power_data["Consumption"] / 16666.67
                )
            
            # Parse production metrics
            for prod in planet_data.get("Production", []):
                # Convert to item metrics
                # ... (implementation details)
                pass
            
            planets[int(planet_id)] = planet_state
        
        return cls(
            timestamp=datetime.fromtimestamp(data.get("Timestamp", 0)),
            planets=planets
        )
    
    @classmethod
    def from_save_data(cls, save_data: dict) -> 'FactoryState':
        """Construct FactoryState from parsed save file."""
        # Transform qhgz2013 parser output to FactoryState
        # ... (implementation details)
        pass
```

## API Contracts

### MCP Tool Schemas

All tools follow JSON Schema Draft 7. Example for primary tool:

```json
{
  "name": "analyze_production_bottlenecks",
  "description": "Identify production chain bottlenecks causing throughput limitations",
  "inputSchema": {
    "type": "object",
    "properties": {
      "planet_id": {
        "type": ["integer", "null"],
        "description": "Specific planet to analyze (null = all planets)"
      },
      "target_item": {
        "type": ["string", "null"],
        "description": "Focus on specific product (e.g., 'green-circuit')"
      },
      "time_window": {
        "type": "integer",
        "default": 60,
        "description": "Analysis window in seconds for real-time mode"
      },
      "include_downstream": {
        "type": "boolean",
        "default": true,
        "description": "Trace impact to final products"
      }
    }
  }
}
```

### WebSocket Protocol

**Message Format** (Plugin → MCP Server):

```json
{
  "Timestamp": 1703520000,
  "Planets": {
    "1": {
      "PlanetId": 1,
      "Power": {
        "Generation": 1000000000,
        "Consumption": 850000000,
        "Surplus": 150000000,
        "SurplusMW": 9.0
      },
      "Production": [
        {
          "RecipeId": 1,
          "AssemblerId": 42,
          "ItemsProduced": 120,
          "ProductionRate": 7200.0,
          "InputStarved": false,
          "OutputBlocked": false
        }
      ],
      "Belts": [
        {
          "BeltId": 100,
          "ItemType": 1101,
          "Throughput": 28,
          "MaxThroughput": 30,
          "SaturationPercent": 93.3
        }
      ]
    }
  }
}
```

## Performance Requirements

### Latency Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Real-time state query | <100ms | 200ms |
| Bottleneck analysis | <1s | 2s |
| Save file parsing | <3s | 5s |
| Blueprint generation | <5s | 10s |
| WebSocket message delivery | <50ms | 100ms |

### Resource Constraints

| Component | CPU | Memory | Network |
|-----------|-----|--------|---------|
| BepInEx Plugin | <5% FPS impact | <100MB | <1MB/s upstream |
| MCP Server | <10% single core | <500MB | <2MB/s total |
| Total Impact | <15% | <600MB | <3MB/s |

## Error Handling Strategy

### Plugin Error Handling

```csharp
try
{
    MetricsCollector.RecordProduction(...);
}
catch (NullReferenceException ex)
{
    Logger.LogWarning($"Null reference in production tracking: {ex.Message}");
    // Continue execution, skip this frame
}
catch (Exception ex)
{
    Logger.LogError($"Critical error in production patch: {ex}");
    // Disable this patch to prevent crash loop
    _harmony.Unpatch(original, HarmonyPatchType.Postfix, PluginGuid);
}
```

### MCP Server Error Handling

```python
@mcp.tool()
async def analyze_production_bottlenecks(...) -> Dict[str, Any]:
    try:
        factory_state = await _get_factory_state()
        result = await bottleneck_analyzer.analyze(factory_state, ...)
        return result
    except ConnectionError as e:
        logger.error(f"Game connection failed: {e}")
        return {
            "error": "game_not_running",
            "message": "Could not connect to game. Ensure DSP is running with DysonMCP plugin installed.",
            "fallback": "Try load_save_analysis with a save file path instead."
        }
    except Exception as e:
        logger.exception("Unexpected error in bottleneck analysis")
        return {
            "error": "analysis_failed",
            "message": str(e)
        }
```

## Testing Strategy

### Unit Tests

**Python** (pytest):
- `test_save_parser.py`: Validate parsing of known save files
- `test_bottleneck_detection.py`: Algorithm correctness with synthetic data
- `test_factory_state.py`: Data model transformations

**C#** (NUnit):
- `ProductionPatchTests.cs`: Harmony patch execution
- `MetricsCollectorTests.cs`: Data aggregation logic
- `WebSocketServerTests.cs`: Connection handling

### Integration Tests

- `test_realtime_analysis.py`: End-to-end from game → MCP → Claude
- `test_websocket_reconnect.py`: Connection resilience
- `test_save_fallback.py`: Automatic fallback to offline mode

### Test Data

- `fixtures/sample_save.dsv`: Known factory state for deterministic testing
- `fixtures/bottleneck_scenario.json`: Synthetic state with known bottlenecks
- `fixtures/power_deficit.json`: Power shortage scenario

## Deployment & Distribution

### GitHub Release Artifacts

1. **BepInEx Plugin**: `DysonMCP-v1.0.0.zip`
   - Contains: `DysonMCP.dll`, `README.txt`, `config.cfg`
   - Installation: Extract to `BepInEx/plugins/`

2. **MCP Server**: `dyson-mcp-1.0.0.tar.gz`
   - PyPI package installable via `pip install dyson-mcp`
   - Includes CLI: `dyson-mcp serve`

3. **Documentation**: `docs.zip`
   - Installation guide, API reference, troubleshooting

### CI/CD Pipeline

**GitHub Actions Workflows**:

1. **build-bepinex.yml**: Compile C# plugin on commit
2. **test-mcp-server.yml**: Run Python tests + coverage
3. **release.yml**: Package artifacts on version tag

## Security Considerations

1. **Localhost Binding**: WebSocket server only binds to 127.0.0.1
2. **No Telemetry**: Zero external network communication
3. **Save File Sandboxing**: Parser executes in restricted context
4. **Input Validation**: All MCP tool parameters validated before processing

## Appendix: DSP Game Internals

### Key Classes (Decompiled from Assembly-CSharp.dll)

- `GameData`: Global game state singleton
- `PlanetFactory`: Per-planet factory data
- `AssemblerComponent`: Individual assembler/smelter state
- `PowerSystem`: Power grid calculations
- `CargoPath`: Belt logistics
- `StationComponent`: ILS/PLS logistics stations

### Item ID Mappings

Reference: `src/shared/item_ids.json`

```json
{
  "1101": "iron-ore",
  "1102": "copper-ore",
  "1103": "stone",
  "1104": "coal",
  "1105": "crude-oil",
  "1106": "iron-ingot",
  "1107": "copper-ingot"
}
```

### Recipe Database Structure

Reference: `src/mcp_server/utils/recipe_database.py`

Each recipe contains:
- Input items + quantities
- Output items + quantities
- Crafting time (seconds)
- Building type (assembler/smelter/refinery)
- Power consumption

## Document Version

- **Version**: 1.0
- **Date**: 2024-12-25
- **Author**: Matthew (Me, Myself Plus AI LLC)
- **Purpose**: Claude Code implementation handoff
