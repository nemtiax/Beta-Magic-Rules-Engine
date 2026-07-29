import unittest

from beta_magic import (
    BASIC_LANDS,
    FLYING_CREATURES,
    FIRST_STRIKE_CREATURES,
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
    TARGETED_PUMP_SPELLS,
    LANDWALK_CREATURES,
    CREATURE_LORDS,
    GRAVEYARD_RECURSION_SPELLS,
    TIMED_ARTIFACTS,
    TIMED_ENCHANTMENTS,
    UPKEEP_CREATURES,
    VARIABLE_CREATURES,
    VANILLA_CREATURES,
    VANILLA_WALLS,
    GameStatus,
    GameState,
    PlayerState,
    CardType,
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
)
from beta_magic.ui import (
    COPPER_CONTROL_DECK,
    COPPER_PRESSURE_DECK,
    MOONLIT_HORDE_DECK,
    RADIANT_CHARGE_DECK,
    STONEFIRE_DECK,
    VERDANT_TIDES_DECK,
    GameViewModel,
    make_demo_game,
    make_enchantment_test_game,
    make_timed_event_test_game,
    make_test_game,
    mana_text,
    parse_args,
)
from beta_magic.vanilla_creatures import HILL_GIANT


class DemoGameTests(unittest.TestCase):
    def test_demo_game_has_two_started_supported_card_decks(self) -> None:
        game = make_demo_game()
        self.assertEqual(len(game.players), 2)
        self.assertEqual(game.status, GameStatus.IN_PROGRESS)
        self.assertEqual(game.current_phase, TurnPhase.UNTAP)
        for player in game.players:
            all_cards = player.library + player.hand
        self.assertEqual(
            len(all_cards),
            len(BASIC_LANDS) * 5
            + len(DUAL_LANDS)
            + len(MANA_ARTIFACTS)
            + len(VANILLA_CREATURES)
            + len(MANA_CREATURES)
            + len(LANDWALK_CREATURES)
            + len(CREATURE_LORDS)
            + len(PUMP_CREATURES)
            + len(VANILLA_WALLS)
            + len(FLYING_CREATURES)
            + len(FIRST_STRIKE_CREATURES)
            + len(TRAMPLE_CREATURES)
            + len(GLOBAL_ENCHANTMENTS)
            + len(ENCHANT_CREATURES)
            + len(TARGETED_DAMAGE_SPELLS)
            + len(TARGETED_PUMP_SPELLS)
            + len(PERMANENT_DESTRUCTION_SPELLS)
            + len(GRAVEYARD_RECURSION_SPELLS)
            + len(TIMED_ARTIFACTS)
            + len(TIMED_ENCHANTMENTS)
            + len(UPKEEP_CREATURES)
            + len(VARIABLE_CREATURES),
        )

    def test_mana_display_only_lists_nonzero_colors(self) -> None:
        game = make_demo_game()
        player = game.players[0]
        self.assertEqual(mana_text(player), "empty")
        player.mana_pool.white = 2
        player.mana_pool.green = 1
        self.assertEqual(mana_text(player), "W:2 G:1")

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
        self.assertTrue(parse_args(["--test-decks"]).test_decks)
        self.assertTrue(
            parse_args(["--enchantment-test-decks"]).enchantment_test_decks
        )
        self.assertTrue(
            parse_args(["--timed-event-test-decks"]).timed_event_test_decks
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
        self.assertEqual(game.players[0].life, 19)
        self.assertEqual(view_model.state["timedEvent"], "")
        self.assertIn("Resolved timed event", view_model.state["message"])

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

        message = view_model.state["message"]
        self.assertIn("took 3 combat damage", message)
        self.assertIn("took 1 mana burn", message)


if __name__ == "__main__":
    unittest.main()
