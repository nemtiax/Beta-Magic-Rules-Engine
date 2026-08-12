"""Small, shared rule-engine value types."""

from __future__ import annotations

from enum import Enum

BASIC_LAND_SUBTYPES = ("Plains", "Island", "Swamp", "Mountain", "Forest")


class Color(str, Enum):
    WHITE = "W"
    BLUE = "U"
    BLACK = "B"
    RED = "R"
    GREEN = "G"
    COLORLESS = "C"


class CardType(str, Enum):
    """Card types printed in Limited Edition Beta.

    ``CREATURE`` is included as a convenient normalized type even though Beta
    creature cards were printed as "Summon <creature>".
    """

    ARTIFACT = "Artifact"
    CREATURE = "Creature"
    ENCHANTMENT = "Enchantment"
    INSTANT = "Instant"
    INTERRUPT = "Interrupt"
    LAND = "Land"
    SORCERY = "Sorcery"


class KeywordAbility(str, Enum):
    """Named abilities understood directly by the rules engine."""

    FLYING = "Flying"
    FIRST_STRIKE = "First strike"
    TRAMPLE = "Trample"
    BANDING = "Banding"
    FORESTWALK = "Forestwalk"
    ISLANDWALK = "Islandwalk"
    MOUNTAINWALK = "Mountainwalk"
    SWAMPWALK = "Swampwalk"
    DOES_NOT_TAP_TO_ATTACK = "Does not tap to attack"
    CAN_BLOCK_FLYING = "Can block flying"
    PROTECTION_FROM_WHITE = "Protection from white"
    PROTECTION_FROM_BLUE = "Protection from blue"
    PROTECTION_FROM_BLACK = "Protection from black"
    PROTECTION_FROM_RED = "Protection from red"
    PROTECTION_FROM_GREEN = "Protection from green"

    @property
    def protection_color(self) -> Color | None:
        return {
            KeywordAbility.PROTECTION_FROM_WHITE: Color.WHITE,
            KeywordAbility.PROTECTION_FROM_BLUE: Color.BLUE,
            KeywordAbility.PROTECTION_FROM_BLACK: Color.BLACK,
            KeywordAbility.PROTECTION_FROM_RED: Color.RED,
            KeywordAbility.PROTECTION_FROM_GREEN: Color.GREEN,
        }.get(self)

    @property
    def landwalk_subtype(self) -> str | None:
        return {
            KeywordAbility.FORESTWALK: "Forest",
            KeywordAbility.ISLANDWALK: "Island",
            KeywordAbility.MOUNTAINWALK: "Mountain",
            KeywordAbility.SWAMPWALK: "Swamp",
        }.get(self)


class Zone(str, Enum):
    LIBRARY = "library"
    HAND = "hand"
    BATTLEFIELD = "battlefield"
    GRAVEYARD = "graveyard"
    STACK = "stack"
    EXILE = "exile"
    ANTE = "ante"


class GameStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class TurnPhase(str, Enum):
    """The six phases of a turn in the 1993 Beta rulebook."""

    UNTAP = "untap"
    UPKEEP = "upkeep"
    DRAW = "draw"
    MAIN = "main"
    DISCARD = "discard"
    END = "end"

    @property
    def next(self) -> TurnPhase | None:
        phases = tuple(type(self))
        index = phases.index(self)
        return phases[index + 1] if index + 1 < len(phases) else None


class CombatStep(str, Enum):
    """Declarations and response windows in the clarified Beta attack."""

    ATTACK_RESPONSE = "fast_effects_before_attackers"
    DECLARE_ATTACKERS = "declare_attackers"
    ATTACKER_RESPONSE = "fast_effects_before_blockers"
    DECLARE_BLOCKERS = "declare_blockers"
    BLOCKER_RESPONSE = "fast_effects_before_damage"
    DAMAGE = "damage"
