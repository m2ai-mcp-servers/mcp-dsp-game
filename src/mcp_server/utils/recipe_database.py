"""Recipe database for DSP production calculations and dependency analysis."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Path to shared data files
SHARED_DIR = Path(__file__).parent.parent.parent / "shared"


@dataclass
class RecipeInput:
    """Input requirement for a recipe."""
    item_id: int
    count: int
    item_name: str = ""


@dataclass
class RecipeOutput:
    """Output product from a recipe."""
    item_id: int
    count: int
    item_name: str = ""


@dataclass
class Recipe:
    """Complete recipe definition."""
    id: int
    name: str
    outputs: List[RecipeOutput]
    inputs: List[RecipeInput]
    time: float  # seconds per cycle
    building: str  # smelter, assembler, chemical, etc.

    @property
    def primary_output(self) -> RecipeOutput:
        """Get the primary (first) output item."""
        return self.outputs[0] if self.outputs else RecipeOutput(0, 0)

    @property
    def primary_output_id(self) -> int:
        """Get the primary output item ID."""
        return self.primary_output.item_id

    def items_per_minute(self, building_speed: float = 1.0) -> float:
        """Calculate items per minute at given building speed."""
        if self.time <= 0:
            return 0
        cycles_per_minute = 60.0 / self.time * building_speed
        return cycles_per_minute * self.primary_output.count

    def input_requirements_per_minute(self, building_speed: float = 1.0) -> Dict[int, float]:
        """Calculate input requirements per minute."""
        if self.time <= 0:
            return {}
        cycles_per_minute = 60.0 / self.time * building_speed
        return {inp.item_id: inp.count * cycles_per_minute for inp in self.inputs}


@dataclass
class DependencyNode:
    """Node in the production dependency graph."""
    item_id: int
    item_name: str
    recipe_id: Optional[int] = None
    is_raw_resource: bool = False
    dependencies: List["DependencyNode"] = field(default_factory=list)
    dependents: List["DependencyNode"] = field(default_factory=list)


class RecipeDatabase:
    """
    Database of DSP recipes and items for production analysis.

    Provides:
    - Item ID to name lookup
    - Recipe ID to recipe details
    - Dependency graph construction
    - Production rate calculations
    """

    def __init__(self) -> None:
        self._items: Dict[int, str] = {}  # item_id -> item_name
        self._items_by_name: Dict[str, int] = {}  # item_name -> item_id
        self._recipes: Dict[int, Recipe] = {}  # recipe_id -> Recipe
        self._recipes_by_output: Dict[int, List[int]] = {}  # item_id -> [recipe_ids]
        self._building_speeds: Dict[str, Dict[str, float]] = {}
        self._loaded = False

    def load(self) -> None:
        """Load item and recipe data from JSON files."""
        if self._loaded:
            return

        try:
            self._load_items()
            self._load_recipes()
            self._loaded = True
            logger.info(f"Recipe database loaded: {len(self._items)} items, "
                       f"{len(self._recipes)} recipes")
        except Exception as e:
            logger.error(f"Failed to load recipe database: {e}")
            raise

    def _load_items(self) -> None:
        """Load item ID mappings."""
        items_path = SHARED_DIR / "item_ids.json"
        if not items_path.exists():
            logger.warning(f"Item IDs file not found: {items_path}")
            return

        with open(items_path, "r") as f:
            data = json.load(f)

        # Flatten all categories
        for category, items in data.items():
            if category.startswith("_"):
                continue
            if isinstance(items, dict):
                for item_id_str, item_name in items.items():
                    item_id = int(item_id_str)
                    self._items[item_id] = item_name
                    self._items_by_name[item_name] = item_id

    def _load_recipes(self) -> None:
        """Load recipe definitions."""
        recipes_path = SHARED_DIR / "recipes.json"
        if not recipes_path.exists():
            logger.warning(f"Recipes file not found: {recipes_path}")
            return

        with open(recipes_path, "r") as f:
            data = json.load(f)

        # Load building speeds
        self._building_speeds = data.get("building_speeds", {})

        # Load recipes
        for recipe_id_str, recipe_data in data.get("recipes", {}).items():
            recipe_id = int(recipe_id_str)

            # Use _items directly to avoid recursion (items loaded before recipes)
            outputs = [
                RecipeOutput(
                    item_id=out["item_id"],
                    count=out["count"],
                    item_name=self._items.get(out["item_id"], f"item_{out['item_id']}")
                )
                for out in recipe_data.get("outputs", [])
            ]

            inputs = [
                RecipeInput(
                    item_id=inp["item_id"],
                    count=inp["count"],
                    item_name=self._items.get(inp["item_id"], f"item_{inp['item_id']}")
                )
                for inp in recipe_data.get("inputs", [])
            ]

            recipe = Recipe(
                id=recipe_id,
                name=recipe_data.get("name", f"Recipe {recipe_id}"),
                outputs=outputs,
                inputs=inputs,
                time=recipe_data.get("time", 1.0),
                building=recipe_data.get("building", "assembler"),
            )

            self._recipes[recipe_id] = recipe

            # Index by output item
            for output in outputs:
                if output.item_id not in self._recipes_by_output:
                    self._recipes_by_output[output.item_id] = []
                self._recipes_by_output[output.item_id].append(recipe_id)

    def get_item_name(self, item_id: int) -> str:
        """Get item name from ID."""
        self.load()
        return self._items.get(item_id, f"item_{item_id}")

    def get_item_id(self, item_name: str) -> Optional[int]:
        """Get item ID from name."""
        self.load()
        return self._items_by_name.get(item_name)

    def get_recipe(self, recipe_id: int) -> Optional[Recipe]:
        """Get recipe by ID."""
        self.load()
        return self._recipes.get(recipe_id)

    def get_recipes_for_item(self, item_id: int) -> List[Recipe]:
        """Get all recipes that produce a given item."""
        self.load()
        recipe_ids = self._recipes_by_output.get(item_id, [])
        return [self._recipes[rid] for rid in recipe_ids if rid in self._recipes]

    def get_building_speed(self, building_type: str, tier: str = "mk2") -> float:
        """Get production speed multiplier for a building."""
        self.load()
        building_speeds = self._building_speeds.get(building_type, {})
        if isinstance(building_speeds, dict):
            return building_speeds.get(tier, 1.0)
        return 1.0

    def calculate_theoretical_rate(
        self,
        recipe_id: int,
        building_count: int = 1,
        building_tier: str = "mk2"
    ) -> float:
        """Calculate theoretical production rate in items/minute."""
        recipe = self.get_recipe(recipe_id)
        if not recipe:
            return 0.0

        speed = self.get_building_speed(recipe.building, building_tier)
        return recipe.items_per_minute(speed) * building_count

    def is_raw_resource(self, item_id: int) -> bool:
        """Check if an item is a raw resource (ore, water, oil, etc.)."""
        self.load()
        # Raw resources typically have IDs in the 1001-1031 range
        return 1001 <= item_id <= 1031

    def build_dependency_graph(
        self,
        target_item_id: int,
        max_depth: int = 10
    ) -> DependencyNode:
        """
        Build a dependency graph for producing a target item.

        Args:
            target_item_id: The item to produce
            max_depth: Maximum recursion depth

        Returns:
            Root DependencyNode for the target item
        """
        self.load()
        visited: Set[int] = set()
        return self._build_node(target_item_id, visited, max_depth)

    def _build_node(
        self,
        item_id: int,
        visited: Set[int],
        depth: int
    ) -> DependencyNode:
        """Recursively build dependency node."""
        item_name = self.get_item_name(item_id)

        node = DependencyNode(
            item_id=item_id,
            item_name=item_name,
            is_raw_resource=self.is_raw_resource(item_id)
        )

        # Stop conditions
        if item_id in visited or depth <= 0 or node.is_raw_resource:
            return node

        visited.add(item_id)

        # Find recipe to produce this item
        recipes = self.get_recipes_for_item(item_id)
        if recipes:
            recipe = recipes[0]  # Use first recipe (primary)
            node.recipe_id = recipe.id

            # Add dependencies for each input
            for inp in recipe.inputs:
                dep_node = self._build_node(inp.item_id, visited, depth - 1)
                node.dependencies.append(dep_node)
                dep_node.dependents.append(node)

        visited.discard(item_id)
        return node

    def trace_bottleneck_upstream(
        self,
        item_id: int,
        max_depth: int = 5
    ) -> List[Tuple[int, str, int]]:
        """
        Trace upstream dependencies to find potential bottleneck sources.

        Returns:
            List of (item_id, item_name, recipe_id) tuples in dependency order
        """
        self.load()
        result: List[Tuple[int, str, int]] = []
        visited: Set[int] = set()

        def trace(iid: int, depth: int) -> None:
            if iid in visited or depth <= 0:
                return
            visited.add(iid)

            recipes = self.get_recipes_for_item(iid)
            if recipes:
                recipe = recipes[0]
                result.append((iid, self.get_item_name(iid), recipe.id))

                for inp in recipe.inputs:
                    if not self.is_raw_resource(inp.item_id):
                        trace(inp.item_id, depth - 1)

        trace(item_id, max_depth)
        return result

    def trace_bottleneck_downstream(
        self,
        item_id: int,
        max_depth: int = 5
    ) -> List[Tuple[int, str]]:
        """
        Trace downstream to find what products are affected by this item.

        Returns:
            List of (item_id, item_name) tuples that use this item
        """
        self.load()
        result: List[Tuple[int, str]] = []
        visited: Set[int] = set()

        def trace(iid: int, depth: int) -> None:
            if iid in visited or depth <= 0:
                return
            visited.add(iid)

            # Find recipes that use this item as input
            for recipe in self._recipes.values():
                for inp in recipe.inputs:
                    if inp.item_id == iid:
                        output_id = recipe.primary_output_id
                        if output_id not in visited:
                            result.append((output_id, self.get_item_name(output_id)))
                            trace(output_id, depth - 1)

        trace(item_id, max_depth)
        return result

    def get_production_chain(
        self,
        target_item_id: int
    ) -> Dict[str, Any]:
        """
        Get complete production chain for an item.

        Returns:
            Dict with production chain details
        """
        self.load()
        chain: Dict[str, Any] = {
            "target": {
                "item_id": target_item_id,
                "item_name": self.get_item_name(target_item_id)
            },
            "steps": [],
            "raw_resources": []
        }

        visited: Set[int] = set()
        raw_resources: Set[int] = set()

        def process(iid: int, level: int) -> None:
            if iid in visited:
                return
            visited.add(iid)

            if self.is_raw_resource(iid):
                raw_resources.add(iid)
                return

            recipes = self.get_recipes_for_item(iid)
            if recipes:
                recipe = recipes[0]
                chain["steps"].append({
                    "level": level,
                    "item_id": iid,
                    "item_name": self.get_item_name(iid),
                    "recipe_id": recipe.id,
                    "recipe_name": recipe.name,
                    "building": recipe.building,
                    "time": recipe.time,
                    "inputs": [
                        {
                            "item_id": inp.item_id,
                            "item_name": inp.item_name,
                            "count": inp.count
                        }
                        for inp in recipe.inputs
                    ]
                })

                for inp in recipe.inputs:
                    process(inp.item_id, level + 1)

        process(target_item_id, 0)

        chain["raw_resources"] = [
            {"item_id": rid, "item_name": self.get_item_name(rid)}
            for rid in raw_resources
        ]

        return chain


# Singleton instance
_database: Optional[RecipeDatabase] = None


def get_recipe_database() -> RecipeDatabase:
    """Get the singleton recipe database instance."""
    global _database
    if _database is None:
        _database = RecipeDatabase()
        _database.load()
    return _database
