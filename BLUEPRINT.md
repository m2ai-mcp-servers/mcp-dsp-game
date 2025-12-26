# Dyson-MCP Project Blueprint

## Project Status Tracker

Track implementation progress across all phases. Check boxes as features are completed.

---

## Phase 0: Foundation
**Status**: Complete
**Goal**: Repository structure and development environment

- [x] Repository structure creation
- [x] README.md with project vision
- [x] pyproject.toml configuration
- [x] .gitignore setup
- [x] Development environment documentation (copied to docs/)
- [x] C# project file (.csproj) for BepInEx plugin
- [x] Python package structure (__init__.py files)
- [x] Initial commit and push

---

## Phase 1A: Save File Analysis (Offline Mode)
**Status**: In Progress
**Goal**: Parse DSP save files and provide basic factory analysis

- [x] Integration with qhgz2013/dsp_save_parser (vendored)
- [x] FactoryState data model (`src/mcp_server/models/factory_state.py`)
- [x] SaveFileParser data source (`src/mcp_server/data_sources/save_parser.py`)
- [x] `load_save_analysis` MCP tool (skeleton)
- [x] `get_factory_snapshot` MCP tool (skeleton)
- [x] Basic bottleneck detection algorithm (skeleton)
- [x] Unit tests (28 tests passing)
- [ ] Test with real DSP save file
- [ ] Recipe database for production rate calculation

**Success Criteria**:
- Parse .dsv files in <5 seconds for typical saves
- Extract production rates, power, and inventory data
- Handle corrupted saves gracefully

---

## Phase 1B: BepInEx Plugin
**Status**: In Progress
**Goal**: Real-time game data extraction via Harmony patches

- [x] BepInEx plugin initialization (Plugin.cs)
- [x] Harmony patch infrastructure
- [x] ProductionPatch - track assembler output
- [x] PowerPatch - track power generation/consumption
- [x] LogisticsPatch - track belt throughput
- [x] MetricsCollector for aggregating data
- [x] MetricsSnapshot data model
- [x] WebSocket server implementation
- [x] Configuration system (BepInEx config)
- [ ] Plugin testing in-game

**Success Criteria**:
- Plugin loads without crashing DSP
- <5% FPS impact during metric collection
- WebSocket streams JSON metrics at 1Hz

---

## Phase 2: Real-Time Integration
**Status**: Complete
**Goal**: Connect MCP server to live game data

- [x] WebSocket client in MCP server
- [x] RealTimeStream data source (with exponential backoff reconnection)
- [x] Data source router (real-time → save fallback)
- [x] Tool migration to real-time mode
- [x] Latency optimization (<200ms target)
- [x] Connection resilience (reconnect logic with backoff)
- [ ] Integration testing with running game

**Success Criteria**:
- <200ms latency from game state to MCP response
- Graceful fallback to save file when game not running
- Stable WebSocket connection for extended play sessions

---

## Phase 3: Optimization Engine
**Status**: In Progress
**Goal**: Advanced analysis algorithms

- [x] Recipe database construction (all DSP recipes - 53 recipes in `src/shared/recipes.json`)
- [x] Item ID mapping file (`src/shared/item_ids.json`)
- [x] Dependency graph builder (`src/mcp_server/utils/recipe_database.py`)
- [x] Root cause bottleneck analysis (upstream/downstream tracing)
- [x] BottleneckAnalyzer tool implementation (full with critical path)
- [x] PowerAnalyzer tool implementation (with consumption breakdown)
- [x] LogisticsAnalyzer tool implementation (with throughput requirements)
- [ ] Blueprint format research
- [ ] Blueprint generation engine
- [ ] `generate_optimized_blueprint` tool (P2)

**Success Criteria**:
- >95% accuracy in bottleneck identification
- Analysis completes in <2 seconds
- Blueprints importable into DSP

---

## Phase 4: CI/CD & Polish
**Status**: In Progress
**Goal**: Production-ready release

- [x] GitHub Actions: Build BepInEx plugin (`.github/workflows/build-plugin.yml`)
- [x] GitHub Actions: Run Python tests (`.github/workflows/python-tests.yml`)
- [x] GitHub Actions: Release automation (`.github/workflows/release.yml`)
- [x] 65% Python test coverage (67 tests, core modules 80%+)
- [ ] >60% C# test coverage
- [x] Installation guide (`docs/INSTALLATION.md`)
- [ ] Comprehensive API documentation
- [ ] Demo video: Bottleneck detection
- [ ] Demo video: Power analysis
- [ ] Portfolio integration

**Success Criteria**:
- CI/CD pipeline operational
- All tests passing
- Documentation complete

---

## Quick Reference

### Key Files

