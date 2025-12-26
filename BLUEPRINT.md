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
**Status**: Not Started
**Goal**: Advanced analysis algorithms

- [ ] Recipe database construction (all DSP recipes)
- [ ] Item ID mapping file
- [ ] Dependency graph builder
- [ ] Root cause bottleneck analysis
- [ ] BottleneckAnalyzer tool implementation
- [ ] PowerAnalyzer tool implementation
- [ ] LogisticsAnalyzer tool implementation
- [ ] Blueprint format research
- [ ] Blueprint generation engine
- [ ] `generate_optimized_blueprint` tool (P2)

**Success Criteria**:
- >95% accuracy in bottleneck identification
- Analysis completes in <2 seconds
- Blueprints importable into DSP

---

## Phase 4: CI/CD & Polish
**Status**: Not Started
**Goal**: Production-ready release

- [ ] GitHub Actions: Build BepInEx plugin
- [ ] GitHub Actions: Run Python tests
- [ ] GitHub Actions: Release automation
- [ ] >80% Python test coverage
- [ ] >60% C# test coverage
- [ ] Comprehensive documentation
- [ ] Installation guide
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
| Item IDs | `src/shared/item_ids.json` |
| Recipe Database | `src/mcp_server/utils/recipe_database.py` |

### MCP Tools

| Tool | Priority | Status |
|------|----------|--------|
| `get_factory_snapshot` | P0 | Skeleton |
| `load_save_analysis` | P0 | Skeleton |
| `analyze_production_bottlenecks` | P0 | Skeleton |
| `analyze_power_grid` | P1 | Skeleton |
| `analyze_logistics_saturation` | P1 | Skeleton |
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

---

**Last Updated**: 2024-12-26
**Current Phase**: Phase 2 Complete (Integration Testing Pending)
