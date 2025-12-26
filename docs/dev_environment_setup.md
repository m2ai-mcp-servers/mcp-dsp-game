# Development Environment Setup Guide

## Prerequisites

### Required Software

| Software | Version | Purpose | Download |
|----------|---------|---------|----------|
| **Dyson Sphere Program** | Latest | Target game | Steam |
| **BepInEx 5** | 5.4.17+ | Unity modding framework | [GitHub](https://github.com/BepInEx/BepInEx/releases) |
| **Visual Studio 2022** | Community/Pro | C# development | [Microsoft](https://visualstudio.microsoft.com/) |
| **.NET Framework** | 4.6+ | C# compilation target | Included with VS |
| **Python** | 3.10+ | MCP server development | [python.org](https://www.python.org/downloads/) |
| **Git** | Latest | Version control | [git-scm.com](https://git-scm.com/) |

### Optional but Recommended

- **dnSpy** (0.11.8+): Decompiler for exploring DSP assemblies
- **VS Code**: Python development alternative
- **Fiddler/Wireshark**: WebSocket debugging

## Initial Setup (Windows)

### 1. Locate DSP Installation

```powershell
# Find DSP installation directory
# Default Steam path:
$DSP_PATH = "C:\Program Files (x86)\Steam\steamapps\common\Dyson Sphere Program"

# Verify installation
if (Test-Path "$DSP_PATH\DSPGAME.exe") {
    Write-Host "✓ DSP found at: $DSP_PATH" -ForegroundColor Green
} else {
    Write-Host "✗ DSP not found. Check Steam library location." -ForegroundColor Red
}

# Set environment variable for convenience
[System.Environment]::SetEnvironmentVariable("DSP_PATH", $DSP_PATH, "User")
```

### 2. Install BepInEx

```powershell
# Download BepInEx 5.x64 (Unity IL2CPP build)
$BEPINEX_URL = "https://github.com/BepInEx/BepInEx/releases/download/v5.4.22/BepInEx_x64_5.4.22.0.zip"
$TEMP_ZIP = "$env:TEMP\BepInEx.zip"

# Download
Invoke-WebRequest -Uri $BEPINEX_URL -OutFile $TEMP_ZIP

# Extract to DSP directory
Expand-Archive -Path $TEMP_ZIP -DestinationPath $DSP_PATH -Force

# Verify installation
if (Test-Path "$DSP_PATH\BepInEx") {
    Write-Host "✓ BepInEx installed successfully" -ForegroundColor Green
    
    # Run game once to generate config files
    Write-Host "Starting DSP to initialize BepInEx..." -ForegroundColor Yellow
    Start-Process "$DSP_PATH\DSPGAME.exe" -Wait
    
    Write-Host "✓ BepInEx initialized" -ForegroundColor Green
} else {
    Write-Host "✗ BepInEx installation failed" -ForegroundColor Red
}
```

### 3. Extract DSP Assemblies for Development

```powershell
# Copy managed assemblies to a dev reference directory
$MANAGED_PATH = "$DSP_PATH\DSPGAME_Data\Managed"
$DEV_REFS = "$env:USERPROFILE\Documents\DSP-DevRefs"

New-Item -ItemType Directory -Force -Path $DEV_REFS

# Copy required assemblies
$REQUIRED_ASSEMBLIES = @(
    "Assembly-CSharp.dll",
    "UnityEngine.CoreModule.dll",
    "UnityEngine.dll",
    "UnityEngine.UI.dll",
    "0Harmony.dll"
)

foreach ($assembly in $REQUIRED_ASSEMBLIES) {
    Copy-Item "$MANAGED_PATH\$assembly" -Destination $DEV_REFS -Force
    Write-Host "Copied $assembly" -ForegroundColor Green
}

Write-Host "`n✓ Development references ready at: $DEV_REFS" -ForegroundColor Green
```

### 4. Visual Studio 2022 Setup

**Install Workloads**:
1. Open Visual Studio Installer
2. Modify VS 2022 installation
3. Select workloads:
   - **.NET desktop development**
   - **Game development with Unity** (for Unity references)
4. Install

**Create Plugin Project**:

```powershell
# Clone repository (replace with your repo URL)
git clone https://github.com/yourusername/dyson-mcp.git
cd dyson-mcp

# Open solution in Visual Studio
start src\bepinex_plugin\DysonMCP.sln
```

**Configure Project References**:

In Visual Studio:
1. Right-click project → **Add** → **Reference**
2. Click **Browse** → Navigate to `$DEV_REFS`
3. Add all assemblies
4. Set **Copy Local** to **False** for all references (they exist in game directory)

**Build Configuration**:

Edit `DysonMCP.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net46</TargetFramework>
    <AssemblyName>DysonMCP</AssemblyName>
    <LangVersion>latest</LangVersion>
    <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
  </PropertyGroup>

  <ItemGroup>
    <Reference Include="Assembly-CSharp">
      <HintPath>$(USERPROFILE)\Documents\DSP-DevRefs\Assembly-CSharp.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="UnityEngine">
      <HintPath>$(USERPROFILE)\Documents\DSP-DevRefs\UnityEngine.dll</HintPath>
      <Private>False</Private>
    </Reference>
    <Reference Include="UnityEngine.CoreModule">
      <HintPath>$(USERPROFILE)\Documents\DSP-DevRefs\UnityEngine.CoreModule.dll</HintPath>
      <Private>False</Private>
    </Reference>
  </ItemGroup>

  <ItemGroup>
    <PackageReference Include="BepInEx.Core" Version="5.4.22" />
    <PackageReference Include="BepInEx.PluginInfoProps" Version="2.1.0" />
    <PackageReference Include="HarmonyX" Version="2.10.1" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>

  <!-- Auto-copy to DSP plugins folder on build -->
  <Target Name="PostBuild" AfterTargets="PostBuildEvent">
    <Copy SourceFiles="$(TargetPath)" 
          DestinationFolder="$(DSP_PATH)\BepInEx\plugins\" 
          SkipUnchangedFiles="true" />
  </Target>
</Project>
```

**Test Build**:

```powershell
# Build in Visual Studio (Ctrl+Shift+B) or via CLI:
dotnet build src\bepinex_plugin\DysonMCP.csproj

# Verify DLL copied to plugins
if (Test-Path "$env:DSP_PATH\BepInEx\plugins\DysonMCP.dll") {
    Write-Host "✓ Plugin built and deployed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Plugin deployment failed" -ForegroundColor Red
}
```

### 5. Python Environment Setup

```powershell
# Create virtual environment
cd dyson-mcp
python -m venv .venv

# Activate environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install development dependencies
pip install -e ".[dev]"

# Verify installation
python -c "import fastmcp; print('FastMCP version:', fastmcp.__version__)"
```

**Install External Dependencies**:

```powershell
# Install qhgz2013 save parser
pip install git+https://github.com/qhgz2013/dsp_save_parser.git

# Verify parser
python -c "from dsp_save_parser import parse; print('Save parser installed')"
```

**pyproject.toml Configuration**:

```toml
[project]
name = "dyson-mcp"
version = "1.0.0"
description = "MCP server for Dyson Sphere Program factory optimization"
authors = [{name = "Matthew", email = "your@email.com"}]
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=0.2.0",
    "websockets>=12.0",
    "pydantic>=2.0",
    "aiofiles>=23.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",
    "black>=23.0",
    "ruff>=0.1",
    "mypy>=1.5"
]

[project.scripts]
dyson-mcp = "mcp_server.server:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ["py310"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]
```

### 6. Test Save File Setup

```powershell
# Locate DSP save directory
$SAVE_DIR = "$env:USERPROFILE\Documents\Dyson Sphere Program\Save"

if (Test-Path $SAVE_DIR) {
    Write-Host "✓ Save directory found: $SAVE_DIR" -ForegroundColor Green
    
    # List save files
    Get-ChildItem "$SAVE_DIR\*.dsv" | 
        Select-Object Name, @{N='Size';E={"{0:N2} MB" -f ($_.Length / 1MB)}}, LastWriteTime |
        Format-Table -AutoSize
    
    # Copy latest save to test fixtures
    $LATEST_SAVE = Get-ChildItem "$SAVE_DIR\*.dsv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    
    New-Item -ItemType Directory -Force -Path "tests\fixtures"
    Copy-Item $LATEST_SAVE.FullName -Destination "tests\fixtures\sample_save.dsv" -Force
    
    Write-Host "✓ Test fixture created: tests\fixtures\sample_save.dsv" -ForegroundColor Green
} else {
    Write-Host "✗ Save directory not found" -ForegroundColor Red
}
```

## Development Workflow

### Plugin Development Cycle

```powershell
# 1. Make code changes in Visual Studio
# 2. Build project (Ctrl+Shift+B)
# 3. DLL auto-copied to BepInEx\plugins
# 4. Launch DSP to test

# OR use watch mode for rapid iteration:
dotnet watch --project src\bepinex_plugin\DysonMCP.csproj
```

### MCP Server Development Cycle

```powershell
# Activate venv if not already active
.\.venv\Scripts\Activate.ps1

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/mcp_server --cov-report=html

# Type checking
mypy src/mcp_server

# Code formatting
black src/mcp_server tests/
ruff check src/mcp_server tests/

# Start MCP server for testing
python -m mcp_server.server

# Or use FastMCP CLI:
fastmcp run src/mcp_server/server.py
```

### Integration Testing

**Terminal 1** (DSP with plugin):
```powershell
# Launch DSP
cd "$env:DSP_PATH"
.\DSPGAME.exe

# Verify plugin loaded:
# Check BepInEx\LogOutput.log for "DysonMCP 1.0.0 loaded successfully"
```

**Terminal 2** (MCP server):
```powershell
# Start MCP server
cd dyson-mcp
.\.venv\Scripts\Activate.ps1
python -m mcp_server.server
```

**Terminal 3** (Claude Desktop/test client):
```powershell
# Configure Claude Desktop to use local MCP server
# Edit: %APPDATA%\Claude\claude_desktop_config.json

# Test with MCP client:
fastmcp test src/mcp_server/server.py analyze_production_bottlenecks
```

## Debugging Strategies

### Plugin Debugging (C#)

**BepInEx Logging**:

```csharp
// In Plugin.cs
Logger.LogDebug("Detailed debug info");
Logger.LogInfo("Informational message");
Logger.LogWarning("Warning message");
Logger.LogError("Error message");

// Check logs at: BepInEx\LogOutput.log
```

**Visual Studio Debugging** (Advanced):

1. Build plugin in Debug configuration
2. In VS: **Debug** → **Attach to Process**
3. Select **DSPGAME.exe**
4. Set breakpoints in plugin code
5. Trigger code path in game

**Unity Explorer Integration** (optional):

```powershell
# Install UnityExplorer for runtime inspection
# Download from: https://github.com/sinai-dev/UnityExplorer/releases
# Extract to BepInEx\plugins\

# Press F7 in-game to open explorer
# Inspect live game objects, components, and state
```

### MCP Server Debugging (Python)

**Logging Configuration**:

```python
# Add to server.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dyson-mcp-debug.log'),
        logging.StreamHandler()
    ]
)
```

**Interactive Debugging**:

```powershell
# Run with debugger
python -m pdb -m mcp_server.server

