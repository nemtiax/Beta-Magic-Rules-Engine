"""Seeded decks and game factories used for UI playtesting."""

from __future__ import annotations

from collections.abc import Iterable

from .basic_lands import BASIC_LANDS
from .card_defs.catalog import ALL_CARDS, card_named
from .cards import CardDefinition
from .game import GameState, PlayerState


def _cards(*names: str) -> tuple[CardDefinition, ...]:
    """Resolve printed names through the authoritative supported-card catalog."""

    return tuple(card_named(name) for name in names)


# Libraries use the end of the list as the top. The last seven entries are
# deliberately useful opening hands, making every test run reproducible.
VERDANT_TIDES_DECK = _cards(
    "War Mammoth", "Mox Sapphire", "Wall of Brambles", "Shanodin Dryads",
    "Sol Ring", "Forest", "Birds of Paradise", "Island", "Lord of Atlantis",
    "Prodigal Sorcerer", "Island", "Forest", "Island", "Giant Growth",
    "Tropical Island", "Flight", "Llanowar Elves", "Tranquility",
    "Psionic Blast", "Elvish Archers",
)

STONEFIRE_DECK = _cards(
    "Orcish Oriflamme", "Tunnel", "Forest", "Keldon Warlord", "Taiga",
    "Forest", "Shivan Dragon", "Mountain", "Goblin King",
    "Orcish Artillery", "Mountain", "Burrowing", "Mountain", "Forest",
    "Taiga", "Black Lotus", "Shatter", "Dragon Whelp", "Lightning Bolt",
    "Elvish Archers",
)

RADIANT_CHARGE_DECK = _cards(
    "Plains", "Northern Paladin", "Blessing", "Plains", "Mountain",
    "Holy Armor", "Plains", "Righteousness", "Plains", "Mountain",
    "Savannah Lions", "Plains", "Dwarven Demolition Team",
    "Orcish Oriflamme", "Disenchant", "Holy Strength", "Plateau", "Crusade",
    "Goblin Balloon Brigade", "Lance",
)

MOONLIT_HORDE_DECK = _cards(
    "Drudge Skeletons", "Uthden Troll", "Bog Wraith", "Will-o'-the-Wisp",
    "Firebreathing", "Royal Assassin", "Wall of Bone", "Plague Rats",
    "Swamp", "Mountain", "Nightmare", "Swamp", "Mons's Goblin Raiders",
    "Orcish Oriflamme", "Mountain", "Unholy Strength", "Badlands",
    "Bad Moon", "Weakness", "Frozen Shade",
)

COPPER_CONTROL_DECK = _cards(
    "Swamp", "Island", "Bog Wraith", "Bad Moon", "Underground Sea",
    "Copper Tablet", "Sol Ring", "Phantasmal Forces", "Swamp", "Island",
    "Scathe Zombies", "Feedback", "Warp Artifact", "Underground Sea",
    "Copper Tablet", "Sol Ring", "Feedback", "Warp Artifact", "Cursed Land",
    "Phantasmal Forces",
)

COPPER_PRESSURE_DECK = _cards(
    "Forest", "Mountain", "Gray Ogre", "Taiga", "Lightning Bolt", "Forest",
    "Copper Tablet", "Mountain", "Sol Ring", "Gray Ogre",
    "Orcish Oriflamme", "Lightning Bolt", "Forest", "Taiga",
    "Copper Tablet", "Sol Ring", "Wanderlust", "Orcish Oriflamme",
    "Force of Nature", "Lightning Bolt",
)

ARCANE_DEPTHS_DECK = _cards(
    "Island", "Swamp", "Scathe Zombies", "Phantom Monster",
    "Underground Sea", "Braingeyser", "Howl from Beyond", "Sol Ring",
    "Island", "Swamp", "Drudge Skeletons", "Braingeyser",
    "Howl from Beyond", "Underground Sea", "Island", "Scathe Zombies",
    "Sol Ring", "Phantom Monster", "Braingeyser", "Howl from Beyond",
)

ELEMENTAL_SURGE_DECK = _cards(
    "Forest", "Mountain", "Grizzly Bears", "Scryb Sprites", "Taiga",
    "Stream of Life", "Hurricane", "Earthquake", "Forest", "Mountain",
    "Grizzly Bears", "Scryb Sprites", "Stream of Life", "Taiga", "Forest",
    "Grizzly Bears", "Sol Ring", "Scryb Sprites", "Earthquake", "Hurricane",
)

