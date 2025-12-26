"""Tests for FactoryState data models."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.models.factory_state import (
    FactoryState,
    PlanetState,
    ItemMetrics,
    AssemblerMetrics,
    PowerMetrics,
    BeltMetrics,
    ENERGY_PER_TICK_TO_MW,
)


class TestItemMetrics:
    """Tests for ItemMetrics dataclass."""

    def test_net_rate_calculation(self):
        """Net rate should be production minus consumption."""
        metrics = ItemMetrics(
            item_name="iron-ingot",
            production_rate=100.0,
            consumption_rate=60.0,
            current_storage=500,
        )
        assert metrics.net_rate == 40.0

    def test_negative_net_rate(self):
        """Net rate can be negative when consumption exceeds production."""
        metrics = ItemMetrics(
            item_name="copper-ingot",
            production_rate=30.0,
            consumption_rate=50.0,
            current_storage=100,
        )
        assert metrics.net_rate == -20.0


class TestAssemblerMetrics:
    """Tests for AssemblerMetrics dataclass."""

    def test_efficiency_calculation(self):
        """Efficiency should be actual/theoretical * 100."""
        metrics = AssemblerMetrics(
            assembler_id=1,
            recipe_id=10,
            production_rate=45.0,
            theoretical_max=60.0,
        )
        assert metrics.efficiency == 75.0

    def test_efficiency_zero_theoretical(self):
        """Efficiency should be 0 when theoretical_max is 0."""
        metrics = AssemblerMetrics(
            assembler_id=1,
            recipe_id=10,
            production_rate=45.0,
            theoretical_max=0.0,
        )
        assert metrics.efficiency == 0.0

    def test_input_starved_flag(self):
        """Input starved flag should be stored correctly."""
        metrics = AssemblerMetrics(
            assembler_id=1,
            recipe_id=10,
            production_rate=30.0,
            theoretical_max=60.0,
            input_starved=True,
        )
        assert metrics.input_starved is True
        assert metrics.efficiency == 50.0


class TestPowerMetrics:
    """Tests for PowerMetrics dataclass."""

    def test_surplus_calculation(self):
        """Surplus should be generation minus consumption."""
        metrics = PowerMetrics(
            generation_mw=100.0,
            consumption_mw=80.0,
        )
        assert metrics.surplus_mw == 20.0

    def test_deficit_calculation(self):
        """Surplus can be negative (deficit)."""
        metrics = PowerMetrics(
            generation_mw=50.0,
            consumption_mw=75.0,
        )
        assert metrics.surplus_mw == -25.0

    def test_accumulator_charge(self):
        """Accumulator charge percent should be stored."""
        metrics = PowerMetrics(
            generation_mw=100.0,
            consumption_mw=80.0,
            accumulator_charge_percent=75.5,
        )
        assert metrics.accumulator_charge_percent == 75.5


class TestBeltMetrics:
    """Tests for BeltMetrics dataclass."""

    def test_saturation_calculation(self):
        """Saturation should be throughput/max * 100."""
        metrics = BeltMetrics(
            belt_id=1,
            item_type="iron-ore",
            throughput=27.0,
            max_throughput=30.0,
        )
        assert metrics.saturation_percent == 90.0

    def test_saturation_zero_max(self):
        """Saturation should be 0 when max is 0."""
        metrics = BeltMetrics(
            belt_id=1,
            item_type="iron-ore",
            throughput=10.0,
            max_throughput=0.0,
        )
        assert metrics.saturation_percent == 0.0


class TestPlanetState:
    """Tests for PlanetState dataclass."""

    def test_empty_planet(self):
        """Planet can be created with minimal data."""
        planet = PlanetState(planet_id=1)
        assert planet.planet_id == 1
        assert planet.planet_name == ""
        assert planet.production == {}
        assert planet.assemblers == []
        assert planet.power is None
        assert planet.belts == []

    def test_planet_with_data(self):
        """Planet can hold production and power data."""
        planet = PlanetState(
            planet_id=1,
            planet_name="Starter Planet",
            power=PowerMetrics(generation_mw=100, consumption_mw=50),
        )
        assert planet.planet_name == "Starter Planet"
        assert planet.power.surplus_mw == 50.0


class TestFactoryState:
    """Tests for FactoryState dataclass."""

    def test_empty_factory(self):
        """Factory can be created empty."""
        state = FactoryState(timestamp=datetime.now())
        assert len(state.planets) == 0

    def test_from_realtime_data_empty(self):
        """from_realtime_data handles empty data."""
        state = FactoryState.from_realtime_data({})
        assert len(state.planets) == 0

    def test_from_realtime_data_with_planets(self):
        """from_realtime_data parses planet data."""
        data = {
            "Timestamp": 1703520000,
            "Planets": {
                "1": {
                    "Power": {
                        "GenerationMW": 100.0,
                        "ConsumptionMW": 80.0,
                        "AccumulatorPercent": 50.0,
                    },
                    "Production": [
                        {
                            "ItemName": "iron-ingot",
                            "ProductionRate": 120.0,
                            "ConsumptionRate": 60.0,
                            "Storage": 500,
                        }
                    ],
                }
            },
        }
        state = FactoryState.from_realtime_data(data)

        assert len(state.planets) == 1
        assert 1 in state.planets

        planet = state.planets[1]
        assert planet.power is not None
        assert planet.power.generation_mw == 100.0
        assert planet.power.surplus_mw == 20.0

        assert "iron-ingot" in planet.production
        assert planet.production["iron-ingot"].net_rate == 60.0


class TestFactoryStateFromSaveData:
    """Tests for FactoryState.from_save_data()."""

    def test_from_save_data_with_mock(self):
        """from_save_data extracts data from GameSave-like object."""
        # Create mock GameSave structure
        mock_generator = MagicMock()
        mock_generator.id = 1
        mock_generator.genEnergyPerTick = 1000000  # ~60 MW

        mock_consumer = MagicMock()
        mock_consumer.id = 1
        mock_consumer.workEnergyPerTick = 500000  # ~30 MW

        mock_power_system = MagicMock()
        mock_power_system.genPool = [mock_generator]
        mock_power_system.consumerPool = [mock_consumer]
        mock_power_system.accPool = []

        mock_factory = MagicMock()
        mock_factory.planetId = 1
        mock_factory.powerSystem = mock_power_system
        mock_factory.factorySystem = MagicMock(assemblerPool=[])

        mock_game_data = MagicMock()
        mock_game_data.factories = [mock_factory]
        mock_game_data.statistics = None

        mock_game_save = MagicMock()
        mock_game_save.gameData = mock_game_data

        # Parse
        state = FactoryState.from_save_data(mock_game_save)

        # Verify
        assert len(state.planets) == 1
        assert 1 in state.planets

        planet = state.planets[1]
        assert planet.power is not None
        # 1000000 * 60 / 1000000 = 60 MW generation
        assert planet.power.generation_mw == pytest.approx(60.0, rel=0.01)
        # 500000 * 60 / 1000000 = 30 MW consumption
        assert planet.power.consumption_mw == pytest.approx(30.0, rel=0.01)
        assert planet.power.surplus_mw == pytest.approx(30.0, rel=0.01)

    def test_from_save_data_handles_missing_attributes(self):
        """from_save_data handles GameSave with missing optional attributes."""
        mock_game_data = MagicMock()
        mock_game_data.factories = []

        mock_game_save = MagicMock()
        mock_game_save.gameData = mock_game_data

        state = FactoryState.from_save_data(mock_game_save)
        assert len(state.planets) == 0
