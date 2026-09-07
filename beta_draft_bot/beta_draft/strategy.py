"""Explainable, pool-aware heuristics; no game simulation or deck construction.

We marginalize over five mono-color and ten two-color hypotheses. Ratings are
original estimates, not trained win rates. Heuristic constants live here so
real draft feedback can be used to tune them without changing the interface.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import math

from .cards import Card, COLORS, normalize_name
from .models import ColorPlan, DraftConfig, PickEvaluation


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def eligible(card: Card, config: DraftConfig) -> bool:
    return not (
        (card.has("ante") and not config.allow_ante)
        or (card.has("dexterity") and not config.allow_dexterity)
        or normalize_name(card.name) in {normalize_name(n) for n in config.banned_cards}
    )


def splashable(card: Card) -> bool:
    recurring = {f"{word}_mana" for word in ("white", "blue", "black", "red", "green")}
    return (len(card.colors) == 1 and card.pips == 1 and card.rating >= 3.0
            and not card.has("no_splash") and not recurring.intersection(card.tags)
            and not card.has("island_required")
            and (card.curve_cost >= 3 or card.has("splashable")))


def pool_rating(card: Card, pool: tuple[Card, ...]) -> float:
    # A drafted rat cluster is genuine black commitment, despite each isolated
    # rat's low initial rating. Do not discount the whole cluster as junk.
    if card.name == "Plague Rats":
        copies = sum(c.name == card.name for c in pool)
        return card.rating + min(2.8, 0.68 * max(0, copies - 1))
    return card.rating


def fixing_sources(pool: tuple[Card, ...], main: tuple[str, ...], color: str) -> float:
    """Persistent independent sources; no imaginary fixing from uncastable Birds.