AEGIS_WARDS_DECK = _cards(
    "Black Ward", "Blue Ward", "Green Ward", "Red Ward", "White Ward",
    "Circle of Protection: Black", "Circle of Protection: Blue",
    "Circle of Protection: Green", "Circle of Protection: Red",
    "Circle of Protection: White", "Black Knight", "White Knight",
    "Scrubland", "Plains", "Plains", "Scrubland", "White Knight",
    "Black Ward", "Circle of Protection: Black",
    "Circle of Protection: Red",
)

SPECTRUM_ASSAULT_DECK = _cards(
    "Island", "Swamp", "Mountain", "Forest", "Scrubland", "Righteousness",
    "Earthquake", "Scathe Zombies", "Mons's Goblin Raiders", "Grizzly Bears",
    "Phantom Monster", "Black Knight", "White Knight", "Lightning Bolt",
    "Psionic Blast", "Weakness", "Giant Growth", "Plains",
    "Tropical Island", "Badlands",
)


def _make_game(
    first_id: str,
    first_name: str,
    first_deck: Iterable[CardDefinition],
    second_id: str,
    second_name: str,
    second_deck: Iterable[CardDefinition],
    *,
    shuffle: bool,
) -> GameState:
    game = GameState(
        [
            PlayerState.with_deck(first_id, first_name, first_deck),
            PlayerState.with_deck(second_id, second_name, second_deck),
        ]
    )
    game.start(shuffle=shuffle)
    return game


def make_demo_game() -> GameState:
    """Create a started game with two decks containing every supported card."""

    deck = ALL_CARDS + BASIC_LANDS * 4
    return _make_game(
        "player-1", "Player 1", deck,
        "player-2", "Player 2", deck,
        shuffle=True,
    )


def make_test_game() -> GameState:
    """Create deterministic, compact decks for rapid UI playtesting."""

    return _make_game(
        "verdant-tides", "Verdant Tides (U/G)", VERDANT_TIDES_DECK,
        "stonefire", "Stonefire (R/G)", STONEFIRE_DECK,
        shuffle=False,
    )


def make_enchantment_test_game() -> GameState:
    """Create deterministic decks focused on global creature enchantments."""

    return _make_game(
        "radiant-charge", "Radiant Charge (W/R)", RADIANT_CHARGE_DECK,
        "moonlit-horde", "Moonlit Horde (B/R)", MOONLIT_HORDE_DECK,
        shuffle=False,
    )


def make_timed_event_test_game() -> GameState:
    """Create compact decks for exercising Copper Tablet response windows."""

    return _make_game(
        "copper-control", "Copper Control (U/B)", COPPER_CONTROL_DECK,
        "copper-pressure", "Copper Pressure (R/G)", COPPER_PRESSURE_DECK,
        shuffle=False,
    )


def make_x_test_game() -> GameState:
    """Create compact decks focused on variable casting costs."""

    return _make_game(
        "arcane-depths", "Arcane Depths (U/B)", ARCANE_DEPTHS_DECK,
        "elemental-surge", "Elemental Surge (R/G)", ELEMENTAL_SURGE_DECK,
        shuffle=False,
    )


def make_protection_test_game() -> GameState:
    """Create compact decks for exercising FAQ-era protection rules."""

    return _make_game(
        "aegis-wards", "Aegis Wards (W/B)", AEGIS_WARDS_DECK,
        "spectrum-assault", "Spectrum Assault (Five Color)",
        SPECTRUM_ASSAULT_DECK,
        shuffle=False,
    )


__all__ = [
    "VERDANT_TIDES_DECK",
    "STONEFIRE_DECK",
    "RADIANT_CHARGE_DECK",
    "MOONLIT_HORDE_DECK",
    "COPPER_CONTROL_DECK",
    "COPPER_PRESSURE_DECK",
    "ARCANE_DEPTHS_DECK",
    "ELEMENTAL_SURGE_DECK",
    "AEGIS_WARDS_DECK",
    "SPECTRUM_ASSAULT_DECK",
    "make_demo_game",
    "make_test_game",
    "make_enchantment_test_game",
    "make_timed_event_test_game",
    "make_x_test_game",
    "make_protection_test_game",
]
