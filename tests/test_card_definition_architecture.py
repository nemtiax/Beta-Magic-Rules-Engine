import ast
from pathlib import Path
import unittest

from beta_magic import ALL_CARDS
from beta_magic.card_defs import (
    ARTIFACT_CARDS,
    BLACK_CARDS,
    BLUE_CARDS,
    GREEN_CARDS,
    LAND_CARDS,
    RED_CARDS,
    WHITE_CARDS,
)


PACKAGE_ROOT = Path(__file__).parents[1] / "beta_magic"
DEFINITION_FILES = {
    "artifacts.py",
    "black.py",
    "blue.py",
    "green.py",
    "lands.py",
    "red.py",
    "shared.py",
    "white.py",
}


class CardDefinitionArchitectureTests(unittest.TestCase):
    def test_every_card_belongs_to_exactly_one_registry_group(self) -> None:
        grouped = (
            WHITE_CARDS
            + BLUE_CARDS
            + BLACK_CARDS
            + RED_CARDS
            + GREEN_CARDS
            + ARTIFACT_CARDS
            + LAND_CARDS
        )
        self.assertEqual(len(grouped), 240)
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(grouped), set(ALL_CARDS))

    def test_card_definitions_only_live_in_printed_characteristic_files(
        self,
    ) -> None:
        files_with_definitions: set[str] = set()
        for path in PACKAGE_ROOT.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "CardDefinition"
                for node in ast.walk(tree)
            ):
                self.assertEqual(path.parent.name, "card_defs")
                files_with_definitions.add(path.name)
        self.assertEqual(files_with_definitions, DEFINITION_FILES)

    def test_legacy_catalog_intake_is_gone(self) -> None:
        self.assertFalse((PACKAGE_ROOT / "card_defs" / "_legacy.py").exists())


if __name__ == "__main__":
    unittest.main()