Duals must share a main color. Wild Growth and Sol Ring cannot fix a red splash.
Black Lotus is not counted as a persistent source. Basic lands are supplied free
and are modeled separately, not inferred from drafted copies.
"""
    sources = 0.0
    for card in pool:
        if card.has("basic") or color not in card.produced_mana:
            continue
        if card.has("dual"):
            sources += float(bool(set(card.produced_mana).intersection(main)))
        elif card.has("mox"):
            sources += 1.0
        elif card.name == "Birds of Paradise" and "G" in main:
            sources += 0.8
        elif card.name == "Celestial Prism":
            sources += 0.45
        elif card.name == "Sunglasses of Urza" and "W" in main and color == "R":
            sources += 0.4
    return sources


def availability(card: Card, pool: tuple[Card, ...], main: tuple[str, ...]) -> float:
    if set(card.colors).issubset(main):
        return 1.0
    if not splashable(card):
        return 0.0
    color = card.colors[0]
    sources = fixing_sources(pool, main, color)
    value = min(0.82, 0.12 + 0.19 * sources)
    # A light splash can use a basic, but each extra off-color spell stretches it.
    existing = [c for c in pool if c.colors == (color,) and splashable(c)]
    value /= 1 + 0.20 * max(0, len(existing) - 2)
    other_splashes = {c.colors[0] for c in pool if splashable(c)
                      and c.colors[0] not in main and c.colors[0] != color}
    if any(fixing_sources(pool, main, c) >= 0.8 for c in other_splashes):
        value *= 0.65
    return value


def color_plans(pool: tuple[Card, ...], signals: dict[str, float], progress: float) -> tuple[ColorPlan, ...]:
    support = Counter()
    for card in pool:
        if card.colors and not card.has("sideboard"):
            weight = max(0, pool_rating(card, pool) - 1.45) ** 1.3
            support[card.colors[0]] += weight
    options = [(c,) for c in COLORS] + list(combinations(COLORS, 2))
    utilities = []
    for main in options:
        utility = sum(support[c] for c in main) - 1.1 * (len(main) - 1)
        utility += 1.25 * sum(signals.get(c, 0.0) for c in main)
        # Committing to a mono-color mana payoff is an option, not a fixed rule.
        if len(main) == 1:
            payoff = sum(c.colors == main and c.has("no_splash") for c in pool)
            utility += min(2.0, payoff * 0.4)
        utilities.append(utility)
    temperature = 3.0 - 0.8 * progress
    highest = max(utilities)
    weights = [math.exp((u - highest) / temperature) for u in utilities]
    total = sum(weights)
    return tuple(ColorPlan(tuple(main), w / total) for main, w in zip(options, weights))


@dataclass
class PoolView:
    pool: tuple[Card, ...]
    main: tuple[str, ...]

    def __post_init__(self):
        self.main_cards = tuple(c for c in self.pool if set(c.colors).issubset(self.main))
        self.playables = tuple(c for c in self.main_cards if pool_rating(c, self.pool) >= 1.5
                               and not c.is_land and not c.has("sideboard"))
        self.bodies = tuple(c for c in self.playables if c.has("body"))
        self.attackers = tuple(c for c in self.bodies if c.attacks)
        self.spells = len(self.playables)
        self.names = Counter()
        for c in self.pool:
            self.names[c.name] += availability(c, self.pool, self.main)
        demand = Counter({c: 4.0 for c in self.main})
        for c in self.playables:
            if c.colors:
                demand[c.colors[0]] += max(0.2, pool_rating(c, self.pool) - 1.4) * (c.pips + 0.4)
        if len(self.main) == 1:
            self.land_sources = {self.main[0]: 17.0}
        else:
            first = self.main[0]
            count = clamp(17 * demand[first] / sum(demand.values()), 5.5, 11.5)
            self.land_sources = {first: count, self.main[1]: 17 - count}

    def count(self, name: str) -> float:
        return self.names[name]

    def tagged(self, tag: str) -> int:
        return sum(c.has(tag) for c in self.playables)

    def sources(self, color: str) -> float:
        if color in self.main:
            # Duals are part of the 17 lands; count their additional color access
            # conservatively rather than pretending every dual is an extra land.
            extras = fixing_sources(self.pool, self.main, color)
            return min(20.0, self.land_sources[color] + 0.65 * extras)
        return min(5.0, 1.0 + fixing_sources(self.pool, self.main, color))


def mana_burden(card: Card, view: PoolView) -> float:
    if not card.colors or not set(card.colors).issubset(view.main):
        return 0.0  # off-color reliability is priced in availability instead
    sources = round(view.sources(card.colors[0]))
    draws = min(14, 6 + max(1, round(card.curve_cost)))
    # Hypergeometric colored-source estimate, not a claim to model every land drop.
    need = card.pips
    denominator = math.comb(40, draws)
    success = sum(math.comb(sources, hits) * math.comb(40 - sources, draws - hits)
                  for hits in range(need, min(sources, draws) + 1)
                  if 0 <= draws - hits <= 40 - sources) / denominator
    target = 0.85 if card.curve_cost <= 3 else 0.80
    return -1.65 * max(0.0, target - success)


# Symmetric pick-order recognition. Each edge is capped at one effective partner:
# drawing two specific cards is uncertain; duplicates must not create runaway scores.
PAIRS = (
    ("Lure", "Thicket Basilisk", 1.55, "Lure plus Basilisk can destroy multiple forced blockers."),
    ("Lure", "Cockatrice", 1.55, "Lure plus Cockatrice can punish multiple legal blockers."),
    ("Lure", "Drudge Skeletons", 0.40, "A regenerating Lure carrier can free your other attackers."),
    ("Pestilence", "White Knight", 0.65, "Protection from black helps keep a creature alive through Pestilence."),
    ("Pestilence", "Black Ward", 0.55, "Black Ward can protect a creature from your Pestilence."),
    ("Pestilence", "Circle of Protection: Black", 0.50, "The Circle can prevent your own Pestilence damage to you."),
    ("Pestilence", "Fungusaur", 0.45, "Controlled nonlethal damage can grow Fungusaur."),
    ("Royal Assassin", "Icy Manipulator", 0.80, "Icy supplies tapped targets for Royal Assassin."),
    ("Royal Assassin", "Nettling Imp", 0.55, "Forced attacks can expose creatures to Royal Assassin."),
    ("Royal Assassin", "Twiddle", 0.40, "Twiddle can supply a tapped target or another Assassin activation."),
    ("Nettling Imp", "Icy Manipulator", 0.60, "Tapping a creature forced to attack can make it die at end step."),
    ("Siren's Call", "Icy Manipulator", 0.45, "Tapping eligible creatures can improve the forced-attack effect."),
    ("Channel", "Fireball", 2.70, "Channel can fund Fireball's X, if life and a red source are available."),
    ("Channel", "Disintegrate", 2.50, "Channel can fund Disintegrate's X, with life and red mana still required."),
    ("Channel", "Rock Hydra", 1.20, "Channel can produce a large Hydra, but cannot pay its red pips."),
    ("Winter Orb", "Icy Manipulator", 1.00, "Icy can tap Winter Orb before your untap to break its symmetry."),
    ("Howling Mine", "Icy Manipulator", 0.60, "Icy can turn off Howling Mine for the opponent's draw step."),
    ("Meekstone", "Icy Manipulator", 0.65, "Icy can turn off Meekstone before your untap step."),
    ("Time Vault", "Twiddle", 1.55, "Each Twiddle can untap Time Vault for one extra turn; this is not infinite."),
    ("Instill Energy", "Royal Assassin", 1.10, "A creature able to tap can get another activation from Instill Energy."),
    ("Instill Energy", "Prodigal Sorcerer", 1.15, "Untapping an established pinger gives another damage activation."),
    ("Instill Energy", "Orcish Artillery", 0.90, "A second Artillery activation is powerful but also costs more life."),
    ("Instill Energy", "Pirate Ship", 0.70, "Untapping an established Pirate Ship gives another ping."),
    ("Instill Energy", "Demonic Hordes", 0.65, "Untapping established Hordes can destroy another land."),
    ("Ley Druid", "Wild Growth", 0.55, "Untapping a land enchanted with Wild Growth produces extra mana."),
    ("Meekstone", "Serra Angel", 0.55, "Serra's vigilance lets it attack without needing to untap."),
    ("Berserk", "Giant Growth", 0.30, "Additional power increases Berserk's damage, at a multi-card risk."),
    ("Berserk", "Force of Nature", 0.50, "A large trampling body makes Berserk a potential finisher."),
    ("Dingus Egg", "Armageddon", 0.80, "Mass land destruction triggers the Egg for both players."),
    ("Lich", "Stream of Life", 0.75, "Lich can convert life gain into cards, but the overall plan remains fragile."),
    ("Kormus Bell", "Pestilence", -1.10, "Pestilence can destroy your own animated Swamps."),
)


def synergies(card: Card, view: PoolView) -> tuple[float, list[str]]:
    score = 0.0
    notes = []

    def add(value: float, reason: str):
        nonlocal score
        score += value
        if abs(value) >= 0.20:
            notes.append(reason)

    for a, b, value, reason in PAIRS:
        partner = b if card.name == a else a if card.name == b else None
        if partner and view.count(partner):
            add(value * min(1.0, view.count(partner)), reason)

    # An actual three-card engine, without pretending Instill Energy can enchant
    # an unanimated artifact. All three colors/casting requirements still apply.
    engine = {"Time Vault", "Animate Artifact", "Instill Energy"}
    if card.name in engine:
        partners = engine - {card.name}
        ready = min(view.count(name) for name in partners)
        if ready:
            add(2.7 * min(1.0, ready), "Animate Artifact plus Instill Energy can repeatedly untap Time Vault, once each extra turn.")

    if card.name == "Plague Rats":
        add(min(2.8, 0.68 * view.count("Plague Rats")), "Additional Plague Rats improve the rat-density plan; there is no Limited four-copy cap.")
    if card.name == "Sedge Troll":
        # Only Swamps grant the stat bonus; a Mox Jet alone only grants regeneration.
        swamp = "B" in view.main or any("Swamp" in c.type_line and c.is_land
                                        and set(c.produced_mana).intersection(view.main) for c in view.pool)
        add((0.65 if swamp else 0.0) + (0.35 if view.sources("B") >= 1.8 else 0.0),
            "A Swamp enables the stat bonus, while black mana enables regeneration.")
    if card.name in {"Drain Life", "Frozen Shade", "Nightmare", "Pestilence", "Demonic Hordes", "Force of Nature", "Gaea's Liege", "Aspect of Wolf", "Blessing"}:
        color = card.colors[0]
        sources = view.sources(color)
        if card.name in {"Nightmare", "Gaea's Liege", "Aspect of Wolf"}:
            sources = view.land_sources.get(color, 0.0)
        add(clamp((sources - 10) * 0.12, -1.1, 0.85), "This card rewards a dense supply of its color or basic land type.")
    lords = {"Lord of Atlantis": "Merfolk", "Goblin King": "Goblin", "Zombie Master": "Zombie"}
    for lord, tribe in lords.items():
        if card.name == lord:
            allies = sum(tribe in c.type_line.split(" — ")[-1].split() for c in view.main_cards if c.is_creature)
            add(min(1.25, allies * 0.30), f"Your existing {tribe} creatures support {lord}.")
        elif card.is_creature and tribe in card.type_line.split(" — ")[-1].split():
            add(min(1.1, 0.45 * view.count(lord)), f"An existing {lord} improves this tribal creature.")
    if card.name in {"Crusade", "Bad Moon", "Gauntlet of Might"}:
        color = {"Crusade": "W", "Bad Moon": "B", "Gauntlet of Might": "R"}[card.name]
        allies = sum(c.colors == (color,) and c.is_creature for c in view.playables)
        add(min(1.65, allies * 0.23), "Enough creatures of the matching color improve this symmetric anthem.")
        if card.name == "Gauntlet of Might" and "R" in view.main:
            add(view.land_sources["R"] * 0.075, "Mountains also benefit from the Gauntlet's mana bonus.")
    if card.is_creature and card.colors:
        anthem = {"W": "Crusade", "B": "Bad Moon", "R": "Gauntlet of Might"}.get(card.colors[0])
        if anthem:
            add(min(0.6, view.count(anthem) * 0.35), f"Your existing {anthem} improves this creature.")
    if card.name == "Verduran Enchantress":
        good = sum(c.is_enchantment and c.rating >= 1.75 and not c.has("sideboard") for c in view.playables)
        add(min(1.85, good * 0.25), "Playable enchantments supply real Enchantress triggers without requiring filler Auras.")
    if card.is_enchantment and card.rating >= 1.75:
        add(min(0.45, 0.30 * view.count("Verduran Enchantress")), "An existing Enchantress can replace this enchantment in hand.")
    if card.name == "Copy Artifact":
        best = max((c.rating for c in view.playables if c.is_artifact), default=0)
        add(clamp((best - 2) * 0.4, 0, 1.2), "Your strong artifacts provide reliable copy targets.")
    if card.name == "Animate Artifact":
        best = max((c.mana_value for c in view.playables if c.is_artifact and not c.is_creature), default=0)
        add(min(0.65, max(0, best - 2) * 0.18), "An existing noncreature artifact supplies an animation target.")
    if card.name == "Animate Wall":
        power = max((c.combat_power for c in view.bodies if c.has("defender")), default=0)
        add(min(0.95, max(0, power - 1) * 0.4), "Your higher-power Walls make animation more useful.")
    if card.name in {"Lure", "Berserk", "Giant Growth", "Unholy Strength", "Holy Strength", "Invisibility", "Flight"}:
        if len(view.attackers) < 3:
            add(-0.2, "Combat support needs enough useful attackers.")
        elif len(view.attackers) >= 8:
            add(0.2, "The pool has enough attackers to support this combat effect.")
    if card.name in {"Keldon Warlord", "Orcish Oriflamme", "Raging River", "Helm of Chatzuk"}:
        add(clamp((len(view.attackers) - 4) * 0.12, -0.4, 0.9), "This effect scales with a broad attacking board, not just defensive creatures.")
    if card.name == "Lord of the Pit":
        fodder = sum(c.is_creature and c.curve_cost <= 3 for c in view.bodies)
        add(clamp((fodder - 4) * 0.15, -0.6, 0.6) + min(0.5, view.count("The Hive") * 0.5),
            "The recurring sacrifice requirement needs cheap creatures or repeatable tokens.")
    if card.name in {"Regrowth", "Demonic Tutor"}:
        best = max((c.rating for c in view.playables), default=0)
        add(clamp((best - 3.6) * 0.3, 0, 0.5), "Access to an existing bomb raises the value of selection or recursion.")
    if card.name in {"Animate Dead", "Resurrection", "Raise Dead"}:
        targets = sum(c.is_creature and c.rating >= 3.2 for c in view.bodies)
        add(min(0.35, 0.08 * targets), "Strong creatures in the pool improve recursion targets.")
    cheap = sum(c.attacks and c.curve_cost <= 2 for c in view.playables)
    rocks = sum(c.is_artifact and (c.has("ramp") or c.has("burst_ramp")) for c in view.playables)
    expensive = sum(c.curve_cost >= 5 for c in view.playables)
    if card.name in {"Armageddon", "Winter Orb", "Black Vise", "Ankh of Mishra", "Manabarbs", "Power Surge"}:
        add(clamp(cheap * 0.10 + rocks * 0.12 - expensive * 0.07 - 0.15, -0.65, 0.9),
            "Cheap pressure and nonland mana make symmetric resource denial easier to exploit.")
    if card.has("mana_sink"):
        excess = sum(c.has("ramp") or c.has("burst_ramp") for c in view.playables)
        add(min(0.45, excess * 0.08),
            "A repeatable mana sink makes excess mana safer under the mana-burn rules.")
    if card.has("ramp") or card.has("burst_ramp"):
        sinks = sum(c.has("mana_sink") for c in view.playables)
        add(min(0.35, sinks * 0.07),
            "Existing mana sinks reduce the mana-burn risk of excess acceleration.")
    if card.name == "Balance":
        add(clamp(rocks * 0.18 - max(0, len(view.bodies) - 7) * 0.04, -0.4, 0.65),
            "Artifact mana and fewer committed creatures improve Balance's symmetry.")
    if card.has("refill"):
        add(clamp(cheap * 0.13 + rocks * 0.08 - expensive * 0.10 - view.tagged("draw") * 0.15, -0.7, 0.8),
            "Symmetric refills favor a pool that empties its own hand first.")
    if card.name == "Dark Ritual":
        payoff = sum(c.colors == ("B",) and 3 <= c.curve_cost <= 5 and c.rating >= 3.5 for c in view.playables)
        add(min(0.65, payoff * 0.22), "Impactful black three-to-five-drops make temporary acceleration more worthwhile.")
    if card.name in {"Pestilence", "Earthquake", "Hurricane", "Wrath of God", "Nevinyrral's Disk"}:
        if card.name == "Pestilence":
            fragile = sum(c.is_creature and c.toughness == "1" and c.name != "White Knight" for c in view.bodies)
            durable = sum(c.is_creature and c.toughness is not None and c.toughness.isdigit()
                          and int(c.toughness) >= 4 for c in view.bodies)
            add(clamp(durable * 0.10 - fragile * 0.07, -0.65, 0.5), "Pestilence is easier to sustain with durable creatures and fewer fragile allies.")
        elif card.name in {"Earthquake", "Hurricane"}:
            flying = sum("Flying" in c.keywords for c in view.bodies)
            value = flying * (0.08 if card.name == "Earthquake" else -0.10)
            add(clamp(value, -0.65, 0.55), "Earthquake spares flyers; Hurricane damages your own flyers as well as opposing ones.")
        else:
            add(-min(0.5, max(0, len(view.bodies) - 10) * 0.06), "A creature-heavy pool pays more of the cost of a symmetric reset.")
    if card.name == "Meekstone":
        locked = sum(c.combat_power >= 3 and "Vigilance" not in c.keywords for c in view.attackers)
        add(clamp(cheap * 0.08 - locked * 0.16, -1, 0.6), "Meekstone can lock your own large nonvigilant attackers.")
    if card.name == "Smoke":
        add(-min(0.7, max(0, len(view.attackers) - 3) * 0.08), "Smoke becomes worse when you need to untap many attackers.")
    if card.name == "Tranquility":
        add(-min(0.75, sum(c.is_enchantment for c in view.playables) * 0.12), "Tranquility also destroys your enchantments.")
    if card.name in {"Karma", "Tsunami", "Flashfires", "Conversion"}:
        harmed = {"Karma": "B", "Tsunami": "U", "Flashfires": "W", "Conversion": "R"}[card.name]
        if harmed in view.main:
            add(-0.65, "This hoser also conflicts with your own mana base.")
    return clamp(score, -2.0, 3.0), notes


def needs(card: Card, view: PoolView, progress: float) -> float:
    if card.is_land or card.has("sideboard") or card.rating < 1.0:
        return 0.0
    n = max(5, view.spells)
    score = 0.0
    if card.has("body"):
        score += clamp((0.60 * (n + 1) - len(view.bodies)) * 0.18, -0.5, 0.9)
        if card.attacks and card.curve_cost <= 3:
            early = sum(c.attacks and c.curve_cost <= 3 for c in view.bodies)
            score += clamp((n * 0.28 - early) * 0.18, -0.30, 0.65)
        if card.has("defender") or not card.attacks:
            score -= min(0.75, max(0, sum(not c.attacks for c in view.bodies) - 2) * 0.20)
    if card.has("removal") and not card.has("sweeper"):
        score += clamp((n * 0.20 - view.tagged("removal")) * 0.17, -0.7, 0.65)
    if card.has("draw"):
        score += clamp((n * 0.09 - view.tagged("draw")) * 0.17, -0.7, 0.30)
    if card.has("trick") or (card.has("aura") and not card.has("removal") and not card.has("body")):
        count = sum(c.has("trick") or (c.has("aura") and not c.has("removal")) for c in view.playables)
        score -= min(1.0, max(0, count - 2) * 0.18)
        if len(view.attackers) < n * 0.35:
            score -= 0.30
    if card.has("ramp") or card.has("burst_ramp"):
        ramp = sum(c.has("ramp") or c.has("burst_ramp") for c in view.playables)
        expensive = sum(c.curve_cost >= 5 for c in view.playables)
        score += clamp((expensive - 2) * 0.07, -0.1, 0.4)
        score -= min(1.1, max(0, ramp - 3) * 0.25)
    if card.curve_cost >= 5:
        top = sum(c.curve_cost >= 5 for c in view.playables)
        ramp = sum(c.has("ramp") or c.has("burst_ramp") for c in view.playables)
        score -= clamp((top - max(2, n * 0.20) - ramp * 0.4) * 0.27, 0, 1.35)
    return score * (0.25 + 0.75 * progress)


def fixing_value(card: Card, view: PoolView) -> float:
    if not card.has("fixing"):
        return 0.0
    shortages = {}
    for c in view.pool:
        if splashable(c) and c.colors[0] not in view.main:
            color = c.colors[0]
            need = clamp((c.rating - 3.0) * 0.85, 0, 1.7)
            need /= 1 + 0.65 * fixing_sources(view.pool, view.main, color)
            shortages[color] = max(shortages.get(color, 0), need)
    enabled = max((shortages.get(color, 0) for color in card.produced_mana), default=0)
    overlap = len(set(card.produced_mana).intersection(view.main))
    if card.has("dual"):
        if overlap == 2:
            return 0.95 + min(0.35, sum(c.pips >= 2 for c in view.playables) * 0.04)
        if overlap == 1:
            return -0.55 + 1.65 * enabled
        return -1.45
    if card.has("mox"):
        return (0.30 if overlap else 0.0) + 0.55 * enabled
    if card.name == "Birds of Paradise":
        return (0.15 if len(view.main) == 2 else 0.0) + 0.65 * enabled
    if card.name == "Celestial Prism":
        return 1.45 * enabled - 0.20
    if card.name == "Sunglasses of Urza":
        return (0.4 + enabled) if "W" in view.main and ("R" in view.main or enabled) else -0.15
    return 0.0


def rank_cards(pool: tuple[Card, ...], pack: tuple[Card, ...], config: DraftConfig,
               signals: dict[str, float], pick_count: int) -> tuple[tuple[PickEvaluation, ...], tuple[ColorPlan, ...]]:
    progress = min(1.0, pick_count / max(1, config.total_picks - 1))
    legal_pool = tuple(c for c in pool if eligible(c, config) and not c.has("basic"))
    plans = color_plans(legal_pool, signals, progress)
    views = [(plan, PoolView(legal_pool, plan.colors)) for plan in plans]
    # Junk picks do not create color commitment. Strong pool evidence does.
    evidence = sum(max(0, pool_rating(c, legal_pool) - 1.5) for c in legal_pool if c.colors and not c.has("sideboard"))
    commitment = 0.20 + 5.0 * progress ** 0.65 * min(1.0, evidence / 14)
    results = []
    for index, card in enumerate(pack):
        allowed = eligible(card, config)
        if not allowed or card.has("basic"):
            value = -100.0 if not allowed else -20.0
            note = "Excluded by the configured rules; a forced pick has no playable value." if not allowed else "Free basic lands have no draft-pool acquisition value."
            results.append(PickEvaluation(card.name, index, value, allowed, {"eligibility": value}, (note,)))
            continue
        components = {"card_quality": card.rating, "color_fit": 0.0, "mana_burden": 0.0,
                      "pool_needs": 0.0, "synergy": 0.0, "fixing": 0.0, "redundancy": 0.0,
                      "availability_signal": 0.0}
        if card.has("dexterity"):
            components["card_quality"] *= config.chaos_orb_hit_rate
        note_weights = Counter()
        for plan, view in views:
            fit = availability(card, legal_pool, plan.colors)
            w = plan.weight
            components["color_fit"] -= w * commitment * (1 - fit)
            components["mana_burden"] += w * mana_burden(card, view)
            components["pool_needs"] += w * fit * needs(card, view, progress)
            synergy, notes = synergies(card, view)
            components["synergy"] += w * fit * synergy
            components["fixing"] += w * fit * fixing_value(card, view)
            for note in notes:
                note_weights[note] += w * fit
        copies = sum(c.name == card.name for c in pool)
        if card.has("sideboard"):
            components["redundancy"] -= min(2.0, copies * 0.70)
        elif card.has("buildaround") and not card.has("body") and card.name != "Time Vault":
            components["redundancy"] -= min(1.2, copies * 0.25)
        if card.colors:
            components["availability_signal"] = 0.10 * (1 - progress) * signals.get(card.colors[0], 0)
        reasons = [card.note]
        reasons.extend(note for note, weight in note_weights.most_common(4) if weight >= 0.18)
        if components["color_fit"] < -1:
            reasons.append("Casting this reliably would stretch the strongest color plans in the current pool.")
        if components["pool_needs"] >= 0.20:
            reasons.append("This improves the pool's current role balance or mana curve.")
        elif components["pool_needs"] <= -0.20:
            reasons.append("The pool already has enough cards in this role or part of the curve.")
        if components["fixing"] >= 0.30:
            reasons.append("Its mana production matches the pool or helps cast an existing splash payoff.")
        score = sum(components.values())
        results.append(PickEvaluation(card.name, index, score, True, components, tuple(reasons)))
    # Stable and deterministic; duplicate copies and exact ties use pack order.
    results.sort(key=lambda e: (-e.score, e.index))
    return tuple(results), plans