# Or use VS Code launch.json:
# {
#   "version": "0.2.0",
#   "configurations": [
#     {
#       "name": "MCP Server",
#       "type": "python",
#       "request": "launch",
#       "module": "mcp_server.server",
#       "console": "integratedTerminal"
#     }
#   ]
# }
```

### WebSocket Debugging

**Monitor WebSocket Traffic**:

```powershell
# Test WebSocket connection manually
npm install -g wscat

# Connect to plugin
wscat -c ws://localhost:8470

# Should receive JSON metrics from game
```

**Wireshark Capture**:

1. Start Wireshark
2. Capture on loopback adapter
3. Filter: `tcp.port == 8470`
4. Inspect WebSocket frames

## Troubleshooting

### Common Issues

#### Plugin Not Loading

**Symptom**: No log entry in BepInEx\LogOutput.log

**Solutions**:
```powershell
# 1. Verify BepInEx installed correctly
Test-Path "$env:DSP_PATH\BepInEx\core\BepInEx.dll"

# 2. Check plugin DLL in correct location
Test-Path "$env:DSP_PATH\BepInEx\plugins\DysonMCP.dll"

# 3. Verify .NET Framework target
# DLL must be compiled for net46, check in dnSpy:
# Target Framework: .NETFramework,Version=v4.6
```

#### Harmony Patch Failures

**Symptom**: Errors in log about patch methods not found

**Solutions**:
```csharp
// 1. Verify method signature matches exactly
[HarmonyPatch(typeof(AssemblerComponent), "InternalUpdate")]
// Use dnSpy to confirm exact signature