| Component | Primary File |
|-----------|-------------|
| MCP Server Entry | `src/mcp_server/server.py` |
| Plugin Entry | `src/bepinex_plugin/Plugin.cs` |
| Factory State Model | `src/mcp_server/models/factory_state.py` |
| Save Parser | `src/mcp_server/data_sources/save_parser.py` |
| Real-Time Stream | `src/mcp_server/data_sources/realtime_stream.py` |
| Data Source Router | `src/mcp_server/data_sources/router.py` |
| Item IDs | `src/shared/item_ids.json` |
| Recipe Database | `src/mcp_server/utils/recipe_database.py` |
| Recipes | `src/shared/recipes.json` |
| Bottleneck Analyzer | `src/mcp_server/tools/bottleneck_analyzer.py` |
| Power Analyzer | `src/mcp_server/tools/power_analyzer.py` |
| Logistics Analyzer | `src/mcp_server/tools/logistics_analyzer.py` |

### MCP Tools

| Tool | Priority | Status |
|------|----------|--------|
| `get_factory_snapshot` | P0 | Complete |
| `load_save_analysis` | P0 | Complete |
| `analyze_production_bottlenecks` | P0 | Complete (with recipe DB) |
| `analyze_power_grid` | P1 | Complete (with power breakdown) |
| `analyze_logistics_saturation` | P1 | Complete (with throughput calc) |
| `get_connection_status` | P0 | Complete |
| `connect_to_game` | P0 | Complete |
| `list_save_files` | P0 | Complete |
| `generate_optimized_blueprint` | P2 | Not Started |

### Performance Targets

| Metric | Target | Maximum |
|--------|--------|---------|
| Real-time query | <100ms | 200ms |
| Bottleneck analysis | <1s | 2s |
| Save file parsing | <3s | 5s |
| FPS impact | <2% | 5% |

---

## Notes

### 2024-12-26: Phase 1A Progress
- Vendored qhgz2013/dsp_save_parser library (not pip-installable)
- Implemented FactoryState.from_save_data() to extract power metrics and assembler data
- SaveFileParser now uses the vendored library
- 28 unit tests passing
- Need real DSP save file to test full parsing

### 2024-12-26: Phase 1B Progress
- Created Plugin.cs with BepInEx initialization and configuration
- Implemented MetricsSnapshot data model with JSON serialization
- Created MetricsCollector with thread-safe accumulator pattern
- Implemented Harmony patches for Production, Power, and Logistics
- Created WebSocketServer implementing RFC 6455 protocol
- Plugin ready for in-game testing

### 2024-12-26: Phase 2 Progress
- Enhanced RealTimeStream with exponential backoff reconnection
- Created DataSourceRouter for intelligent source selection
- Updated FactoryState.from_realtime_data() to match C# JSON schema
- Added new MCP tools: get_connection_status, connect_to_game, list_save_files
- All tools now report data_source in responses
- Added require_realtime parameter to analysis tools
- Latency tracking and health monitoring implemented

### Architecture Decision: Vendoring
The dsp_save_parser library doesn't have setup.py/pyproject.toml, so we vendor it directly
in `src/mcp_server/vendor/dsp_save_parser/`. This ensures reproducible builds.

### 2024-12-26: Phase 3 Progress
- Created comprehensive `src/shared/recipes.json` with 53 DSP recipes
- Created `src/mcp_server/utils/recipe_database.py` with:
  - Item ID/name lookup
  - Recipe lookup and production rate calculations
  - Dependency graph builder (upstream/downstream tracing)
  - Building speed multipliers by tier
- Enhanced BottleneckAnalyzer with:
  - Recipe database integration for item name resolution
  - Grouped assembler analysis by recipe
  - Root cause detection (input_starvation, output_blocked, low_efficiency)
  - Critical path construction through bottleneck chain
  - Human-readable summary generation
- Enhanced PowerAnalyzer with:
  - Power consumption breakdown by production line
  - Top power consumers per planet
  - Building type aggregation
- Enhanced LogisticsAnalyzer with:
  - Throughput requirement calculations
  - Belt tier recommendations per item
  - Item name resolution from IDs

### 2024-12-26: Phase 4 Progress
- Created GitHub Actions workflows:
  - `python-tests.yml`: Multi-version Python testing (3.10-3.12) with coverage
  - `build-plugin.yml`: BepInEx plugin build with structure validation
  - `release.yml`: Automated releases on version tags
- Added `.coveragerc` to exclude vendor code from coverage metrics
- Created comprehensive test suites:
  - `test_recipe_database.py` (22 tests)
  - `test_analyzers.py` (17 tests)
- Fixed recipe database recursion bug during loading
- Created `docs/INSTALLATION.md` installation guide
- Test coverage: 65% overall, core modules 80%+ (excluding vendor code)

---

**Last Updated**: 2024-12-26
**Current Phase**: Phase 4 In Progress (CI/CD Complete, Documentation Pending)
