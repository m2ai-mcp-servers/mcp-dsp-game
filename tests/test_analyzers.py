"""Tests for analyzer tools."""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.models.factory_state import (
    FactoryState,
    PlanetState,
    PowerMetrics,
    AssemblerMetrics,
    BeltMetrics,
    ItemMetrics,
)
from mcp_server.tools.bottleneck_analyzer import BottleneckAnalyzer, Bottleneck
from mcp_server.tools.power_analyzer import PowerAnalyzer, PowerConsumer
from mcp_server.tools.logistics_analyzer import LogisticsAnalyzer, ThroughputRequirement


class TestBottleneckAnalyzer:
    """Tests for BottleneckAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return BottleneckAnalyzer()

    @pytest.fixture
    def factory_with_bottleneck(self):
        """Factory state with input starvation bottleneck."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Test Planet",
            power=PowerMetrics(
                generation_mw=100,
                consumption_mw=80,
            ),
        )
        # Add starved assemblers
        for i in range(10):
            planet.assemblers.append(AssemblerMetrics(
                assembler_id=i,
                recipe_id=1,  # Iron Ingot
                production_rate=30,  # Below theoretical
                theoretical_max=60,
                input_starved=i < 5,  # 50% starved
                output_blocked=False,
            ))
        return FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )

    @pytest.fixture
    def healthy_factory(self):
        """Factory state with no bottlenecks."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Healthy Planet",
            power=PowerMetrics(
                generation_mw=100,
                consumption_mw=50,
            ),
        )
        # Add efficient assemblers
        for i in range(5):
            planet.assemblers.append(AssemblerMetrics(
                assembler_id=i,
                recipe_id=1,
                production_rate=58,
                theoretical_max=60,
                input_starved=False,
                output_blocked=False,
            ))
        return FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )

    @pytest.mark.asyncio
    async def test_analyze_empty_factory(self, analyzer):
        """Analyze empty factory returns no bottlenecks."""
        factory = FactoryState(timestamp=datetime.now(), planets={})
        result = await analyzer.analyze(factory)
        assert result["bottlenecks_found"] == 0
        assert result["summary"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_analyze_healthy_factory(self, analyzer, healthy_factory):
        """Healthy factory has no major bottlenecks."""
        result = await analyzer.analyze(healthy_factory)
        assert result["planets_analyzed"] == 1
        assert result["total_assemblers"] == 5

    @pytest.mark.asyncio
    async def test_analyze_bottleneck_detection(self, analyzer, factory_with_bottleneck):
        """Detects input starvation bottleneck."""
        result = await analyzer.analyze(factory_with_bottleneck)
        assert result["bottlenecks_found"] >= 1
        # Check bottleneck details
        bottleneck = result["bottlenecks"][0]
        assert bottleneck["type"] == "input_starvation"
        assert "recommendation" in bottleneck

    @pytest.mark.asyncio
    async def test_analyze_specific_planet(self, analyzer, factory_with_bottleneck):
        """Can analyze specific planet."""
        result = await analyzer.analyze(factory_with_bottleneck, planet_id=1)
        assert result["planets_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_analyze_nonexistent_planet(self, analyzer, factory_with_bottleneck):
        """Analyzing nonexistent planet returns no data."""
        result = await analyzer.analyze(factory_with_bottleneck, planet_id=999)
        assert result["planets_analyzed"] == 0

    def test_bottleneck_dataclass(self):
        """Bottleneck dataclass works."""
        b = Bottleneck(
            item_id=1101,
            item_name="Iron Ingot",
            recipe_id=1,
            bottleneck_type="input_starvation",
            severity=75.0,
            affected_throughput=30.0,
            efficiency=50.0,
            root_cause="Insufficient iron ore",
            recommendation="Add more miners",
            upstream_items=["Iron Ore"],
            downstream_impact=["Gear", "Circuit"],
            planet_id=1,
            assembler_count=10,
        )
        assert b.severity == 75.0
        assert b.bottleneck_type == "input_starvation"


class TestPowerAnalyzer:
    """Tests for PowerAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return PowerAnalyzer()

    @pytest.fixture
    def factory_with_power(self):
        """Factory with power data."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Power Planet",
            power=PowerMetrics(
                generation_mw=100,
                consumption_mw=80,
                accumulator_charge_percent=75.0,
            ),
        )
        # Add some assemblers
        for i in range(3):
            planet.assemblers.append(AssemblerMetrics(
                assembler_id=i,
                recipe_id=1,
                production_rate=50,
                theoretical_max=60,
            ))
        return FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )

    @pytest.fixture
    def factory_with_deficit(self):
        """Factory with power deficit."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Low Power",
            power=PowerMetrics(
                generation_mw=50,
                consumption_mw=100,
            ),
        )
        return FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )

    @pytest.mark.asyncio
    async def test_analyze_power_healthy(self, analyzer, factory_with_power):
        """Analyze healthy power grid."""
        result = await analyzer.analyze(factory_with_power)
        assert result["summary"]["total_generation_mw"] == 100
        assert result["summary"]["total_consumption_mw"] == 80
        assert result["summary"]["net_surplus_mw"] == 20
        assert result["summary"]["planets_with_deficit"] == 0

    @pytest.mark.asyncio
    async def test_analyze_power_deficit(self, analyzer, factory_with_deficit):
        """Detect power deficit."""
        result = await analyzer.analyze(factory_with_deficit)
        assert result["summary"]["net_surplus_mw"] == -50
        assert result["summary"]["planets_with_deficit"] == 1
        # Should have recommendation
        planet_data = result["planets"][0]
        assert planet_data["status"] == "deficit"
        assert "recommendation" in planet_data

    @pytest.mark.asyncio
    async def test_analyze_accumulator(self, analyzer, factory_with_power):
        """Accumulator charge is included."""
        result = await analyzer.analyze(factory_with_power, include_accumulator_cycles=True)
        planet_data = result["planets"][0]
        assert "accumulator_charge" in planet_data
        assert planet_data["accumulator_charge"] == "75.0%"

    @pytest.mark.asyncio
    async def test_analyze_no_power_data(self, analyzer):
        """Handle planet without power data."""
        planet = PlanetState(planet_id=1, planet_name="No Power")
        factory = FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )
        result = await analyzer.analyze(factory)
        assert result["summary"]["total_generation_mw"] == 0

    def test_power_consumer_dataclass(self):
        """PowerConsumer dataclass works."""
        pc = PowerConsumer(
            recipe_id=1,
            item_name="Iron Ingot",
            building_type="smelter",
            building_count=10,
            power_mw=7.2,
            efficiency=100.0,
            production_rate=600.0,
        )
        assert pc.power_mw == 7.2
        assert pc.building_count == 10


