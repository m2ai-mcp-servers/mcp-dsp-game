# Dyson-MCP Installation Guide

This guide covers installing both the MCP server (Python) and the BepInEx plugin (C#) for Dyson Sphere Program integration.

## Requirements

### MCP Server
- Python 3.10 or higher
- pip package manager

### BepInEx Plugin
- Dyson Sphere Program (Steam version)
- BepInEx 5.4.x

## Quick Start

### Option 1: Install from PyPI (Recommended)

```bash
pip install dyson-mcp
```

### Option 2: Install from Source

```bash
git clone https://github.com/MatthewSnow2/Dyson.git
cd Dyson
pip install -e .
```

## MCP Server Setup

### 1. Install the Package

```bash
pip install dyson-mcp
```

### 2. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dyson": {
      "command": "dyson-mcp",
      "args": []
    }
  }
}
```

**Config file locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 3. Verify Installation

Restart Claude Desktop and test with:
> "What MCP tools are available for Dyson Sphere Program?"

## BepInEx Plugin Setup

### 1. Install BepInEx

1. Download [BepInEx 5.4.x](https://github.com/BepInEx/BepInEx/releases) (x64 version)
2. Extract to your DSP game folder:
   ```
   Steam\steamapps\common\Dyson Sphere Program\
   ```
3. Run the game once to generate BepInEx config files

### 2. Install the Plugin

**From Release:**
1. Download `DysonMCP-Plugin.zip` from the [releases page](https://github.com/MatthewSnow2/Dyson/releases)
2. Extract to your BepInEx plugins folder:
   ```
   Dyson Sphere Program\BepInEx\plugins\DysonMCP\
   ```

**From Source:**
1. Open `src/bepinex_plugin/DysonMCP.csproj` in Visual Studio
2. Build in Release configuration
3. Copy the DLL to your plugins folder

### 3. Configure the Plugin

Edit `BepInEx\config\DysonMCP.cfg`:

```ini
[WebSocket]
# Port for MCP server connection
Port = 8765

# Enable real-time metrics streaming
EnableStreaming = true

[Metrics]
# Collection interval in seconds
CollectionInterval = 1

# Include belt throughput data
IncludeBeltMetrics = true

# Include assembler efficiency data
IncludeAssemblerMetrics = true
```

### 4. Verify Plugin Installation

1. Launch DSP
2. Check BepInEx console for: `[DysonMCP] Plugin loaded`
3. MCP server should connect automatically

## Usage Modes

### Offline Mode (Save Files)

Works without the game running:
- Analyzes save files in `%USERPROFILE%\Documents\Dyson Sphere Program\Save\`
- Limited to snapshot analysis (no real-time data)

### Real-Time Mode (Plugin)

Requires the game running with the plugin:
- Live production metrics
- Real-time bottleneck detection
- Power grid monitoring
- Belt saturation tracking

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `get_factory_snapshot` | Get current factory state |
| `analyze_production_bottlenecks` | Detect production issues |
| `analyze_power_grid` | Analyze power generation/consumption |
| `analyze_logistics_saturation` | Check belt throughput |
| `get_connection_status` | Check plugin connection |
| `list_save_files` | List available save files |

## Troubleshooting

### MCP Server Issues

**"Command not found"**
- Ensure Python is in your PATH
- Try: `python -m mcp_server.server`

**"Module not found"**
- Reinstall: `pip install --force-reinstall dyson-mcp`

### Plugin Issues

**Plugin not loading**
- Verify BepInEx is installed correctly
- Check `BepInEx\LogOutput.log` for errors
- Ensure all dependencies are in the `lib` folder

**WebSocket connection failed**
- Check firewall settings for port 8765
- Verify plugin is running (check BepInEx console)
- Try restarting both the game and Claude Desktop

### Connection Issues

**Real-time mode not working**
- Ensure the game is running with the plugin loaded
- Check that the WebSocket server is started (port 8765)
- MCP server automatically falls back to save file analysis

## Development Setup

For contributors:

```bash
# Clone repository
git clone https://github.com/MatthewSnow2/Dyson.git
cd Dyson

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linting
ruff check src/mcp_server
black --check src/mcp_server
```

## Support

- [GitHub Issues](https://github.com/MatthewSnow2/Dyson/issues)
- [Documentation](https://github.com/MatthewSnow2/Dyson/docs/)
