# Product Requirements Document: Dyson Sphere Program MCP Integration

## Executive Summary

**Project Name**: Dyson-MCP  
**Version**: 1.0  
**Author**: Matthew (Me, Myself Plus AI LLC)  
**Target Audience**: MCP Engineer role positioning at Anthropic, DSP optimization community  
**Strategic Purpose**: Demonstrate production-grade MCP engineering with hybrid real-time/offline architecture, agentic optimization systems, and full-stack integration across C#/Python/MCP protocols

## Vision Statement

Create a comprehensive Model Context Protocol (MCP) server that transforms Dyson Sphere Program from a manual optimization challenge into an AI-assisted factory management system. Enable players to ask natural language questions about production bottlenecks, power deficits, and logistics inefficiencies—receiving actionable insights from both real-time game state and historical save file analysis.

## Business Objectives

### Primary Objectives
1. **Portfolio Differentiation**: Build flagship MCP engineering demonstration showing sophisticated multi-layer integration (Unity C# → Python → Claude)
2. **Technical Capability Proof**: Validate ability to architect production-quality systems with hybrid data sources, real-time streaming, and agentic optimization
3. **Community Value**: Solve genuine DSP optimization pain points, creating shareable public artifact
4. **Career Positioning**: Support $200K+ remote role applications with concrete production expertise demonstration

### Success Metrics
- **Technical**: <200ms latency for real-time queries, 95%+ accuracy in bottleneck detection, successful CI/CD pipeline
- **Usage**: Public GitHub repository with comprehensive documentation, 3+ demo videos showing real-world optimization scenarios
- **Career**: Reference artifact in Anthropic MCP Engineer application, discussable case study in technical interviews

## User Personas

### Primary Persona: Advanced DSP Player (Self)
- **Background**: 100+ hours in DSP, understands production chains and optimization theory
- **Pain Points**: 
  - Manual bottleneck hunting across multiple planets is tedious
  - Power grid balancing requires spreadsheet analysis
  - Blueprint optimization involves trial-and-error iteration
  - No visibility into why production chains stall
- **Goals**: 
  - Ask "why is my green circuit production at 60% of target?" and get root cause
  - Receive proactive alerts when power deficit approaching
  - Generate optimized blueprints for target throughput requirements
- **Technical Comfort**: Willing to install BepInEx mods, run Python MCP servers, comfortable with technical setup

### Secondary Persona: MCP Engineering Evaluator
- **Background**: Technical hiring manager or senior engineer at Anthropic
- **Evaluation Criteria**:
  - Quality of MCP tool schema design
  - Sophistication of agentic reasoning patterns
  - Production engineering practices (error handling, testing, CI/CD)
  - Code quality and documentation standards
- **Goals**: Assess candidate's ability to build production MCP integrations
- **Success Indicators**: Clean architecture, comprehensive error handling, well-documented APIs, demonstrable real-world problem solving

## Functional Requirements

### FR-1: Save File Analysis (Offline Mode)
**Priority**: P0 (Must Have)  
**User Story**: As a DSP player, I want to analyze my save file without running the game so I can optimize my factory between play sessions.

**Acceptance Criteria**:
- System can parse .dsv binary save files using qhgz2013/dsp_save_parser library
- Extracts complete factory state: buildings, production rates, inventory, power grid
- MCP tool `load_save_analysis` returns structured factory state
- Analysis completes within 5 seconds for typical save files (<50MB)
- Handles corrupted saves gracefully with clear error messages

**Technical Specifications**:
- Integration with existing Python save parser library
- Data model transformation from parser output to FactoryState schema
- File system monitoring for auto-reload on save file updates
- Support for DSP save format versions 0.9.24+

### FR-2: Real-Time Game State Streaming
**Priority**: P0 (Must Have)  
**User Story**: As a DSP player, I want to analyze my factory while actively playing so I can respond to bottlenecks as they develop.

**Acceptance Criteria**:
- BepInEx plugin loads successfully in DSP without crashes
- Harmony patches execute on GameData, PlanetFactory, PowerSystem, CargoTraffic classes
- WebSocket server on port 8470 streams JSON metrics at configurable frequency (default 1Hz)
- Metrics include: production rates per assembler, belt throughput, power generation/consumption, logistics station state
- Plugin has <5% performance impact on game FPS
- Connection loss handled gracefully (buffering + reconnect logic)

**Technical Specifications**:
- C# BepInEx 5.4.17 plugin targeting .NET Framework 4.6
- Harmony 2.x runtime IL patching
- WebSocket server using System.Net.WebSockets or third-party library
- JSON serialization with Newtonsoft.Json
- Configuration file for metric collection settings

### FR-3: Production Bottleneck Detection
**Priority**: P0 (Must Have)  
**User Story**: As a DSP player, I want to identify what's limiting my production chains so I can fix the root cause instead of guessing.

**Acceptance Criteria**:
- MCP tool `analyze_production_bottlenecks` identifies bottlenecks within 2 seconds
- Correctly distinguishes input starvation vs. output backup vs. power limitations
- Traces dependency chains to identify upstream shortfalls
- Returns actionable recommendations (e.g., "Increase iron ore mining by 200/min")
- Handles multi-planet production networks
- Accuracy validated against known bottleneck test cases (>95% correct identification)

**Algorithm Requirements**:
- Compare actual production rates vs. theoretical maximum (recipe speed × assembler count)
- Detect input buffer starvation (empty input slots for >3 consecutive seconds)
- Detect output buffer backup (full output slots for >3 consecutive seconds)
- Build dependency graph recursively (item → inputs → raw resources)
- Calculate critical path through dependency graph
- Score bottleneck severity based on throughput impact

### FR-4: Power Grid Analysis
**Priority**: P1 (Should Have)  
**User Story**: As a DSP player, I want to understand my power generation/consumption balance so I can avoid brownouts.

**Acceptance Criteria**:
- MCP tool `analyze_power_grid` returns current surplus/deficit in MW
- Identifies critical periods (times when power dips below demand)
- Calculates accumulator efficiency (% of theoretical storage utilized)
- Provides recommendations for additional generation or consumption reduction
- Handles multiple power networks on same planet
- Supports both real-time and save file analysis modes

**Technical Specifications**:
- Track PowerSystem.consumerCursor and PowerSystem.genCursor
- Monitor PowerNodeComponent states for generation/consumption
- Calculate accumulator charge/discharge cycles
- Time-series analysis for deficit period detection

### FR-5: Logistics Saturation Analysis
**Priority**: P1 (Should Have)  
**User Story**: As a DSP player, I want to know which belts are saturated so I can upgrade them before they cause backups.

**Acceptance Criteria**:
- MCP tool `analyze_logistics_saturation` identifies belts above saturation threshold (default 95%)
- Reports current throughput vs. maximum for belt tier
- Lists connected buildings (producers/consumers)
- Identifies logistics station inventory bottlenecks (>90% full or vessel wait times >30s)
- Configurable saturation threshold and item filters

**Technical Specifications**:
- Patch CargoPath.Update to track items/sec throughput
- Compare against belt tier maximums (Blue: 30/s, Red: 60/s, Green: 120/s)
- Track StationComponent vessel arrival/departure times
- Monitor StationComponent.storage array for utilization

### FR-6: Blueprint Generation
**Priority**: P2 (Nice to Have)  
**User Story**: As a DSP player, I want to generate optimized blueprints for target production rates so I can build efficient factories faster.

**Acceptance Criteria**:
- MCP tool `generate_optimized_blueprint` returns base64 encoded blueprint string
- Blueprint achieves within 10% of target production rate
- Respects constraints (max footprint, power budget, preferred recipe)
- Includes construction cost calculations
- Supports optimization goals: minimal_footprint, power_efficient, throughput_maximized
- Generated blueprints are importable into DSP without errors

**Technical Specifications**:
- Recipe database with all DSP production chains, crafting times, power consumption
- Constraint satisfaction solver for building placement
- Blueprint format encoding (reverse-engineer DSP blueprint string format)
- Validation against game rules (building spacing, belt connections)

## Non-Functional Requirements

### NFR-1: Performance
- Real-time bottleneck analysis completes within 2 seconds for factories with <10,000 buildings
- Save file parsing completes within 5 seconds for <50MB files
- BepInEx plugin maintains <5% FPS impact during metric collection
- WebSocket streaming latency <200ms from game state change to MCP server receipt
- MCP server handles 10+ concurrent tool invocations without degradation

### NFR-2: Reliability
- BepInEx plugin recovers from Harmony patch failures without crashing DSP
- WebSocket server auto-reconnects on connection loss with exponential backoff
- MCP server degrades gracefully to save file mode when real-time unavailable
- All external dependencies (save parser library) have fallback error handling
- System state persisted across MCP server restarts (configuration, cached analysis)

### NFR-3: Maintainability
- Comprehensive unit test coverage (>80% for Python, >60% for C#)
- Integration tests for end-to-end workflows (save analysis, real-time streaming, bottleneck detection)
- CI/CD pipeline automates builds, tests, and releases
- API versioning for MCP tool schemas (allows backward compatibility)
- Logging at debug/info/warn/error levels with configurable verbosity
- Code documentation with XML comments (C#) and docstrings (Python)

### NFR-4: Usability
- Installation process documented with step-by-step instructions
- Configuration file with sensible defaults (minimal required changes)
- Clear error messages for common issues (game not running, save file not found, port conflicts)
- Example queries documented in README for common optimization scenarios
- Demo videos showing installation and usage

### NFR-5: Security
- WebSocket server binds to localhost only (no external exposure)
- No telemetry or data collection beyond local MCP server
- Save file parsing sandboxed (no arbitrary code execution from malicious saves)
- Configuration file validation prevents injection attacks

## Technical Architecture Requirements

### TAR-1: MCP Protocol Compliance
- Server implements MCP protocol specification for tool definitions
- Tool schemas follow JSON Schema Draft 7
- Server supports both stdio and SSE transport mechanisms
- Error responses conform to MCP error format
- Server metadata includes version, capabilities, supported tools

### TAR-2: Data Source Abstraction
- Abstract interface for data sources (RealTimeStream, SaveFileParser)
- Tools query abstraction layer, not specific data sources directly
- Automatic fallback from real-time → save file when game not running
- Configuration specifies preferred data source priority

### TAR-3: Plugin Architecture
- BepInEx plugin follows standard mod structure (Plugin.cs entry point)
- Harmony patches isolated in separate classes (ProductionPatch, PowerPatch, LogisticsPatch)
- Data collectors decoupled from export mechanism (allow future HTTP/file export)
- Configuration system using BepInEx config API

### TAR-4: Extensibility
- Plugin architecture allows adding new metric collectors without core changes
- MCP tool registry allows dynamic tool registration
- Recipe database updatable for new DSP versions
- Analysis algorithms pluggable (allow custom bottleneck detection strategies)

## Development Phases

### Phase 0: Foundation (Week 1)
- Repository structure creation
- Development environment setup documentation
- Dependency management (pyproject.toml, .csproj)
- Initial README with project vision

### Phase 1A: Save File Analysis (Weeks 2-3)
- Integration with qhgz2013/dsp_save_parser
- FactoryState data model
- `load_save_analysis` and `get_factory_snapshot` tools (offline mode)
- Basic bottleneck detection on static data
- Unit tests with real save file fixtures

### Phase 1B: BepInEx Plugin (Weeks 4-6)
- BepInEx plugin initialization
- Harmony patch infrastructure
- Production/power/logistics metric collection
- WebSocket server implementation
- Configuration system

### Phase 2: Real-Time Integration (Weeks 7-8)
- MCP server WebSocket client
- Real-time data source implementation
- Tool migration to real-time mode
- Latency optimization
- Integration testing with running game

### Phase 3: Optimization Engine (Weeks 9-11)
- Recipe database construction
- Dependency graph algorithms
- Root cause bottleneck analysis
- Blueprint generation engine
- `generate_optimized_blueprint` tool

### Phase 4: CI/CD & Polish (Week 12+)
- GitHub Actions workflows
- Automated testing and releases
- Comprehensive documentation
- Demo video production
- Portfolio integration

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| DSP game updates break Harmony patches | High | Medium | Version pinning, automated testing on updates, community monitoring |
| Save file format changes between DSP versions | Medium | Low | Parser library maintenance, format versioning |
| WebSocket performance insufficient for real-time | Medium | Low | Profiling, batching, compression, fallback to polling |
| Blueprint generation complexity exceeds estimates | Medium | Medium | Deprioritize to P2, focus on analysis tools first |
| BepInEx plugin causes game crashes | High | Medium | Extensive testing, graceful error handling, user crash reporting |

### Project Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep delays core features | Medium | High | Strict phase gating, P0/P1/P2 prioritization |
| C# learning curve slows development | Low | Medium | Start with save analysis (Python-only), parallel C# learning |
| Community overlap with existing tools | Low | Low | Differentiate on MCP integration, agentic capabilities |
| Limited time availability | Medium | Medium | Focus on P0 features, accept longer timeline for polish |

## Success Criteria

### Minimum Viable Product (MVP)
- [ ] Save file analysis functional with bottleneck detection
- [ ] BepInEx plugin streams real-time production metrics
- [ ] MCP server with 3 core tools: analyze_bottlenecks, analyze_power_grid, get_factory_snapshot
- [ ] Documentation for installation and basic usage
- [ ] Demo video showing bottleneck detection in action

### Version 1.0 Release
- [ ] All P0 and P1 features implemented
- [ ] CI/CD pipeline operational
- [ ] Comprehensive test coverage
- [ ] Public repository with 100+ stars (community validation)
- [ ] Referenced in Anthropic MCP Engineer application materials

### Portfolio Excellence
- [ ] Clean, documented codebase reviewable by technical evaluators
- [ ] Demonstrates production engineering practices (testing, CI/CD, error handling)
- [ ] Clear architectural separation of concerns
- [ ] Novel integration approach (hybrid real-time/offline)
- [ ] Measurable impact (user testimonials, community adoption)

## Appendix A: Related Work

### Existing DSP Tools
- **DSP Resource Tracker**: Mod providing real-time production tracking, demonstrates BepInEx viability
- **Nebula Multiplayer**: Networking infrastructure shows TCP communication patterns
- **qhgz2013/dsp_save_parser**: Python library for save file parsing

### Relevant Patterns
- **Factorio Learning Environment**: REPL-based AI integration, MCP protocol support
- **Game optimization tools**: Satisfactory Calculator, Oxygen Not Included Tools

### Differentiation
- Only DSP tool with MCP integration
- Hybrid real-time + offline analysis (others choose one)
- Agentic optimization (AI-assisted planning vs. static calculators)
- Production-quality engineering focus

## Appendix B: Glossary

- **BepInEx**: Unity game modding framework using Harmony IL patching
- **Harmony**: Runtime code injection library for .NET applications
- **MCP**: Model Context Protocol, Anthropic's protocol for AI tool integration
- **FastMCP**: Python framework for building MCP servers
- **DSP**: Dyson Sphere Program, factory simulation game
- **.dsv**: Dyson Sphere Program save file format
- **Bottleneck**: Production chain limitation preventing optimal throughput
- **Blueprint**: Sharable factory layout design in DSP
- **ILS/PLS**: Interstellar/Planetary Logistics Station in DSP

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-12-25 | Matthew | Initial PRD creation for Claude Code handoff |
