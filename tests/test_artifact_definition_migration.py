import unittest

from beta_magic import CARDS_BY_NAME
from beta_magic.card_defs.artifacts import (
    ARTIFACT_CARDS,
    ARTIFACT_CREATURES,
    CLOCKWORK_BEAST,
    EVENT_LIFE_ARTIFACTS,
    LAND_EVENT_ARTIFACTS,
    JUGGERNAUT,
    LIVING_WALL,
    MANA_ARTIFACTS,
    OBSIANUS_GOLEM,
    TIMED_ARTIFACTS,
    TURN_ARTIFACTS,
    UNTAP_ARTIFACTS,
    UTILITY_ARTIFACTS,
)


class ArtifactDefinitionMigrationTests(unittest.TestCase):
    def test_artifact_creature_group_is_canonical(self) -> None:
        self.assertEqual(
            ARTIFACT_CREATURES,
            (CLOCKWORK_BEAST, JUGGERNAUT, LIVING_WALL, OBSIANUS_GOLEM),
        )

    def test_catalog_uses_all_artifact_definitions(self) -> None:
        self.assertEqual(len(ARTIFACT_CARDS), 42)
        for artifact in ARTIFACT_CARDS:
            self.assertIs(CARDS_BY_NAME[artifact.name], artifact)

    def test_artifact_groups_cover_each_definition_once(self) -> None:
        grouped = (
            MANA_ARTIFACTS
            + EVENT_LIFE_ARTIFACTS
            + LAND_EVENT_ARTIFACTS
            + UTILITY_ARTIFACTS
            + TIMED_ARTIFACTS
            + TURN_ARTIFACTS
            + UNTAP_ARTIFACTS
            + ARTIFACT_CREATURES
        )
        self.assertEqual(len(grouped), len(set(grouped)))
        self.assertEqual(set(grouped), set(ARTIFACT_CARDS))


if __name__ == "__main__":
    unittest.main()
