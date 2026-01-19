# mcp-dsp

MCP (Model Context Protocol) server for Dyson Sphere Program factory optimization. Enable AI-assisted bottleneck detection, power grid analysis, and logistics optimization.

## Overview

Dyson-MCP transforms Dyson Sphere Program from a manual optimization challenge into an AI-assisted factory management system. Ask natural language questions about production bottlenecks, power deficits, and logistics inefficiencies—receive actionable insights from both real-time game state and save file analysis.

## Architecture

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
│  • analyze_production_bottlenecks    • analyze_power_grid               │
│  • analyze_logistics_saturation      • generate_optimized_blueprint     │
│  • get_factory_snapshot              • load_save_analysis               │
└─────────────────────────────────────────────────────────────────────────┘
         ↑ WebSocket (ws://localhost:8470)      ↑ File I/O
         │                                      │
┌─────────────────────────────────────────────────────────────────────────┐
│            Layer 1: Game Instrumentation (C# BepInEx Plugin)            │
│  • Harmony IL Patches     • Real-time Metrics     • WebSocket Server    │
└─────────────────────────────────────────────────────────────────────────┘
         ↑ Runtime Patching
         │
┌─────────────────────────────────────────────────────────────────────────┐
│                 Layer 0: Dyson Sphere Program (Unity)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

### Production Analysis
- **Bottleneck Detection**: Identify what's limiting your production chains
- **Root Cause Analysis**: Trace dependencies to find upstream shortfalls
- **Efficiency Metrics**: Compare actual vs theoretical production rates

### Power Grid
- **Generation/Consumption Balance**: Monitor surplus/deficit in MW
- **Accumulator Analysis**: Track charge/discharge cycles
- **Critical Period Detection**: Identify when power dips below demand

### Logistics
- **Belt Saturation**: Find belts approaching maximum throughput
- **Station Bottlenecks**: Detect logistics station inventory issues
- **Vessel Wait Times**: Monitor interstellar logistics efficiency

## Installation

### Prerequisites
- Dyson Sphere Program (Steam)
- BepInEx 5.4.17+ ([Download](https://github.com/BepInEx/BepInEx/releases))
- Python 3.10+

### Quick Start

1. **Install BepInEx** into your DSP installation directory

2. **Install the Plugin**
   ```bash
   # Copy DysonMCP.dll to BepInEx/plugins/
   ```

3. **Install MCP Server**
   ```bash
   pip install dyson-mcp
   # or
   pip install -e .
   ```

4. **Configure Claude Desktop**
   ```json
   {
     "mcpServers": {
       "dyson-mcp": {
         "command": "dyson-mcp",
         "args": ["serve"]
       }
     }
   }
   ```

5. **Start Playing!**
   - Launch DSP (plugin loads automatically)
   - Ask Claude about your factory

## Usage Examples

```
"What's bottlenecking my green circuit production?"
→ "Green circuits limited by copper plate input with 420/min shortage"

"Analyze my power grid on planet 1"
→ "Power deficit of 420MW during peak, recommend adding 3 fusion plants"

"Which belts are saturated?"
→ "3 belts at >95% capacity: iron ingots (Line A), copper plates (Line B)"
```

## Development

See [Development Environment Setup](docs/dyson_mcp.md) for detailed instructions.

```bash
# Clone repository
git clone https://github.com/m2ai-mcp-servers/mcp-dsp.git
cd mcp-dsp

# Python setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run MCP server
python -m mcp_server.server
```

## Project Structure

```
Dyson/
├── src/
│   ├── bepinex_plugin/      # C# BepInEx plugin
│   │   ├── Plugin.cs        # Entry point
│   │   ├── Patches/         # Harmony patches
│   │   ├── DataCollectors/  # Metric collection
│   │   └── WebSocketServer.cs
│   ├── mcp_server/          # Python MCP server
│   │   ├── server.py        # FastMCP entry point
│   │   ├── data_sources/    # Real-time + save file
│   │   ├── tools/           # Analysis algorithms
│   │   └── models/          # Data models
│   └── shared/              # Shared data (item IDs, recipes)
├── tests/                   # Python tests
├── docs/                    # Documentation
└── .github/workflows/       # CI/CD
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `analyze_production_bottlenecks` | Identify production chain limitations |
| `analyze_power_grid` | Evaluate power generation and consumption |
| `analyze_logistics_saturation` | Detect belt and station bottlenecks |
| `get_factory_snapshot` | Retrieve current production state |
| `load_save_analysis` | Parse save file for offline analysis |
| `generate_optimized_blueprint` | Create optimized factory blueprints |

## Contributing

Contributions welcome! Please read the contributing guidelines first.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [qhgz2013/dsp_save_parser](https://github.com/qhgz2013/dsp_save_parser) - Save file parsing
- [BepInEx](https://github.com/BepInEx/BepInEx) - Unity modding framework
- [Anthropic](https://anthropic.com) - MCP protocol specification