// 2. Add try-catch to identify issue
[HarmonyPostfix]
public static void MyPatch_Postfix(AssemblerComponent __instance)
{
    try
    {
        // Patch logic
    }
    catch (Exception ex)
    {
        Logger.LogError($"Patch error: {ex}");
    }
}

// 3. Check Harmony debug log
HarmonyFileLog.Enabled = true;
```

#### WebSocket Connection Refused

**Symptom**: MCP server cannot connect to ws://localhost:8470

**Solutions**:
```powershell
# 1. Verify port not in use
netstat -ano | findstr :8470

# 2. Check firewall (Windows Defender)
New-NetFirewallRule -DisplayName "DSP MCP" -Direction Inbound -LocalPort 8470 -Protocol TCP -Action Allow

# 3. Test with simple HTTP listener first
# Modify plugin to use HTTP instead temporarily
```

#### Save Parser Errors

**Symptom**: Cannot parse .dsv files

**Solutions**:
```powershell
# 1. Verify save file not corrupted
# Try opening in DSP first

# 2. Check parser version compatibility
pip show dsp-save-parser

# 3. Try different save file
# Parser may not support latest DSP version
```

### Performance Issues

#### High FPS Impact

```csharp
// Reduce metric collection frequency
MetricsUpdateFrequency = Config.Bind("Performance", "UpdateFrequency", 1, 
    "Metrics collection frequency in Hz (1-60)");

