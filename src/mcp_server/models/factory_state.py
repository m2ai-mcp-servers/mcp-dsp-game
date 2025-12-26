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
        """
        Construct FactoryState from real-time plugin data.

        The C# plugin sends JSON with lowercase property names (via Newtonsoft.Json).
        Example structure:
        {
            "timestamp": 1234567890,
            "gameTick": 12345,
            "planets": {
                "1": {
                    "planetId": 1,
                    "planetName": "Planet Name",
                    "power": { ... },
                    "production": [ ... ],
                    "belts": [ ... ]
                }
            }
        }
        """
        planets: Dict[int, PlanetState] = {}

        # Handle both "planets" (new C# format) and "Planets" (legacy)
        planets_data = data.get("planets", data.get("Planets", {}))

        for planet_id_str, planet_data in planets_data.items():
            planet_id = int(planet_id_str)
            planet_state = PlanetState(
                planet_id=planet_id,
                planet_name=planet_data.get("planetName", planet_data.get("PlanetName", ""))
            )

            # Parse power metrics (new C# format uses lowercase)
            power_data = planet_data.get("power", planet_data.get("Power"))
            if power_data:
                # C# sends both raw energy per tick AND calculated MW values
                # Prefer the calculated MW values if available
                generation_mw = power_data.get("generationMW", power_data.get("GenerationMW", 0))
                consumption_mw = power_data.get("consumptionMW", power_data.get("ConsumptionMW", 0))
                acc_percent = power_data.get("accumulatorPercent", power_data.get("AccumulatorPercent", 0))

                planet_state.power = PowerMetrics(
                    generation_mw=generation_mw,
                    consumption_mw=consumption_mw,
                    accumulator_charge_percent=acc_percent,
                )

            # Parse production metrics (new C# format)
            production_list = planet_data.get("production", planet_data.get("Production", []))
            for prod in production_list:
                # Map recipeId/protoId to item name (TODO: use recipe database)
                recipe_id = prod.get("recipeId", prod.get("RecipeId", 0))
                proto_id = prod.get("protoId", prod.get("ProtoId", 0))
                item_name = f"recipe_{recipe_id}" if recipe_id > 0 else f"item_{proto_id}"

                # Check for legacy format with ItemName
                if "ItemName" in prod or "itemName" in prod:
                    item_name = prod.get("itemName", prod.get("ItemName", item_name))

                production_rate = prod.get("productionRate", prod.get("ProductionRate", 0))
                items_produced = prod.get("itemsProduced", prod.get("ItemsProduced", 0))

                # Handle legacy format with ConsumptionRate in Production list
                consumption_rate = prod.get("consumptionRate", prod.get("ConsumptionRate", 0))
                storage = prod.get("storage", prod.get("Storage", items_produced))

                # Store assembler-level metrics
                assembler_id = prod.get("assemblerId", prod.get("AssemblerId", 0))
                input_starved = prod.get("inputStarved", prod.get("InputStarved", False))
                output_blocked = prod.get("outputBlocked", prod.get("OutputBlocked", False))
                power_level = prod.get("powerLevel", prod.get("PowerLevel", 1.0))

                # Add to production dict (aggregate by item/recipe)
                if item_name not in planet_state.production:
                    planet_state.production[item_name] = ItemMetrics(
                        item_name=item_name,
                        production_rate=production_rate,
                        consumption_rate=consumption_rate,
                        current_storage=storage,
                    )
                else:
                    # Aggregate production from multiple assemblers
                    existing = planet_state.production[item_name]
                    planet_state.production[item_name] = ItemMetrics(
                        item_name=item_name,
                        production_rate=existing.production_rate + production_rate,
                        consumption_rate=existing.consumption_rate + consumption_rate,
                        current_storage=existing.current_storage + storage,
                    )

                # Store assembler metrics
                if assembler_id > 0:
                    planet_state.assemblers.append(AssemblerMetrics(
                        assembler_id=assembler_id,
                        recipe_id=recipe_id,
                        production_rate=production_rate,
                        theoretical_max=0,  # TODO: Get from recipe database
                        input_starved=input_starved,
                        output_blocked=output_blocked,
                    ))

            # Parse belt metrics (new C# format)
            belts_list = planet_data.get("belts", planet_data.get("Belts", []))
            for belt in belts_list:
                belt_id = belt.get("beltId", belt.get("BeltId", 0))
                item_type = belt.get("itemType", belt.get("ItemType", 0))
                throughput = belt.get("throughput", belt.get("Throughput", 0))
                max_throughput = belt.get("maxThroughput", belt.get("MaxThroughput", 30))

                if belt_id > 0:
                    planet_state.belts.append(BeltMetrics(
                        belt_id=belt_id,
                        item_type=f"item_{item_type}",  # TODO: Map to item name
                        throughput=throughput,
                        max_throughput=max_throughput,
                    ))

            planets[planet_id] = planet_state

        # Handle timestamp (lowercase from C#, uppercase from legacy)
        timestamp_val = data.get("timestamp", data.get("Timestamp", 0))
        if isinstance(timestamp_val, (int, float)) and timestamp_val > 0:
            timestamp = datetime.fromtimestamp(timestamp_val)
        else:
            timestamp = datetime.now()

        return cls(
            timestamp=timestamp,
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
