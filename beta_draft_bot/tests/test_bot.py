import copy
import math
import random
import unittest

from beta_draft import DraftBot, DraftConfig, DraftContext, default_catalog


GREEN_RED = (["Grizzly Bears"] * 4 + ["Giant Spider"] * 3 + ["Llanowar Elves"] * 2
             + ["Hill Giant"] * 4 + ["Granite Gargoyle"] * 3 + ["Lightning Bolt"] * 3)
BLUE_BLACK = (["Phantom Monster"] * 4 + ["Prodigal Sorcerer"] * 2 + ["Air Elemental"] * 2
              + ["Terror"] * 3 + ["Black Knight"] * 3 + ["Sengir Vampire"] * 3)


def evaluation(bot, card, context=None):
    return bot.rank([card], context=context)[0]


class InterfaceTests(unittest.TestCase):
    def test_catalog_is_complete_and_all_cards_are_rankable(self):
        catalog = default_catalog()
        self.assertEqual(len(catalog), 292)
        cards = [c.name for c in catalog]
        self.assertEqual(len(set(cards)), 292)
        for pool in ([], GREEN_RED, BLUE_BLACK):
            rankings = DraftBot(pool=pool).rank(cards)
            self.assertEqual(len(rankings), 292)
            for result in rankings:
                self.assertEqual(cards[result.index], result.card)
                self.assertTrue(math.isfinite(result.score))
                self.assertAlmostEqual(result.score, sum(result.components.values()))
                self.assertTrue(result.reasons)

    def test_pick_remembers_exactly_one_card_per_call(self):
        bot = DraftBot()
        self.assertEqual(bot.pick(["Fireball", "Healing Salve"]), "Fireball")
        self.assertEqual(bot.pick(["Lightning Bolt", "Gray Ogre"]), "Lightning Bolt")
        self.assertEqual(bot.pool, ("Fireball", "Lightning Bolt"))

    def test_duplicate_cards_have_distinct_indices_and_no_four_copy_cap(self):
        bot = DraftBot()
        self.assertEqual([r.index for r in bot.rank(["Terror", "Terror"])], [0, 1])
        for _ in range(6):
            self.assertEqual(bot.pick_with_details(["Terror", "Terror"]).index, 0)
        self.assertEqual(bot.pool.count("Terror"), 6)

    def test_names_are_canonicalized_without_fuzzy_unknown_card_guesses(self):
        bot = DraftBot()
        self.assertEqual(bot.pick(["  lightning   BOLT "]), "Lightning Bolt")
        self.assertEqual(bot.pick(["Nevinyrral’s Disk"]), "Nevinyrral's Disk")
        with self.assertRaises(ValueError):
            bot.pick(["Lightning Boltt"])
        with self.assertRaises(ValueError):
            bot.pick(["Voltaic Key"])

    def test_bad_inputs_and_repeated_previews_do_not_mutate_state(self):
        bot = DraftBot(pool=["Fireball"])
        before = bot.to_dict()
        for bad in ([], ["Terror", "not a card"], "Terror", [None], None):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                bot.pick(bad)
            self.assertEqual(bot.to_dict(), before)
        for _ in range(3):
            bot.rank(["Terror", "Grizzly Bears"], context=DraftContext(1, 8, "pack-a"))
        self.assertEqual(bot.to_dict(), before)

    def test_color_plan_preview_can_include_current_pack_without_learning_it(self):
        bot = DraftBot(pool=["Grizzly Bears"])
        context = DraftContext(1, 10, "late-pack")
        before = bot.to_dict()
        baseline = bot.color_plans(context=context)
        preview = bot.color_plans(context=context, pack=["Air Elemental"])
        blue_weight = lambda plans: sum(plan.weight for plan in plans if "U" in plan.colors)

        self.assertGreater(blue_weight(preview), blue_weight(baseline))
        self.assertEqual(bot.to_dict(), before)

    def test_manual_override_must_be_in_pack(self):
        bot = DraftBot()
        bot.record_pick(["Fireball", "Gray Ogre"], "Gray Ogre")
        before = bot.to_dict()
        with self.assertRaises(ValueError):
            bot.record_pick(["Terror"], "Black Knight")
        self.assertEqual(bot.to_dict(), before)
        self.assertEqual(bot.pool, ("Gray Ogre",))

    def test_serialized_states_are_detached_and_validate_finite_signals(self):
        bot = DraftBot()
        bot.pick(["Lightning Bolt"], context=DraftContext(1, 6, "a"))
        state = bot.to_dict()
        state["pool"].append("Terror")
        self.assertEqual(len(bot.pool), 1)
        state["observations"][0]["evidence"]["R"] = float("nan")
        with self.assertRaises(ValueError):
            DraftBot.from_dict(state)
        for value in (2, True, "1"):
            invalid = bot.to_dict()
            invalid["schema_version"] = value
            with self.assertRaises(ValueError):
                DraftBot.from_dict(invalid)

    def test_configuration_and_context_validation(self):
        for fields in ({"total_picks": 0}, {"pack_size": True}, {"table_size": -1},
                       {"allow_ante": "false"}, {"chaos_orb_hit_rate": float("nan")},
                       {"chaos_orb_hit_rate": 2}, {"banned_cards": "Sol Ring"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                DraftConfig(**fields)
        with self.assertRaises(ValueError):
            DraftBot().pick(["Terror"], context=DraftContext(1, 16))
        with self.assertRaises(ValueError):
            DraftContext(0, 1)

    def test_custom_pack_size_and_explicit_context_resume(self):
        bot = DraftBot(config=DraftConfig(pack_size=3, total_picks=9, table_size=2))
        bot.pick(["Terror"], context=DraftContext(2, 3))
        bot = DraftBot.from_dict(bot.to_dict())
        bot.pick(["Fireball"])
        self.assertEqual(bot.to_dict()["last_context"], {"pack_number": 3, "pick_number": 1, "pack_id": None})


class StrategyTests(unittest.TestCase):
    def test_historical_rules_are_reflected_in_sensitive_card_ratings(self):
        cards = {card.name: card for card in default_catalog()}
        self.assertGreater(cards["Power Surge"].rating, 1.0)
        self.assertIn("Mana burn", cards["Power Surge"].note)
        self.assertGreater(cards["Camouflage"].rating, 1.0)
        self.assertIn("deliberately rearrange", cards["Camouflage"].note)
        self.assertGreater(cards["Conservator"].rating, 0.8)
        self.assertIn("life loss", cards["Conservator"].note)
        self.assertIn("continuous artifact", cards["Twiddle"].note)

    def test_bombs_and_removal_beat_famous_but_unsupported_cards(self):
        bot = DraftBot()
        self.assertEqual(bot.pick(["Time Vault", "Fastbond", "Black Lotus", "Fireball"]), "Fireball")
        self.assertEqual(DraftBot().pick(["Sol Ring", "Craw Wurm", "Mox Emerald"]), "Sol Ring")

    def test_early_flexibility_and_late_color_commitment(self):
        self.assertEqual(DraftBot(pool=["Grizzly Bears"]).pick(["Fireball", "Ironroot Treefolk"]), "Fireball")
        late = DraftBot(pool=BLUE_BLACK + ["Phantom Monster", "Black Knight"] * 4)
        self.assertEqual(late.pick(["Serra Angel", "Phantom Monster"]), "Phantom Monster")

    def test_junk_and_free_basics_do_not_anchor_a_color(self):
        bot = DraftBot(pool=["Purelace"] * 12 + ["Plains"] * 12)
        self.assertEqual(bot.pick(["Healing Salve", "Sengir Vampire"]), "Sengir Vampire")

    def test_real_fixing_can_make_a_powerful_splash_worth_picking(self):
        no_fixing = DraftBot(pool=GREEN_RED + ["War Mammoth"] * 4)
        fixed = DraftBot(pool=GREEN_RED + ["War Mammoth"] * 4 + ["Savannah", "Plateau", "Mox Pearl"])
        self.assertEqual(no_fixing.pick(["Swords to Plowshares", "Uthden Troll"]), "Uthden Troll")
        self.assertEqual(fixed.pick(["Swords to Plowshares", "Uthden Troll"]), "Swords to Plowshares")

    def test_relevant_dual_beats_irrelevant_dual_and_gains_from_existing_splash(self):
        bot = DraftBot(pool=GREEN_RED)
        self.assertEqual(bot.pick(["Underground Sea", "Taiga"]), "Taiga")
        without = evaluation(DraftBot(pool=GREEN_RED), "Savannah").components["fixing"]
        with_splash = evaluation(DraftBot(pool=GREEN_RED + ["Swords to Plowshares"]), "Savannah").components["fixing"]
        self.assertGreater(with_splash, without + 0.6)

    def test_colorless_acceleration_does_not_make_black_x_cost_splashable(self):
        bot = DraftBot(pool=GREEN_RED + ["Sol Ring", "Mana Vault", "Black Lotus"])
        self.assertEqual(bot.pick(["Drain Life", "Disintegrate"]), "Disintegrate")

    def test_black_mana_payoffs_improve_in_heavy_black(self):
        mono = DraftBot(pool=["Black Knight", "Terror", "Sengir Vampire", "Paralyze"] * 5)
        two = DraftBot(pool=["Black Knight", "Terror", "Granite Gargoyle", "Lightning Bolt"] * 5)
        for card in ("Drain Life", "Nightmare", "Frozen Shade"):
            with self.subTest(card=card):
                self.assertGreater(evaluation(mono, card).score, evaluation(two, card).score)

    def test_curve_saturation_moves_priority_to_early_creatures(self):
        bot = DraftBot(pool=["Craw Wurm"] * 6 + ["Ironroot Treefolk"] * 4 + ["Giant Spider"] * 4
                      + ["Giant Growth"] * 3 + ["Hurricane"] * 2)
        self.assertEqual(bot.pick(["Craw Wurm", "Grizzly Bears"]), "Grizzly Bears")

    def test_creature_shortage_can_beat_excess_removal(self):
        bot = DraftBot(pool=["Terror"] * 7 + ["Paralyze"] * 5 + ["Weakness"] * 4
                      + ["Mind Twist"] * 2 + ["Demonic Tutor"] * 2 + ["Raise Dead"] * 3)
        self.assertEqual(bot.pick(["Terror", "Black Knight"]), "Black Knight")

    def test_lure_combo_recognized_in_both_pick_orders(self):
        green = ["Grizzly Bears", "Giant Spider", "Scryb Sprites"] * 4
        first = evaluation(DraftBot(pool=green), "Lure").components["synergy"]
        supported = evaluation(DraftBot(pool=green + ["Thicket Basilisk"]), "Lure").components["synergy"]
        self.assertGreater(supported, first + 1.0)
        plain = evaluation(DraftBot(pool=green), "Thicket Basilisk").score
        paired = evaluation(DraftBot(pool=green + ["Lure"]), "Thicket Basilisk").score
        self.assertGreater(paired, plain + 0.9)

    def test_channel_synergy_does_not_mistake_drain_life_for_fireball(self):
        pool = ["Grizzly Bears", "Giant Spider", "Lightning Bolt"] * 4
        fireball = evaluation(DraftBot(pool=pool + ["Fireball"]), "Channel")
        drain = evaluation(DraftBot(pool=pool + ["Drain Life"]), "Channel")
        self.assertGreater(fireball.components["synergy"], drain.components["synergy"] + 1)

    def test_time_vault_requires_actual_untapping_and_animation(self):
        pool = ["Phantom Monster", "Giant Spider", "Grizzly Bears"] * 3
        plain = evaluation(DraftBot(pool=pool), "Time Vault")
        icy = evaluation(DraftBot(pool=pool + ["Icy Manipulator"]), "Time Vault")
        energy = evaluation(DraftBot(pool=pool + ["Instill Energy"]), "Time Vault")
        twiddle = evaluation(DraftBot(pool=pool + ["Twiddle"]), "Time Vault")
        engine = evaluation(DraftBot(pool=pool + ["Animate Artifact", "Instill Energy"]), "Time Vault")
        self.assertEqual(icy.components["synergy"], plain.components["synergy"])
        self.assertEqual(energy.components["synergy"], plain.components["synergy"])
        self.assertGreater(twiddle.components["synergy"], 0.8)
        self.assertGreater(engine.components["synergy"], twiddle.components["synergy"])

    def test_beta_mana_burn_rewards_sinks_and_power_surge_pressure(self):
        pressure = ["Savannah Lions", "White Knight", "Mesa Pegasus"] * 3
        slow = ["Craw Wurm", "Mahamoti Djinn", "Force of Nature"] * 3
        self.assertGreater(
            evaluation(DraftBot(pool=pressure), "Power Surge").components["synergy"],
            evaluation(DraftBot(pool=slow), "Power Surge").components["synergy"],
        )
        plain = evaluation(DraftBot(pool=["Firebreathing"]), "Sol Ring").components["synergy"]
        sinks = evaluation(DraftBot(pool=["Firebreathing", "Rod of Ruin", "Jayemdae Tome"]), "Sol Ring").components["synergy"]
        self.assertGreater(sinks, plain)

    def test_icy_manipulator_can_switch_off_meekstone(self):
        pool = ["Savannah Lions", "White Knight", "Mesa Pegasus"] * 3
        plain = evaluation(DraftBot(pool=pool), "Icy Manipulator").components["synergy"]
        meekstone = evaluation(DraftBot(pool=pool + ["Meekstone"]), "Icy Manipulator").components["synergy"]
        self.assertGreater(meekstone, plain + 0.5)

    def test_plague_rats_density_becomes_a_real_plan(self):
        self.assertEqual(DraftBot().pick(["Plague Rats", "Scathe Zombies"]), "Scathe Zombies")
        rats = DraftBot(pool=["Plague Rats"] * 6)
        self.assertEqual(rats.pick(["Plague Rats", "Scathe Zombies"]), "Plague Rats")
        self.assertIn("B", rats.color_plans()[0].colors)

    def test_sedge_troll_and_pestilence_receive_specific_support(self):
        red = ["Lightning Bolt", "Hill Giant", "Granite Gargoyle"] * 4
        before = evaluation(DraftBot(pool=red), "Sedge Troll").components["synergy"]
        after = evaluation(DraftBot(pool=red + ["Badlands"]), "Sedge Troll").components["synergy"]
        self.assertGreater(after, before + 0.5)
        black_white = ["Terror", "Black Knight", "Swords to Plowshares", "Serra Angel"] * 3
        ordinary = evaluation(DraftBot(pool=black_white), "Pestilence").components["synergy"]
        protected = evaluation(DraftBot(pool=black_white + ["White Knight"]), "Pestilence").components["synergy"]
        self.assertGreater(protected, ordinary + 0.35)

    def test_ante_dexterity_and_custom_exclusions(self):
        pack = ["Contract from Below", "Chaos Orb", "Grizzly Bears"]
        self.assertEqual(DraftBot().pick(pack), "Grizzly Bears")
        self.assertEqual(DraftBot(config=DraftConfig(allow_ante=True)).pick(pack), "Contract from Below")
        dexterity = DraftBot(config=DraftConfig(allow_dexterity=True, chaos_orb_hit_rate=1))
        self.assertEqual(dexterity.pick(["Chaos Orb", "Grizzly Bears"]), "Chaos Orb")
        banned = DraftBot(config=DraftConfig(banned_cards=("Sol Ring",)))
        self.assertEqual(banned.pick(["Sol Ring", "Grizzly Bears"]), "Grizzly Bears")
        forced = DraftBot().pick_with_details(["Darkpact", "Demonic Attorney"])
        self.assertFalse(forced.eligible)
        self.assertEqual(forced.index, 0)
        self.assertEqual(DraftBot().pick(["Contract from Below", "Island"]), "Island")

    def test_repeated_sideboard_cards_have_diminishing_value(self):
        pool = ["Lightning Bolt", "Granite Gargoyle", "Hill Giant"] * 4
        first = evaluation(DraftBot(pool=pool), "Red Elemental Blast").score
        third = evaluation(DraftBot(pool=pool + ["Red Elemental Blast"] * 2), "Red Elemental Blast").score
        self.assertGreater(first, third + 0.9)


class SignalTests(unittest.TestCase):
    def test_opening_pack_has_no_availability_signal(self):
        bot = DraftBot()
        bot.pick(["Fireball", "Lightning Bolt"], context=DraftContext(1, 1, "a"))
        evidence = bot.to_dict()["observations"][0]["evidence"]
        self.assertTrue(all(value == 0 for value in evidence.values()))

    def test_late_quality_is_learned_and_wheels_do_not_double_count(self):
        bot = DraftBot()
        context = DraftContext(1, 7, "same-pack")
        bot.record_pick(["Fireball", "Grizzly Bears"], "Grizzly Bears", context=context)
        before = copy.deepcopy(bot.to_dict()["observations"])
        bot.record_pick(["Fireball", "Grizzly Bears"], "Grizzly Bears", context=context)
        self.assertEqual(bot.to_dict()["observations"], before)
        self.assertGreater(before[0]["evidence"]["R"], 0)
        weights = lambda ctx: sum(p.weight for p in bot.color_plans(context=ctx) if "R" in p.colors)
        self.assertGreater(weights(DraftContext(1, 8)), weights(DraftContext(2, 1)))
        self.assertGreater(weights(DraftContext(3, 1)), weights(DraftContext(2, 1)))

    def test_inferred_seat_identity_is_reused_on_wheel(self):
        bot = DraftBot()
        bot.pick(["Fireball"], context=DraftContext(1, 2))
        bot.pick(["Lightning Bolt"], context=DraftContext(1, 10))
        self.assertEqual(len(bot.to_dict()["observations"]), 1)


class IntegrationTests(unittest.TestCase):
    def test_eight_seats_three_rounds_conserve_cards_and_keep_separate_pools(self):
        # Arbitrary Beta packs, deliberately not claiming historical print collation.
        rng = random.Random(72)
        names = [card.name for card in default_catalog()]
        bots = [DraftBot() for _ in range(8)]
        opened = []
        for round_number in range(1, 4):
            packs = [rng.sample(names, 15) for _ in bots]
            identities = [f"round-{round_number}-origin-{seat}" for seat in range(8)]
            opened.extend(name for pack in packs for name in pack)
            direction = 1 if round_number % 2 else -1
            for pick_number in range(1, 16):
                for seat, bot in enumerate(bots):
                    pack = packs[seat]
                    choice = bot.pick_with_details(pack, context=DraftContext(round_number, pick_number, identities[seat]))
                    self.assertEqual(pack.pop(choice.index), choice.card)
                    self.assertEqual(len(pack), 15 - pick_number)
                passed = [None] * 8
                passed_ids = [None] * 8
                for seat in range(8):
                    passed[(seat + direction) % 8] = packs[seat]
                    passed_ids[(seat + direction) % 8] = identities[seat]
                packs, identities = passed, passed_ids
        self.assertTrue(all(len(bot.pool) == 45 for bot in bots))
        self.assertCountEqual(opened, [name for bot in bots for name in bot.pool])
        self.assertGreater(len({bot.pool for bot in bots}), 1)


if __name__ == "__main__":
    unittest.main()