// Batch updates instead of per-entity
private List<ProductionMetric> _pendingMetrics = new();

void Update()
{
    // Collect all metrics first
    CollectAllMetrics();
    
    // Batch send every N frames
    if (Time.frameCount % 60 == 0)
    {
        _wsServer.BroadcastMetrics(_pendingMetrics);
        _pendingMetrics.Clear();
    }
}
```

#### Memory Leaks

```csharp
// Implement IDisposable for all data collectors
public class MetricsCollector : IDisposable
{
    private Dictionary<int, ProductionMetric> _cache = new();
    
    public void Dispose()
    {
        _cache?.Clear();
        _cache = null;
    }
}

// Clean up in OnDestroy
void OnDestroy()
{
    _collector?.Dispose();
    _wsServer?.Stop();
    _harmony?.UnpatchSelf();
}
```

## CI/CD Setup (GitHub Actions)

### Repository Secrets

Configure in GitHub → Settings → Secrets:

- No secrets required for public repository
- For private: None needed (self-contained build)

### Build Workflow

**File**: `.github/workflows/build-bepinex.yml`

```yaml
name: Build BepInEx Plugin

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup .NET
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '6.0.x'
      
      - name: Restore dependencies
        run: dotnet restore src/bepinex_plugin/DysonMCP.csproj
      
      - name: Build
        run: dotnet build src/bepinex_plugin/DysonMCP.csproj --configuration Release --no-restore
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: DysonMCP-plugin
          path: src/bepinex_plugin/bin/Release/net46/DysonMCP.dll
```

### Test Workflow

**File**: `.github/workflows/test-mcp-server.yml`

```yaml
name: Test MCP Server

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      
      - name: Run tests
        run: pytest tests/ -v --cov=src/mcp_server --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Quick Reference Commands

```powershell
# === Plugin Development ===
# Build and deploy plugin
dotnet build src\bepinex_plugin\DysonMCP.csproj

# Watch mode (auto-rebuild)
dotnet watch --project src\bepinex_plugin\DysonMCP.csproj

# === MCP Server Development ===
# Activate environment
.\.venv\Scripts\Activate.ps1

# Run tests
pytest tests/ -v

# Run server
python -m mcp_server.server

# === Debugging ===
# View plugin logs
Get-Content "$env:DSP_PATH\BepInEx\LogOutput.log" -Tail 50 -Wait

# Test WebSocket
wscat -c ws://localhost:8470

# === Cleanup ===
# Remove build artifacts
dotnet clean src\bepinex_plugin\DysonMCP.csproj

# Clear Python cache
Remove-Item -Recurse -Force src\mcp_server\__pycache__

# Reset BepInEx config (fresh start)
Remove-Item "$env:DSP_PATH\BepInEx\config\*" -Force
```

## Next Steps

1. ✅ Complete this setup guide
2. ⬜ Scaffold repository structure (use blueprint)
3. ⬜ Implement basic plugin (loads without errors)
4. ⬜ Implement save file parser integration
5. ⬜ Test first MCP tool (`get_factory_snapshot`)
6. ⬜ Add Harmony patches for real-time data
7. ⬜ Implement WebSocket streaming
8. ⬜ Build bottleneck analysis algorithm
9. ⬜ Write comprehensive tests
10. ⬜ Set up CI/CD pipeline

## Support Resources

- **BepInEx Documentation**: https://docs.bepinex.dev/
- **Harmony Documentation**: https://harmony.pardeike.net/
- **FastMCP Documentation**: https://github.com/jlowin/fastmcp
- **DSP Modding Discord**: [Community link if available]
- **Unity Scripting API**: https://docs.unity3d.com/ScriptReference/

---

**Document Version**: 1.0  
**Last Updated**: 2024-12-25  
**Author**: Matthew (Me, Myself Plus AI LLC)
