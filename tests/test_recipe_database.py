"""Tests for RecipeDatabase."""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server.utils import recipe_database
from mcp_server.utils.recipe_database import (
    RecipeDatabase,
    Recipe,
    RecipeInput,
    RecipeOutput,
    DependencyNode,
    get_recipe_database,
)


@pytest.fixture(autouse=True)
def reset_database_singleton():
    """Reset the singleton database between tests."""
    recipe_database._database = None
    yield
    recipe_database._database = None


class TestRecipeDatabase:
    """Tests for RecipeDatabase class."""

    def test_singleton_instance(self):
        """get_recipe_database returns singleton."""
        db1 = get_recipe_database()
        db2 = get_recipe_database()
        assert db1 is db2

    def test_load_items(self):
        """Database loads item IDs."""
        db = get_recipe_database()
        # Iron Ore should exist (using actual format from item_ids.json)
        assert db.get_item_name(1001) == "iron-ore"
        # Copper Ore
        assert db.get_item_name(1002) == "copper-ore"

    def test_load_recipes(self):
        """Database loads recipes."""
        db = get_recipe_database()
        # Iron Ingot recipe (ID 1)
        recipe = db.get_recipe(1)
        assert recipe is not None
        assert recipe.name == "Iron Ingot"
        assert recipe.building == "smelter"

    def test_get_item_name_unknown(self):
        """Unknown item returns placeholder name."""
        db = get_recipe_database()
        name = db.get_item_name(99999)
        assert name == "item_99999"

    def test_get_item_id(self):
        """Can look up item ID by name."""
        db = get_recipe_database()
        iron_ore_id = db.get_item_id("iron-ore")
        assert iron_ore_id == 1001

    def test_get_item_id_unknown(self):
        """Unknown item name returns None."""
        db = get_recipe_database()
        assert db.get_item_id("Nonexistent Item") is None

    def test_get_recipe_unknown(self):
        """Unknown recipe returns None."""
        db = get_recipe_database()
        assert db.get_recipe(99999) is None

    def test_recipe_primary_output(self):
        """Recipe has primary output."""
        db = get_recipe_database()
        recipe = db.get_recipe(1)  # Iron Ingot
        assert recipe is not None
        assert recipe.primary_output_id == 1101  # Iron Ingot item ID

    def test_recipe_items_per_minute(self):
        """Recipe calculates items per minute."""
        db = get_recipe_database()
        recipe = db.get_recipe(1)  # Iron Ingot, 1s cycle
        assert recipe is not None
        # 60 seconds / 1 second per cycle = 60 items per minute
        assert recipe.items_per_minute(1.0) == 60.0

    def test_recipe_input_requirements(self):
        """Recipe calculates input requirements."""
        db = get_recipe_database()
        recipe = db.get_recipe(1)  # Iron Ingot
        assert recipe is not None
        reqs = recipe.input_requirements_per_minute(1.0)
        # Should require Iron Ore (1001)
        assert 1001 in reqs
        assert reqs[1001] == 60.0  # 60 iron ore per minute

    def test_get_recipes_for_item(self):
        """Can find recipes that produce an item."""
        db = get_recipe_database()
        # Iron Ingot (1101)
        recipes = db.get_recipes_for_item(1101)
        assert len(recipes) >= 1
        assert recipes[0].name == "Iron Ingot"

    def test_is_raw_resource(self):
        """Raw resources are identified correctly."""
        db = get_recipe_database()
        # Iron Ore is raw (1001-1031 range)
        assert db.is_raw_resource(1001) is True
        # Iron Ingot is not raw
        assert db.is_raw_resource(1101) is False

    def test_calculate_theoretical_rate(self):
        """Theoretical production rate calculated correctly."""
        db = get_recipe_database()
        # 1 smelter making iron ingots
        rate = db.calculate_theoretical_rate(1, building_count=1)
        assert rate > 0
        # 2 smelters should double the rate
        rate2 = db.calculate_theoretical_rate(1, building_count=2)
        assert rate2 == rate * 2


class TestDependencyGraph:
    """Tests for dependency graph building."""

    def test_build_dependency_graph_simple(self):
        """Build graph for simple item."""
        db = get_recipe_database()
        # Iron Ingot depends on Iron Ore
        node = db.build_dependency_graph(1101, max_depth=2)
        assert node.item_id == 1101
        assert node.item_name == "iron-ingot"
        assert len(node.dependencies) == 1
        assert node.dependencies[0].item_id == 1001  # Iron Ore

    def test_build_dependency_graph_raw_resource(self):
        """Raw resource has no dependencies."""
        db = get_recipe_database()
        node = db.build_dependency_graph(1001, max_depth=5)  # Iron Ore
        assert node.item_id == 1001
        assert node.is_raw_resource is True
        assert len(node.dependencies) == 0

    def test_trace_upstream(self):
        """Trace upstream dependencies."""
        db = get_recipe_database()
        # Trace upstream from Iron Ingot
        upstream = db.trace_bottleneck_upstream(1101, max_depth=2)
        assert len(upstream) >= 1
        # Should include Iron Ingot itself
        item_ids = [item_id for item_id, _, _ in upstream]
        assert 1101 in item_ids

    def test_trace_downstream(self):
        """Trace downstream dependents."""
        db = get_recipe_database()
        # Trace downstream from Iron Ingot
        downstream = db.trace_bottleneck_downstream(1101, max_depth=3)
        # Iron Ingot is used in many recipes (gears, circuits, etc.)
        assert len(downstream) >= 1

    def test_get_production_chain(self):
        """Get complete production chain."""
        db = get_recipe_database()
        chain = db.get_production_chain(1101)  # Iron Ingot
        assert "target" in chain
        assert chain["target"]["item_id"] == 1101
        assert "steps" in chain
        assert "raw_resources" in chain


class TestRecipeDataclasses:
    """Tests for Recipe dataclasses."""

    def test_recipe_input(self):
        """RecipeInput dataclass works."""
        inp = RecipeInput(item_id=1001, count=2, item_name="Iron Ore")
        assert inp.item_id == 1001
        assert inp.count == 2
        assert inp.item_name == "Iron Ore"

    def test_recipe_output(self):
        """RecipeOutput dataclass works."""
        out = RecipeOutput(item_id=1101, count=1, item_name="Iron Ingot")
        assert out.item_id == 1101
        assert out.count == 1

    def test_recipe_zero_time(self):
        """Recipe with zero time returns 0 rate."""
        recipe = Recipe(
            id=999,
            name="Test",
            outputs=[RecipeOutput(1, 1)],
            inputs=[],
            time=0,
            building="test",
        )
        assert recipe.items_per_minute() == 0
        assert recipe.input_requirements_per_minute() == {}

    def test_dependency_node(self):
        """DependencyNode dataclass works."""
        node = DependencyNode(
            item_id=1001,
            item_name="Iron Ore",
            is_raw_resource=True,
        )
        assert node.item_id == 1001
        assert node.is_raw_resource is True
        assert len(node.dependencies) == 0
        assert len(node.dependents) == 0
