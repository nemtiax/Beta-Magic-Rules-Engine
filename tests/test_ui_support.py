import unittest

from beta_magic import (
    BASIC_LANDS,
    ALL_CARDS,
    FLYING_CREATURES,
    SPECIAL_FLYING_CREATURES,
    FIRST_STRIKE_CREATURES,
    PROTECTION_CREATURES,
    PREVENTION_CARDS,
    GLOBAL_ENCHANTMENTS,
    ENCHANT_CREATURES,
    BAD_MOON,
    CRUSADE,
    TRAMPLE_CREATURES,
    TARGETED_DAMAGE_SPELLS,
    PERMANENT_DESTRUCTION_SPELLS,
    DUAL_LANDS,
    MANA_CREATURES,
    PUMP_CREATURES,
    MANA_ARTIFACTS,
    UTILITY_ARTIFACTS,
    REACH_CREATURES,
    TARGETED_PUMP_SPELLS,
    LANDWALK_CREATURES,
    CREATURE_LORDS,
    CIRCLES_OF_PROTECTION,
    GRAVEYARD_RECURSION_SPELLS,
    TIMED_ARTIFACTS,
    TIMED_ENCHANTMENTS,
    UPKEEP_CREATURES,
    VARIABLE_CREATURES,
    DAMAGE_ABILITY_CREATURES,
    UTILITY_ABILITY_CREATURES,
    REGENERATION_CREATURES,
    REGENERATION_SPELLS,
    LIFE_GAIN_SPELLS,
    VARIABLE_SPELLS,
    BLUE_UTILITY_SPELLS,
    VANILLA_CREATURES,
    VANILLA_WALLS,
    GameStatus,
    GameState,
    CardDefinition,
    PlayerState,
    CardType,
    KeywordAbility,
    TurnPhase,
    Zone,
    WAR_MAMMOTH,
    ORCISH_ORIFLAMME,
    HOLY_STRENGTH,
    UNHOLY_STRENGTH,
    WEAKNESS,
    FLIGHT,
    LANCE,
    LIGHTNING_BOLT,
    PSIONIC_BLAST,
    DISENCHANT,
    SHATTER,
    TRANQUILITY,
    TUNNEL,
    TROPICAL_ISLAND,
    TAIGA,
    BIRDS_OF_PARADISE,
    LLANOWAR_ELVES,
    DRAGON_WHELP,
    FROZEN_SHADE,
    BLACK_LOTUS,
    SOL_RING,
    GIANT_GROWTH,
    RIGHTEOUSNESS,
    BOG_WRAITH,
    SHANODIN_DRYADS,
    LORD_OF_ATLANTIS,
    GOBLIN_KING,
    BURROWING,
    REGROWTH,
    COPPER_TABLET,
    PHANTASMAL_FORCES,
    FORCE_OF_NATURE,
    PRODIGAL_SORCERER,
    ORCISH_ARTILLERY,
    DWARVEN_DEMOLITION_TEAM,
    GOBLIN_BALLOON_BRIGADE,
    NORTHERN_PALADIN,
    ROYAL_ASSASSIN,
    DRUDGE_SKELETONS,
    UTHDEN_TROLL,
    WILL_O_THE_WISP,
    WALL_OF_BONE,
    WALL_OF_BRAMBLES,
    KELDON_WARLORD,
    NIGHTMARE,
    PLAGUE_RATS,
    ISLAND,
    CURSED_LAND,
    FEEDBACK,
    WANDERLUST,
    WARP_ARTIFACT,
    BLESSING,
    HOLY_ARMOR,
    FIREBREATHING,
    STREAM_OF_LIFE,
    BRAINGEYSER,
    HOWL_FROM_BEYOND,
    EARTHQUAKE,
    HURRICANE,
)
from beta_magic.decks import (
    ARCANE_DEPTHS_DECK,
    COPPER_CONTROL_DECK,
    COPPER_PRESSURE_DECK,
    ELEMENTAL_SURGE_DECK,
    MOONLIT_HORDE_DECK,
    RADIANT_CHARGE_DECK,
    STONEFIRE_DECK,
    VERDANT_TIDES_DECK,
    make_demo_game,
    make_enchantment_test_game,
    make_protection_test_game,
    make_timed_event_test_game,
    make_test_game,
    make_x_test_game,
    AEGIS_WARDS_DECK,
    SPECTRUM_ASSAULT_DECK,
    IVORY_LAYERS_DECK,
    SHADOW_COATS_DECK,
    make_aura_test_game,
)
from beta_magic.ui import (
    GameViewModel,
    mana_text,
    parse_args,
)
from beta_magic.card_defs import HILL_GIANT


