"""Mechanic-focused card collections used by rules and UI tests.

These are test expectations and fixtures, not part of the rules engine's
card-definition API. Production code should query the catalog or import a
printed definition from its color/type module.
"""

from beta_magic.card_defs.catalog import card_named


def _cards(*names: str):
    return tuple(card_named(name) for name in names)


VANILLA_CREATURES = _cards(
    "Pearled Unicorn",
    "Savannah Lions",
    "Merfolk of the Pearl Trident",
    "Water Elemental",
    "Scathe Zombies",
    "Earth Elemental",
    "Fire Elemental",
    "Gray Ogre",
    "Hill Giant",
    "Hurloon Minotaur",
    "Mons's Goblin Raiders",
    "Craw Wurm",
    "Grizzly Bears",
    "Ironroot Treefolk",
    "Obsianus Golem",
)
MANA_CREATURES = _cards("Llanowar Elves", "Birds of Paradise")
LANDWALK_CREATURES = _cards("Bog Wraith", "Shanodin Dryads")
CREATURE_LORDS = _cards("Lord of Atlantis", "Goblin King")
PUMP_CREATURES = _cards(
    "Shivan Dragon",
    "Frozen Shade",
    "Granite Gargoyle",
    "Dragon Whelp",
    "Wall of Water",
    "Wall of Fire",
)
VANILLA_WALLS = _cards("Wall of Ice", "Wall of Stone", "Wall of Wood")
FLYING_CREATURES = _cards(
    "Air Elemental",
    "Mahamoti Djinn",
    "Phantom Monster",
    "Roc of Kher Ridges",
    "Scryb Sprites",
    "Wall of Air",
    "Wall of Swords",
)
SPECIAL_FLYING_CREATURES = _cards("Serra Angel")
REACH_CREATURES = _cards("Giant Spider")
FIRST_STRIKE_CREATURES = _cards("Elvish Archers")
PROTECTION_CREATURES = _cards("White Knight", "Black Knight")
PREVENTION_CARDS = _cards("Guardian Angel", "Healing Salve", "Samite Healer")
TRAMPLE_CREATURES = _cards("War Mammoth")
GLOBAL_ENCHANTMENTS = _cards(
    "Crusade", "Bad Moon", "Orcish Oriflamme", "Castle", "Living Lands"
)

SIMPLE_ENCHANT_CREATURES = _cards(
    "Holy Strength", "Unholy Strength", "Weakness", "Aspect of Wolf"
)
ABILITY_ENCHANT_CREATURES = _cards(
    "Lance", "Flight", "Burrowing", "Fear", "Regeneration", "Web"
)
PUMP_ENCHANT_CREATURES = _cards("Blessing", "Holy Armor", "Firebreathing")
PROTECTION_ENCHANT_CREATURES = _cards(
    "Black Ward", "Blue Ward", "Green Ward", "Red Ward", "White Ward"
)
CONTROL_ENCHANTMENTS = _cards("Control Magic", "Steal Artifact")
ENCHANT_CREATURES = (
    SIMPLE_ENCHANT_CREATURES
    + ABILITY_ENCHANT_CREATURES
    + PUMP_ENCHANT_CREATURES
    + PROTECTION_ENCHANT_CREATURES
    + _cards("Control Magic")
)

TARGETED_DAMAGE_SPELLS = _cards("Lightning Bolt", "Psionic Blast")
TARGETED_PUMP_SPELLS = _cards("Giant Growth", "Righteousness")
LAND_DESTRUCTION_SPELLS = _cards(
    "Stone Rain", "Sinkhole", "Ice Storm", "Armageddon", "Flashfires", "Tsunami"
)
PERMANENT_DESTRUCTION_SPELLS = _cards(
    "Disenchant", "Shatter", "Terror", "Tunnel", "Tranquility"
) + LAND_DESTRUCTION_SPELLS
GRAVEYARD_RECURSION_SPELLS = _cards("Regrowth", "Raise Dead", "Resurrection")
LACES = _cards("Purelace", "Thoughtlace", "Deathlace", "Chaoslace", "Lifelace")
BLUE_UTILITY_SPELLS = _cards("Ancestral Recall", "Jump", "Unsummon")
TIMED_ENCHANTMENTS = _cards("Cursed Land", "Feedback", "Wanderlust", "Warp Artifact")
UPKEEP_CREATURES = _cards("Phantasmal Forces", "Force of Nature")
VARIABLE_CREATURES = _cards("Keldon Warlord", "Nightmare", "Plague Rats")
DAMAGE_ABILITY_CREATURES = _cards(
    "Prodigal Sorcerer", "Orcish Artillery", "Pirate Ship"
)
LANDHOME_CREATURES = _cards("Pirate Ship", "Sea Serpent")
UTILITY_ABILITY_CREATURES = _cards(
    "Dwarven Demolition Team",
    "Dwarven Warriors",
    "Goblin Balloon Brigade",
    "Royal Assassin",
    "Northern Paladin",
)
REGENERATION_CREATURES = _cards(
    "Drudge Skeletons",
    "Uthden Troll",
    "Will-o'-the-Wisp",
    "Wall of Bone",
    "Wall of Brambles",
    "Living Wall",
    "Sedge Troll",
    "Zombie Master",
)
REGENERATION_SPELLS = _cards("Death Ward")
LIFE_GAIN_SPELLS = _cards("Stream of Life")
VARIABLE_SPELLS = _cards(
    "Braingeyser", "Howl from Beyond", "Disintegrate", "Earthquake", "Hurricane"
)