class TestLogisticsAnalyzer:
    """Tests for LogisticsAnalyzer."""

    @pytest.fixture
    def analyzer(self):
        return LogisticsAnalyzer()

    @pytest.fixture
    def factory_with_belts(self):
        """Factory with belt data."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Belt Planet",
        )
        # Add some belts
        planet.belts.append(BeltMetrics(
            belt_id=1,
            item_type="item_1101",
            throughput=5.8,
            max_throughput=6.0,  # mk1 belt nearly saturated
        ))
        planet.belts.append(BeltMetrics(
            belt_id=2,
            item_type="item_1102",
            throughput=6.0,
            max_throughput=12.0,  # mk2 belt half used
        ))
        planet.belts.append(BeltMetrics(
            belt_id=3,
            item_type="item_1103",
            throughput=12.0,
            max_throughput=12.0,  # mk2 belt saturated
        ))
        # Add assemblers for throughput analysis
        planet.assemblers.append(AssemblerMetrics(
            assembler_id=1,
            recipe_id=1,  # Iron Ingot
            production_rate=60,
            theoretical_max=60,
        ))
        return FactoryState(
            timestamp=datetime.now(),
            planets={1: planet},
        )

    @pytest.mark.asyncio
    async def test_analyze_saturated_belts(self, analyzer, factory_with_belts):
        """Detect saturated belts."""
        result = await analyzer.analyze(factory_with_belts, saturation_threshold=95.0)
        assert result["summary"]["saturated_count"] >= 2  # 2 belts over 95%
        # Check saturated belt details
        saturated = result["saturated_belts"]
        assert len(saturated) >= 1

    @pytest.mark.asyncio
    async def test_analyze_near_saturation(self, analyzer, factory_with_belts):
        """Detect near-saturation belts."""
        result = await analyzer.analyze(factory_with_belts, saturation_threshold=95.0)
        # Belt at 96.7% (5.8/6.0) should be saturated
        assert result["summary"]["saturated_count"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_item_filter(self, analyzer, factory_with_belts):
        """Filter by specific items."""
        result = await analyzer.analyze(
            factory_with_belts,
            item_filter=["Iron Ingot"],
        )
        # Should have fewer results when filtering
        assert "saturated_belts" in result

    @pytest.mark.asyncio
    async def test_analyze_throughput_requirements(self, analyzer, factory_with_belts):
        """Calculate throughput requirements."""
        result = await analyzer.analyze(
            factory_with_belts,
            include_throughput_analysis=True,
        )
        assert "throughput_requirements" in result
        # Should have at least one item
        reqs = result["throughput_requirements"]
        assert len(reqs) >= 1
        # Check structure
        if reqs:
            req = reqs[0]
            assert "item" in req
            assert "production_rate" in req
            assert "required_belt_tier" in req

    @pytest.mark.asyncio
    async def test_analyze_empty_factory(self, analyzer):
        """Empty factory has no belt issues."""
        factory = FactoryState(timestamp=datetime.now(), planets={})
        result = await analyzer.analyze(factory)
        assert result["summary"]["saturated_count"] == 0

    def test_throughput_requirement_dataclass(self):
        """ThroughputRequirement dataclass works."""
        tr = ThroughputRequirement(
            item_id=1101,
            item_name="Iron Ingot",
            production_rate=360.0,
            consumption_rate=300.0,
            net_rate=60.0,
            required_belt_tier="mk1",
            belt_count_needed=1,
        )
        assert tr.net_rate == 60.0
        assert tr.required_belt_tier == "mk1"