class DemoGameTests(unittest.TestCase):
    @staticmethod
    def resolve_damage_windows(view_model: GameViewModel) -> None:
        while view_model.game.pending_damage is not None:
            view_model.perspective_index = (
                view_model.game.priority_player_index
            )
            view_model.passPriority()

    def test_command_bar_only_exposes_actions_valid_in_current_context(self) -> None:
        game = make_test_game()
        view_model = GameViewModel(game)

        self.assertTrue(view_model.state["canAdvance"])
        self.assertEqual(view_model.state["advanceLabel"], "Advance to Upkeep")
        self.assertFalse(view_model.state["contextActionsVisible"])
        self.assertFalse(view_model.state["canDiscard"])

        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        self.assertEqual(view_model.state["advanceLabel"], "Advance to Discard")
        self.assertTrue(view_model.state["canBeginAttack"])
        self.assertTrue(view_model.state["contextActionsVisible"])

        attacker = game.players[0].library.pop()
        attacker.definition = HILL_GIANT
        attacker.zone = Zone.BATTLEFIELD
        game.players[0].battlefield.append(attacker)
        game.begin_combat()
        self.assertTrue(view_model.state["canDeclareAttackers"])
        self.assertFalse(view_model.state["canDeclareBlockers"])

        game.declare_attackers([attacker])
        view_model.switchPerspective()
        self.assertFalse(view_model.state["canDeclareAttackers"])
        self.assertTrue(view_model.state["canDeclareBlockers"])

    def test_auto_pass_applies_to_later_priority_windows_in_current_turn(self) -> None:
        game = make_test_game()
        view_model = GameViewModel(game)
        view_model.advance()  # Untap advances immediately to upkeep.
        view_model.advance()  # Active player proposes leaving upkeep.
        view_model.switchPerspective()

        self.assertTrue(view_model.state["hasPriority"])
        view_model.autoPassTurn()
        self.assertEqual(game.current_phase, TurnPhase.DRAW)
        self.assertTrue(view_model.state["autoPassingTurn"])

        view_model.switchPerspective()
        view_model.advance()
        self.assertEqual(game.current_phase, TurnPhase.MAIN)
        self.assertIsNone(game.priority_player_index)

        game.turn_number += 1
        view_model.switchPerspective()
        self.assertFalse(view_model.state["autoPassingTurn"])

    def test_auto_pass_responds_to_an_opponents_untargeted_spell(self) -> None:
        game = make_test_game()
        view_model = GameViewModel(game)
        view_model.advance()
        view_model.advance()
        view_model.switchPerspective()
        view_model.autoPassTurn()

        view_model.switchPerspective()
        spell = game.players[0].hand[0]
        spell.definition = CardDefinition(
            name="Test Fast Effect",
            card_types=frozenset({CardType.INSTANT}),
        )
        view_model.activateCard(str(spell.id))

        self.assertEqual(game.priority_player_index, 0)
        self.assertTrue(view_model.state["hasPriority"])
        self.assertEqual(game.consecutive_passes, 1)

    def test_discard_command_only_appears_for_affected_perspective(self) -> None:
        game = make_test_game()
        view_model = GameViewModel(game)
        game.current_phase = TurnPhase.DISCARD
        while len(game.active_player.hand) <= 7:
            game.active_player.draw()

        self.assertTrue(view_model.state["canDiscard"])
        view_model.switchPerspective()
        self.assertFalse(view_model.state["canDiscard"])

    def test_battlefield_view_groups_attachments_behind_their_host(self) -> None:
        game = make_test_game()
        host = game.players[0].library.pop()
        host.definition = HILL_GIANT
        host.zone = Zone.BATTLEFIELD
        game.players[0].battlefield.append(host)
        aura = game.players[0].library.pop()
        aura.definition = HOLY_STRENGTH
        aura.zone = Zone.BATTLEFIELD
        aura.enchanted_card_id = host.id
        game.players[0].battlefield.append(aura)
        second_aura = game.players[0].library.pop()
        second_aura.definition = FLIGHT
        second_aura.zone = Zone.BATTLEFIELD
        second_aura.enchanted_card_id = host.id
        game.players[0].battlefield.append(second_aura)
        view_model = GameViewModel(game)

        nonlands = view_model.state["perspective"]["battlefieldNonlands"]
        self.assertEqual(
            [card["id"] for card in nonlands].count(str(aura.id)), 0
        )
        host_data = next(card for card in nonlands if card["id"] == str(host.id))
        self.assertEqual(
            [card["id"] for card in host_data["attachments"]],
            [str(aura.id), str(second_aura.id)],
        )
        self.assertEqual(host_data["attachments"][0]["attachedTo"], host.name)
        view_model.toggleCard(str(aura.id))
        view_model.toggleCard(str(second_aura.id))
        self.assertEqual(
            view_model.selected_card_ids,
            {aura.id, second_aura.id},
        )

    def test_demo_game_has_two_started_supported_card_decks(self) -> None:
        game = make_demo_game()
        self.assertEqual(len(game.players), 2)
        self.assertEqual(game.status, GameStatus.IN_PROGRESS)
        self.assertEqual(game.current_phase, TurnPhase.UNTAP)
        for player in game.players:
            all_cards = player.library + player.hand
        self.assertEqual(
            len(all_cards),
            len(ALL_CARDS) + len(BASIC_LANDS) * 4,
        )

    def test_mana_display_only_lists_nonzero_colors(self) -> None:
        game = make_demo_game()
        player = game.players[0]
        self.assertEqual(mana_text(player), "empty")
        player.mana_pool.white = 2
        player.mana_pool.green = 1
        self.assertEqual(mana_text(player), "W:2 G:1")

    def test_ui_x_picker_starts_at_maximum_and_supports_adjustment(self) -> None:
        game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [STREAM_OF_LIFE] * 10),
                PlayerState.with_deck("bob", "Bob", [STREAM_OF_LIFE] * 10),
            ]
        )
        game.start(opening_hand_size=1, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        spell = game.players[0].hand[0]
        game.players[0].mana_pool.green = 1
        game.players[0].mana_pool.colorless = 4
        view_model = GameViewModel(game)

        view_model.activateCard(str(spell.id))
        self.assertTrue(view_model.state["choosingX"])
        self.assertEqual(view_model.state["xMaximum"], 4)
        self.assertEqual(view_model.state["xValue"], 4)

        view_model.adjustX(-1)
        self.assertEqual(view_model.state["xValue"], 3)
        view_model.confirmXCast()
        self.assertFalse(view_model.state["choosingX"])
        self.assertEqual(game.pending_cast.x_value, 3)

    def test_view_model_hides_opponents_hand(self) -> None:
        view_model = GameViewModel(make_demo_game())
        state = view_model.state
        self.assertEqual(len(state["perspective"]["hand"]), 7)
        self.assertEqual(state["opponent"]["hand"], [])
        self.assertEqual(state["opponent"]["handCount"], 7)

    def test_card_view_data_includes_compact_mana_cost(self) -> None:
        view_model = GameViewModel(make_demo_game())
        cards = (
            view_model.game.players[0].library + view_model.game.players[0].hand
        )
        creature = next(card for card in cards if card.definition.mana_cost.mana_value)
        data = view_model._card_data(creature)
        self.assertEqual(data["manaCost"], creature.definition.mana_cost.compact)
        self.assertNotIn("{", data["manaCost"])

    def test_battlefield_view_separates_lands_and_nonlands(self) -> None:
        view_model = GameViewModel(make_test_game())
        player = view_model.game.players[0]
        land = next(
            card
            for card in player.hand
            if CardType.LAND in card.definition.card_types
        )
        creature = next(
            card for card in player.hand if CardType.CREATURE in card.definition.card_types
        )
        player.hand.remove(land)
        player.hand.remove(creature)
        land.zone = Zone.BATTLEFIELD
        creature.zone = Zone.BATTLEFIELD
        player.battlefield.extend((land, creature))

        data = view_model.state["perspective"]
        self.assertEqual(
            [card["name"] for card in data["battlefieldLands"]], [land.name]
        )
        self.assertEqual(
            [card["name"] for card in data["battlefieldNonlands"]], [creature.name]
        )

    def test_seeded_test_decks_are_small_repeatable_and_two_color(self) -> None:
        first = make_test_game()
        second = make_test_game()
        self.assertEqual(len(VERDANT_TIDES_DECK), 20)
        self.assertEqual(len(STONEFIRE_DECK), 20)
        self.assertEqual(
            [card.name for card in first.players[0].hand],
            [card.name for card in second.players[0].hand],
        )
        self.assertEqual(
            {color.value for card in VERDANT_TIDES_DECK for color in card.colors},
            {"U", "G"},
        )
        self.assertEqual(
            {color.value for card in STONEFIRE_DECK for color in card.colors},
            {"R", "G"},
        )
        self.assertIn(WAR_MAMMOTH, VERDANT_TIDES_DECK)
        self.assertIn(TROPICAL_ISLAND, VERDANT_TIDES_DECK)
        self.assertIn(TAIGA, STONEFIRE_DECK)
        self.assertIn(DRAGON_WHELP, STONEFIRE_DECK)
        self.assertIn(BLACK_LOTUS, STONEFIRE_DECK)
        self.assertIn(SOL_RING, VERDANT_TIDES_DECK)
        self.assertIn(GIANT_GROWTH, VERDANT_TIDES_DECK)
        self.assertIn(SHANODIN_DRYADS, VERDANT_TIDES_DECK)
        self.assertIn(LORD_OF_ATLANTIS, VERDANT_TIDES_DECK)
        self.assertIn(GOBLIN_KING, STONEFIRE_DECK)
        self.assertIn(BURROWING, STONEFIRE_DECK)
        self.assertIn(KELDON_WARLORD, STONEFIRE_DECK)
        self.assertIn(BIRDS_OF_PARADISE, VERDANT_TIDES_DECK)
        self.assertIn(PRODIGAL_SORCERER, VERDANT_TIDES_DECK)
        self.assertIn(WALL_OF_BRAMBLES, VERDANT_TIDES_DECK)
        self.assertIn(ORCISH_ARTILLERY, STONEFIRE_DECK)
        self.assertIn(TUNNEL, STONEFIRE_DECK)
        self.assertIn(
            LLANOWAR_ELVES,
            [card.definition for card in first.players[0].hand],
        )
        self.assertIn(
            TRANQUILITY,
            [card.definition for card in first.players[0].hand],
        )
        self.assertIn(
            SHATTER,
            [card.definition for card in first.players[1].hand],
        )
        self.assertIn(
            FLIGHT, [card.definition for card in first.players[0].hand]
        )
        self.assertIn(
            PSIONIC_BLAST, [card.definition for card in first.players[0].hand]
        )
        self.assertIn(
            LIGHTNING_BOLT, [card.definition for card in first.players[1].hand]
        )
        self.assertIn(ORCISH_ORIFLAMME, STONEFIRE_DECK)

    def test_view_model_exposes_and_activates_dual_land_choices(self) -> None:
        view_model = GameViewModel(make_test_game())
        view_model.game.advance_phase()
        player = view_model.game.players[0]
        land = next(
            card
            for card in player.hand
            if card.definition is TROPICAL_ISLAND
        )
        player.hand.remove(land)
        land.zone = Zone.BATTLEFIELD
        land.controller_id = player.id
        player.battlefield.append(land)

        data = view_model._card_data(land)
        self.assertEqual(
            [ability["label"] for ability in data["activatedAbilities"]],
            ["Add G", "Add U"],
        )
        view_model.activateAbility(str(land.id), 1)

        self.assertTrue(land.tapped)
        self.assertEqual(player.mana_pool.blue, 1)
        self.assertEqual(player.mana_pool.green, 0)

    def test_view_model_disables_summoning_sick_mana_ability(self) -> None:
        view_model = GameViewModel(make_test_game())
        while view_model.game.current_phase is not TurnPhase.MAIN:
            view_model.game.advance_phase()
        player = view_model.game.players[0]
        elves = next(
            card for card in player.hand if card.definition is LLANOWAR_ELVES
        )
        player.mana_pool.green = 1
        view_model.game.begin_cast(elves)
        while view_model.game.stack:
            priority = view_model.game.players[
                view_model.game.priority_player_index
            ]
            view_model.game.pass_priority(priority.id)

        ability = view_model._card_data(elves)["activatedAbilities"][0]
        self.assertFalse(ability["enabled"])
        view_model.activateAbility(str(elves.id), 0)
        self.assertFalse(elves.tapped)

    def test_ui_casts_and_activates_black_lotus(self) -> None:
        view_model = GameViewModel(make_test_game())
        player = view_model.game.players[1]
        while not (
            view_model.game.active_player is player
            and view_model.game.current_phase is TurnPhase.MAIN
        ):
            if (
                view_model.game.current_phase is TurnPhase.DISCARD
                and view_model.game.active_player.discard_required
            ):
                view_model.game.discard(view_model.game.active_player.hand[0])
            view_model.game.advance_phase()
        view_model.perspective_index = 1
        lotus = next(
            card for card in player.hand if card.definition is BLACK_LOTUS
        )

        view_model.activateCard(str(lotus.id))
        while view_model.game.stack:
            priority = view_model.game.players[
                view_model.game.priority_player_index
            ]
            view_model.game.pass_priority(priority.id)
        data = view_model._card_data(lotus)
        self.assertEqual(data["manaCost"], "0")
        self.assertEqual(
            [ability["label"] for ability in data["activatedAbilities"]],
            ["Add WWW", "Add UUU", "Add BBB", "Add RRR", "Add GGG"],
        )
        view_model.activateAbility(str(lotus.id), 4)

        self.assertEqual(player.mana_pool.green, 3)
        self.assertIn(lotus, player.graveyard)

    def test_test_deck_flag_is_opt_in(self) -> None:
        self.assertFalse(parse_args([]).test_decks)
        self.assertFalse(parse_args([]).enchantment_test_decks)
        self.assertFalse(parse_args([]).timed_event_test_decks)
        self.assertFalse(parse_args([]).x_test_decks)
        self.assertFalse(parse_args([]).protection_test_decks)
        self.assertFalse(parse_args([]).aura_test_decks)
        self.assertTrue(parse_args(["--test-decks"]).test_decks)
        self.assertTrue(
            parse_args(["--enchantment-test-decks"]).enchantment_test_decks
        )
        self.assertTrue(
            parse_args(["--timed-event-test-decks"]).timed_event_test_decks
        )
        self.assertTrue(parse_args(["--x-test-decks"]).x_test_decks)
        self.assertTrue(
            parse_args(["--protection-test-decks"]).protection_test_decks
        )
        self.assertTrue(parse_args(["--aura-test-decks"]).aura_test_decks)

    def test_aura_test_decks_open_with_creatures_mana_and_auras(self) -> None:
        game = make_aura_test_game()

        self.assertEqual(len(IVORY_LAYERS_DECK), 20)
        self.assertEqual(len(SHADOW_COATS_DECK), 20)
        for player in game.players:
            self.assertTrue(any(CardType.LAND in card.definition.card_types
                                for card in player.hand))
            self.assertTrue(any(CardType.CREATURE in card.definition.card_types
                                for card in player.hand))
            self.assertGreaterEqual(
                sum("Enchant Creature" in card.definition.subtypes
                    for card in player.hand),
                3,
            )

    def test_protection_test_decks_are_small_repeatable_and_focused(self) -> None:
        first = make_protection_test_game()
        second = make_protection_test_game()
        self.assertEqual(len(AEGIS_WARDS_DECK), 20)
        self.assertEqual(len(SPECTRUM_ASSAULT_DECK), 20)
        self.assertEqual(
            [card.name for card in first.players[0].hand],
            [card.name for card in second.players[0].hand],
        )
        for name in (
            "Black Ward",
            "Blue Ward",
            "Green Ward",
            "Red Ward",
            "White Ward",
            "White Knight",
            "Black Knight",
            "Circle of Protection: Black",
            "Circle of Protection: Blue",
            "Circle of Protection: Green",
            "Circle of Protection: Red",
            "Circle of Protection: White",
        ):
            self.assertIn(name, [card.name for card in AEGIS_WARDS_DECK])
        for name in (
            "Lightning Bolt",
            "Psionic Blast",
            "Weakness",
            "Giant Growth",
            "Righteousness",
            "Earthquake",
        ):
            self.assertIn(name, [card.name for card in SPECTRUM_ASSAULT_DECK])
        spectrum_hand = first.players[1].hand
        self.assertEqual(
            {
                subtype
                for card in spectrum_hand
                if CardType.LAND in card.definition.card_types
                for subtype in card.definition.subtypes
            },
            {"Plains", "Island", "Swamp", "Mountain", "Forest"},
        )

    def test_x_test_decks_are_small_repeatable_and_effect_focused(self) -> None:
        first = make_x_test_game()
        second = make_x_test_game()
        self.assertEqual(len(ARCANE_DEPTHS_DECK), 20)
        self.assertEqual(len(ELEMENTAL_SURGE_DECK), 20)
        self.assertEqual(
            [card.name for card in first.players[0].hand],
            [card.name for card in second.players[0].hand],
        )
        self.assertEqual(
            {
                color.value
                for card in ARCANE_DEPTHS_DECK
                for color in card.colors
            },
            {"U", "B"},
        )
        self.assertEqual(
            {
                color.value
                for card in ELEMENTAL_SURGE_DECK
                for color in card.colors
            },
            {"R", "G"},
        )
        combined = ARCANE_DEPTHS_DECK + ELEMENTAL_SURGE_DECK
        for definition in (
            BRAINGEYSER,
            HOWL_FROM_BEYOND,
            EARTHQUAKE,
            HURRICANE,
            STREAM_OF_LIFE,
        ):
            self.assertIn(definition, combined)
        for player in first.players:
            opening = [card.definition for card in player.hand]
            self.assertTrue(
                any(
                    CardType.CREATURE in definition.card_types
                    and KeywordAbility.FLYING in definition.abilities
                    for definition in opening
                )
            )
            self.assertTrue(
                any(
                    CardType.CREATURE in definition.card_types
                    and KeywordAbility.FLYING not in definition.abilities
                    for definition in opening
                )
            )

    def test_timed_event_test_decks_are_small_repeatable_and_effect_focused(
        self,
    ) -> None:
        first = make_timed_event_test_game()
        second = make_timed_event_test_game()
        self.assertEqual(len(COPPER_CONTROL_DECK), 20)
        self.assertEqual(len(COPPER_PRESSURE_DECK), 20)
        self.assertEqual(
            [card.name for card in first.players[0].hand],
            [card.name for card in second.players[0].hand],
        )
        for player in first.players:
            definitions = [card.definition for card in player.hand]
            self.assertIn(COPPER_TABLET, definitions)
            self.assertIn(SOL_RING, definitions)
        combined = COPPER_CONTROL_DECK + COPPER_PRESSURE_DECK
        for definition in (
            CURSED_LAND,
            FEEDBACK,
            WANDERLUST,
            WARP_ARTIFACT,
        ):
            self.assertIn(definition, combined)
        self.assertIn(PHANTASMAL_FORCES, COPPER_CONTROL_DECK)
        self.assertIn(FORCE_OF_NATURE, COPPER_PRESSURE_DECK)

    def test_ui_prompts_for_and_pays_upkeep_cost(self) -> None:
        game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [HILL_GIANT] * 20),
                PlayerState.with_deck("bob", "Bob", [HILL_GIANT] * 20),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        forces = game.players[0].library.pop()
        forces.definition = PHANTASMAL_FORCES
        forces.zone = Zone.BATTLEFIELD
        forces.controller_id = game.players[0].id
        game.players[0].battlefield.append(forces)
        island = game.players[0].library.pop()
        island.definition = ISLAND
        island.zone = Zone.BATTLEFIELD
        island.controller_id = game.players[0].id
        game.players[0].battlefield.append(island)
        view_model = GameViewModel(game)

        view_model.advance()

        self.assertTrue(view_model.state["upkeepPaymentRequired"])
        self.assertFalse(view_model.state["canPayUpkeep"])
        view_model.activateAbility(str(island.id), 0)
        self.assertTrue(view_model.state["canPayUpkeep"])
        view_model.chooseUpkeepPayment(True)
        self.assertFalse(view_model.state["upkeepPaymentRequired"])
        view_model.switchPerspective()
        view_model.passPriority()
        view_model.switchPerspective()
        view_model.passPriority()
        self.assertIn(forces, game.players[0].battlefield)

    def test_ui_exposes_and_resolves_timed_event_priority(self) -> None:
        game = GameState(
            [
                PlayerState.with_deck("alice", "Alice", [HILL_GIANT] * 20),
                PlayerState.with_deck("bob", "Bob", [HILL_GIANT] * 20),
            ]
        )
        game.start(opening_hand_size=0, shuffle=False)
        tablet = game.players[1].library.pop()
        tablet.definition = COPPER_TABLET
        tablet.zone = Zone.BATTLEFIELD
        tablet.controller_id = game.players[1].id
        game.players[1].battlefield.append(tablet)
        view_model = GameViewModel(game)

        view_model.advance()

        self.assertEqual(view_model.state["stack"], [])
        self.assertIn("Copper Tablet", view_model.state["timedEvent"])
        self.assertTrue(view_model.state["hasPriority"])
        view_model.passPriority()
        view_model.switchPerspective()
        view_model.passPriority()
        self.resolve_damage_windows(view_model)
        self.assertEqual(game.players[0].life, 19)
        self.assertEqual(view_model.state["timedEvent"], "")
        self.assertIn("damage from Copper Tablet", view_model.state["message"])

    def test_enchantment_test_decks_are_small_and_repeatable(self) -> None:
        first = make_enchantment_test_game()
        second = make_enchantment_test_game()
        self.assertEqual(len(RADIANT_CHARGE_DECK), 20)
        self.assertEqual(len(MOONLIT_HORDE_DECK), 20)
        self.assertEqual(
            [card.name for card in first.players[0].hand],
            [card.name for card in second.players[0].hand],
        )
        self.assertEqual(
            {color.value for card in RADIANT_CHARGE_DECK for color in card.colors},
            {"W", "R"},
        )
        self.assertEqual(
            {color.value for card in MOONLIT_HORDE_DECK for color in card.colors},
            {"B", "R"},
        )
        self.assertIn(CRUSADE, RADIANT_CHARGE_DECK)
        self.assertIn(BAD_MOON, MOONLIT_HORDE_DECK)
        self.assertIn(FROZEN_SHADE, MOONLIT_HORDE_DECK)
        self.assertIn(BOG_WRAITH, MOONLIT_HORDE_DECK)
        self.assertIn(NIGHTMARE, MOONLIT_HORDE_DECK)
        self.assertIn(PLAGUE_RATS, MOONLIT_HORDE_DECK)
        self.assertIn(RIGHTEOUSNESS, RADIANT_CHARGE_DECK)
        self.assertIn(ORCISH_ORIFLAMME, RADIANT_CHARGE_DECK)
        self.assertIn(BLESSING, RADIANT_CHARGE_DECK)
        self.assertIn(HOLY_ARMOR, RADIANT_CHARGE_DECK)
        self.assertIn(FIREBREATHING, MOONLIT_HORDE_DECK)
        self.assertIn(
            DISENCHANT,
            [card.definition for card in first.players[0].hand],
        )
        self.assertIn(ORCISH_ORIFLAMME, MOONLIT_HORDE_DECK)
        self.assertIn(NORTHERN_PALADIN, RADIANT_CHARGE_DECK)
        self.assertIn(DWARVEN_DEMOLITION_TEAM, RADIANT_CHARGE_DECK)
        self.assertIn(GOBLIN_BALLOON_BRIGADE, RADIANT_CHARGE_DECK)
        self.assertIn(ROYAL_ASSASSIN, MOONLIT_HORDE_DECK)
        self.assertIn(DRUDGE_SKELETONS, MOONLIT_HORDE_DECK)
        self.assertIn(UTHDEN_TROLL, MOONLIT_HORDE_DECK)
        self.assertIn(WILL_O_THE_WISP, MOONLIT_HORDE_DECK)
        self.assertIn(WALL_OF_BONE, MOONLIT_HORDE_DECK)
        self.assertIn(
            HOLY_STRENGTH, [card.definition for card in first.players[0].hand]
        )
        self.assertIn(
            UNHOLY_STRENGTH, [card.definition for card in first.players[1].hand]
        )
        self.assertIn(
            WEAKNESS, [card.definition for card in first.players[1].hand]
        )
        self.assertIn(
            LANCE, [card.definition for card in first.players[0].hand]
        )

    def test_ui_waits_for_and_accepts_enchantment_target(self) -> None:
        game = make_enchantment_test_game()
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        view_model = GameViewModel(game)
        caster = game.players[0]
        aura = next(
            card for card in caster.hand if card.definition is HOLY_STRENGTH
        )
        target = caster.library.pop()
        target.definition = HILL_GIANT
        target.zone = Zone.BATTLEFIELD
        caster.battlefield.append(target)
        caster.mana_pool.white = 1

        view_model.activateCard(str(aura.id))

        self.assertTrue(view_model.state["targeting"])
        self.assertIn("Choose a target", view_model.state["message"])
        self.assertIn(aura, caster.hand)

        view_model.toggleCard(str(target.id))

        self.assertFalse(view_model.state["targeting"])
        self.assertIn(aura, game.stack)
        while game.stack:
            priority = game.players[game.priority_player_index]
            game.pass_priority(priority.id)
        self.assertEqual(aura.enchanted_card_id, target.id)
        self.assertIn("enchanting", view_model.state["message"])

    def test_ui_can_click_a_card_in_graveyard_as_a_target(self) -> None:
        alice = PlayerState.with_deck("alice", "Alice", [HILL_GIANT] * 20)
        bob = PlayerState.with_deck("bob", "Bob", [HILL_GIANT] * 20)
        game = GameState([alice, bob])
        game.start(opening_hand_size=0, shuffle=False)
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        target = alice.library.pop()
        target.zone = Zone.GRAVEYARD
        alice.graveyard.append(target)
        for _ in range(6):
            card = alice.library.pop()
            card.zone = Zone.GRAVEYARD
            alice.graveyard.append(card)
        regrowth = alice.library.pop()
        regrowth.definition = REGROWTH
        regrowth.zone = Zone.HAND
        alice.hand.append(regrowth)
        alice.mana_pool.green = 1
        alice.mana_pool.colorless = 1
        view_model = GameViewModel(game)

        view_model.activateCard(str(regrowth.id))

        graveyard_data = view_model.state["perspective"]["graveyard"]
        self.assertEqual(len(graveyard_data), 7)
        target_data = next(card for card in graveyard_data if card["id"] == str(target.id))
        self.assertTrue(target_data["legalTarget"])
        view_model.toggleCard(str(target.id))
        while game.stack:
            priority = game.players[game.priority_player_index]
            game.pass_priority(priority.id)

        self.assertIn(target, alice.hand)

    def test_ui_can_target_player_with_damage_instant(self) -> None:
        game = make_test_game()
        game.advance_phase()
        view_model = GameViewModel(game)
        caster = game.players[0]
        blast = next(
            card for card in caster.hand if card.definition is PSIONIC_BLAST
        )
        caster.mana_pool.blue = 1
        caster.mana_pool.colorless = 2

        view_model.activateCard(str(blast.id))

        self.assertTrue(view_model.state["targeting"])
        self.assertTrue(view_model.state["perspective"]["legalTarget"])
        self.assertTrue(view_model.state["opponent"]["legalTarget"])

        view_model.targetPlayer(game.players[1].id)

        self.assertFalse(view_model.state["targeting"])
        view_model.switchPerspective()
        view_model.passPriority()
        view_model.switchPerspective()
        view_model.passPriority()
        self.resolve_damage_windows(view_model)
        self.assertEqual(game.players[1].life, 16)
        self.assertEqual(caster.life, 18)
        self.assertIn(blast, caster.graveyard)
        self.assertIn("damage from Psionic Blast", view_model.state["message"])

    def test_new_game_preserves_enchantment_test_deck_mode(self) -> None:
        view_model = GameViewModel(
            make_enchantment_test_game(), game_factory=make_enchantment_test_game
        )
        view_model.newGame()
        self.assertEqual(
            len(view_model.game.players[0].library)
            + len(view_model.game.players[0].hand),
            20,
        )

    def test_new_game_preserves_test_deck_mode(self) -> None:
        view_model = GameViewModel(
            make_test_game(), game_factory=make_test_game
        )
        view_model.newGame()
        self.assertEqual(
            len(view_model.game.players[0].library)
            + len(view_model.game.players[0].hand),
            20,
        )

    def test_new_game_preserves_x_test_deck_mode(self) -> None:
        view_model = GameViewModel(
            make_x_test_game(), game_factory=make_x_test_game
        )
        view_model.newGame()
        self.assertEqual(
            [player.name for player in view_model.game.players],
            ["Arcane Depths (U/B)", "Elemental Surge (R/G)"],
        )
        self.assertTrue(
            all(
                len(player.library) + len(player.hand) == 20
                for player in view_model.game.players
            )
        )

    def test_combat_damage_is_not_reported_as_mana_burn(self) -> None:
        game = make_test_game()
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        attacker = game.players[0].library.pop()
        attacker.definition = HILL_GIANT
        attacker.zone = Zone.BATTLEFIELD
        game.players[0].battlefield.append(attacker)
        game.begin_combat()
        game.declare_attackers([attacker])
        game.declare_blockers({})
        game.advance_combat()
        view_model = GameViewModel(game)

        view_model.advance()
        self.resolve_damage_windows(view_model)

        self.assertIn("took 3 combat damage", view_model.state["message"])
        self.assertNotIn("mana burn", view_model.state["message"])

    def test_combat_damage_and_mana_burn_are_reported_separately(self) -> None:
        game = make_test_game()
        while game.current_phase is not TurnPhase.MAIN:
            game.advance_phase()
        attacker = game.players[0].library.pop()
        attacker.definition = HILL_GIANT
        attacker.zone = Zone.BATTLEFIELD
        game.players[0].battlefield.append(attacker)
        game.begin_combat()
        game.declare_attackers([attacker])
        game.declare_blockers({})
        game.advance_combat()
        game.players[1].mana_pool.green = 1
        view_model = GameViewModel(game)

        view_model.advance()
        self.resolve_damage_windows(view_model)

        message = view_model.state["message"]
        self.assertIn("took 3 combat damage", message)
        self.assertIn("took 1 mana burn", message)


if __name__ == "__main__":
    unittest.main()
