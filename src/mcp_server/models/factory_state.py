"""Data models for factory state representation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Energy conversion: DSP uses energy per tick, 60 ticks = 1 second
# 1 MW = 1,000,000 J/s = 1,000,000 / 60 J/tick ≈ 16,666.67 J/tick
ENERGY_PER_TICK_TO_MW = 60 / 1_000_000


@dataclass
class ItemMetrics:
    """Production metrics for a specific item."""

    item_name: str
    production_rate: float  # items/min
    consumption_rate: float  # items/min
    current_storage: int
    net_rate: float = field(init=False)

    def __post_init__(self) -> None:
        self.net_rate = self.production_rate - self.consumption_rate


@dataclass
class AssemblerMetrics:
    """Metrics for individual assembler/smelter."""

    assembler_id: int
    recipe_id: int
    production_rate: float
    theoretical_max: float
    input_starved: bool = False
    output_blocked: bool = False
    efficiency: float = field(init=False)

    def __post_init__(self) -> None:
        self.efficiency = (
            (self.production_rate / self.theoretical_max * 100)
            if self.theoretical_max > 0
            else 0
        )


@dataclass
class PowerMetrics:
    """Power grid metrics for a planet."""

    generation_mw: float
    consumption_mw: float
    accumulator_charge_percent: float = 0.0
    surplus_mw: float = field(init=False)

    def __post_init__(self) -> None:
        self.surplus_mw = self.generation_mw - self.consumption_mw


@dataclass
class BeltMetrics:
    """Belt throughput metrics."""

    belt_id: int
    item_type: str
    throughput: float  # items/sec
    max_throughput: float  # items/sec (based on tier)
    saturation_percent: float = field(init=False)

    def __post_init__(self) -> None:
        self.saturation_percent = (
            (self.throughput / self.max_throughput * 100) if self.max_throughput > 0 else 0
        )


@dataclass
class PlanetState:
    """Complete state for a single planet."""

    planet_id: int
    planet_name: str = ""
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
    def from_realtime_data(cls, data: dict) -> "FactoryState":
        """Construct FactoryState from real-time plugin data."""
        planets: Dict[int, PlanetState] = {}

        for planet_id_str, planet_data in data.get("Planets", {}).items():
            planet_id = int(planet_id_str)
            planet_state = PlanetState(planet_id=planet_id)

            # Parse power metrics
            if "Power" in planet_data:
                power_data = planet_data["Power"]
                planet_state.power = PowerMetrics(
                    generation_mw=power_data.get("GenerationMW", 0),
                    consumption_mw=power_data.get("ConsumptionMW", 0),
                    accumulator_charge_percent=power_data.get("AccumulatorPercent", 0),
                )

            # Parse production metrics
            for prod in planet_data.get("Production", []):
                item_name = prod.get("ItemName", "unknown")
                planet_state.production[item_name] = ItemMetrics(
                    item_name=item_name,
                    production_rate=prod.get("ProductionRate", 0),
                    consumption_rate=prod.get("ConsumptionRate", 0),
                    current_storage=prod.get("Storage", 0),
                )

            planets[planet_id] = planet_state

        return cls(
            timestamp=datetime.fromtimestamp(data.get("Timestamp", 0)),
            planets=planets,
        )

    @classmethod
    def from_save_data(cls, game_save: Any) -> "FactoryState":
        """
        Construct FactoryState from parsed GameSave object.

        Args:
            game_save: GameSave object from dsp_save_parser

        Returns:
            FactoryState with extracted factory data
        """
        planets: Dict[int, PlanetState] = {}

        try:
            game_data = game_save.gameData
            factories = game_data.factories if hasattr(game_data, 'factories') else []

            for factory in factories:
                if not hasattr(factory, 'planetId'):
                    continue

                planet_id = int(factory.planetId)
                planet_state = PlanetState(planet_id=planet_id)

                # Extract power metrics
                if hasattr(factory, 'powerSystem'):
                    planet_state.power = cls._extract_power_metrics(factory.powerSystem)

                # Extract assembler metrics
                if hasattr(factory, 'factorySystem'):
                    planet_state.assemblers = cls._extract_assembler_metrics(
                        factory.factorySystem
                    )

                planets[planet_id] = planet_state
                logger.debug(f"Processed planet {planet_id}")

            # Extract production statistics if available
            if hasattr(game_data, 'statistics'):
                cls._merge_production_stats(planets, game_data.statistics)

        except Exception as e:
            logger.error(f"Error parsing save data: {e}")
            raise

        return cls(
            timestamp=datetime.now(),
            planets=planets,
        )

    @staticmethod
    def _extract_power_metrics(power_system: Any) -> PowerMetrics:
        """Extract power metrics from PowerSystem."""
        total_generation = 0.0
        total_consumption = 0.0
        accumulator_current = 0
        accumulator_max = 0

        # Sum up generator output
        if hasattr(power_system, 'genPool'):
            for gen in power_system.genPool:
                if hasattr(gen, 'genEnergyPerTick') and hasattr(gen, 'id') and gen.id > 0:
                    total_generation += float(gen.genEnergyPerTick)

        # Sum up consumer demand
        if hasattr(power_system, 'consumerPool'):
            for consumer in power_system.consumerPool:
                if hasattr(consumer, 'workEnergyPerTick') and hasattr(consumer, 'id') and consumer.id > 0:
                    total_consumption += float(consumer.workEnergyPerTick)

        # Sum up accumulator charge
        if hasattr(power_system, 'accPool'):
            for acc in power_system.accPool:
                if hasattr(acc, 'curEnergy') and hasattr(acc, 'maxEnergy') and hasattr(acc, 'id') and acc.id > 0:
                    accumulator_current += int(acc.curEnergy)
                    accumulator_max += int(acc.maxEnergy)

        # Convert to MW
        generation_mw = total_generation * ENERGY_PER_TICK_TO_MW
        consumption_mw = total_consumption * ENERGY_PER_TICK_TO_MW

        # Calculate accumulator percentage
        acc_percent = (accumulator_current / accumulator_max * 100) if accumulator_max > 0 else 0.0

        return PowerMetrics(
            generation_mw=generation_mw,
            consumption_mw=consumption_mw,
            accumulator_charge_percent=acc_percent,
        )

    @staticmethod
    def _extract_assembler_metrics(factory_system: Any) -> List[AssemblerMetrics]:
        """Extract assembler metrics from FactorySystem."""
        assemblers: List[AssemblerMetrics] = []

        if not hasattr(factory_system, 'assemblerPool'):
            return assemblers

        for assembler in factory_system.assemblerPool:
            if not hasattr(assembler, 'id') or assembler.id <= 0:
                continue
            if not hasattr(assembler, 'recipeId') or assembler.recipeId <= 0:
                continue

            # Calculate production rate from speed and time
            # Note: Actual rate calculation needs recipe database
            # For now, we store the raw values
            assemblers.append(AssemblerMetrics(
                assembler_id=int(assembler.id),
                recipe_id=int(assembler.recipeId),
                production_rate=0.0,  # TODO: Calculate from recipe database
                theoretical_max=0.0,   # TODO: Get from recipe database
                input_starved=False,   # TODO: Detect from input buffer state
                output_blocked=False,  # TODO: Detect from output buffer state
            ))

        return assemblers

    @staticmethod
    def _merge_production_stats(
        planets: Dict[int, "PlanetState"],
        statistics: Any,
    ) -> None:
        """Merge production statistics into planet states."""
        # The statistics object contains FactoryProductionStat per factory
        # This provides historical production/consumption data
        # TODO: Implement full statistics integration
        pass
