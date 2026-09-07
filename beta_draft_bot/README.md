# Beta draft tools

A stateful draft-pick bot and historical booster generator for Magic: The
Gathering's Limited Edition Beta.
Submit a pack of card names; receive one choice. The bot remembers its picks and
adapts its evaluations to the developing pool. It has a Python API and a
JSON-lines interface suitable for a draft server, simulator, or another language.

Python **3.10 or newer**. The bot and booster generator have **no runtime
dependencies, network access, API key, or model service requirement.** The
optional desktop UI uses PySide6. All 292 distinct Beta card names are included, with
individual ratings and evaluation notes. Alternate basic-land artwork accounts
for the difference from the set's 302 printings. Card metadata was retrieved
from the [Scryfall Beta catalog](https://scryfall.com/sets/leb) on September 5, 2026.

This is a hand-tuned strategy engine. Its ratings and weights are original
heuristic estimates, **not measured win rates or a guarantee of optimal drafting**.
The bot does not build a deck or play a game. The desktop client coordinates
pack passing between one human and local bot seats.

## Run it

Extract the archive and enter the `beta-draft-bot` directory. Running from this
directory requires no installation:

```bash
python -m examples.sequential
python -m unittest discover -s tests -v
python -m beta_draft
```

For use from another project, install this directory:

```bash
python -m pip install /path/to/beta-draft-bot
```

The installed command `beta-draft` is equivalent to `python -m beta_draft`.
Installation uses setuptools; runtime drafting itself uses only the standard library.

### Draft against bots

Install the optional UI dependency and launch the desktop client:

```bash
python -m pip install -e ".[ui]"
python -m beta_draft.ui
```

The client runs a three-round, eight-seat draft by default. Double-click a card
in the current pack to take it; all seven bots then make their choices and the
next pack is passed. Hovering over any offered or drafted card fills the preview
pane with its printed text. Your pool remains visible at the bottom, sorted by
color and mana value.

Historical boosters include basic lands in their original sheet slots. To use
the modernized generator instead, or reproduce a draft, run:

```bash
python -m beta_draft.ui --no-basic-lands --seed 1993
```

Use `--color-balanced` to guarantee that the eleven-common portion represents
all five colors. It can be combined with `--no-basic-lands`.

`--players` and `--rounds` can make shorter test drafts. The installed
`beta-draft-ui` command is equivalent to `python -m beta_draft.ui`.

These command-line options establish the initial draft settings. Use **New
draft...** in the UI to review or change booster style, common color balancing,
table size, and round count. The settings are applied together only after
confirming **Start new draft**, which replaces the current packs and drafted
pool.

Add `--bot-advisor` to start with the advisor visible. Its preferred card in
each pack receives a teal outline and `BOT PICK` badge, but double-clicking a
different card still takes the human choice. The advisor records that actual
choice, so subsequent recommendations evaluate the player's real pool. The
same display can be toggled at any time with **Show bot pick** above the pack.

For debugging the evaluation model, enable **Show scores** to display the bot's
two-decimal score on every card in the current pack. `--bot-scores` starts the
UI with those scores visible; it can be used with or without `--bot-advisor`.

Use `--bot-color-plans` to add a diagnostic panel below the card preview. It
lists all five mono-color and ten two-color hypotheses, ordered by the
normalized weight currently used to evaluate the pack. These weights update
after every pick and include availability evidence from the current pack.

## Minimal Python interface

```python
from beta_draft import DraftBot

bot = DraftBot()  # one instance for one drafter

choice = bot.pick(["Fireball", "Grizzly Bears", "Healing Salve"])
assert choice == "Fireball"

choice = bot.pick(["Lightning Bolt", "Hill Giant", "Purelace"])
assert choice == "Lightning Bolt"

assert bot.pool == ("Fireball", "Lightning Bolt")
```

Each `pick` call adds exactly one card. The returned name uses the catalog's
canonical spelling. Names accept case differences, extra whitespace, and curly
apostrophes; unknown or non-Beta names raise an error instead of receiving a
made-up evaluation. Pack lists may contain duplicate names. No four-copy limit
is imposed on the draft pool.

The caller decides which pack to present next and removes the selected card.
The bot itself accepts any pack distribution and has no hard limit on the
number of calls or required UI framework. The separate booster generator below
can supply historically weighted packs.

### Historical Beta boosters

```python
from beta_draft import BetaBoosterGenerator

generator = BetaBoosterGenerator()
pack = generator.generate_pack()  # tuple of 15 Card records
choice = bot.pick([card.name for card in pack])
```

Each pack draws one slot from the 121-card rare sheet, three distinct slots
from the 121-card uncommon sheet, and eleven distinct slots from the 121-card
common sheet. The sheets include Beta's unusual basic-land distribution:

- rare: four Islands alongside the 117 rares;
- uncommon: six each of Plains, Swamp, Mountain, and Forest, plus two Islands;
- common: eight Plains, ten Islands, nine Swamps, ten Mountains, and nine Forests.

Sampling is without replacement within each rarity portion of one pack. A
nonbasic therefore cannot duplicate within a pack, while basics can because
they occupy multiple physical sheet slots. Packs are independent. Pass a
seeded `random.Random` as `rng=` for reproducible simulations, or use the
`generate_beta_pack()` convenience function for a single pack.

For a modernized draft in which basics do not consume any of those fifteen
slots, use the separate no-basic generator:

```python
from beta_draft import NoBasicLandBetaBoosterGenerator

generator = NoBasicLandBetaBoosterGenerator()
pack = generator.generate_pack()
```

This preserves the 1/3/11 rarity structure while sampling only the 117 actual
rares, 95 actual uncommons, and 75 nonbasic commons. Nonbasic lands remain in
their normal rarity pools. `generate_no_basic_land_beta_pack()` is the
corresponding one-pack convenience function.

Both generator classes and convenience functions accept
`color_balanced=True`. The pack is sampled normally first. If a color is absent
from the common portion, a common from an overrepresented color is replaced by
a random common of the missing color. Basic lands are replaced only when the
original selection contains fewer than five colored commons. Rare and uncommon
slots are never adjusted. This is intentionally a play-oriented approximation,
not a reconstruction of Beta's physical print-run collation.

### Scores, explanations, and card-instance IDs

```python
pack = ["Sedge Troll", "Gray Ogre", "Mons's Goblin Raiders"]

# Preview only: does not add a card or update signal memory.
for option in bot.rank(pack):
    print(option.card, round(option.score, 3), option.components)

# Make and remember a pick, with its original zero-based pack index.
decision = bot.pick_with_details(pack)
print(decision.card, decision.index, decision.reasons)
pack.pop(decision.index)
```

`rank` and `pick_with_details` return `PickEvaluation` records. A record contains
`card`, `index`, `score`, `eligible`, `components`, and `reasons`; `to_dict()` makes
it JSON-compatible. Scores are comparable within a decision, not probabilities.
Higher is better. Components sum to the final score. Exact ties use original
pack order deterministically.

When your application has its own card-instance objects, retain them and map
the returned index back to the original pack:

```python
offered = [
    {"id": "instance-101", "name": "Terror"},
    {"id": "instance-102", "name": "Terror"},
    {"id": "instance-103", "name": "Dark Ritual"},
]
decision = bot.pick_with_details([card["name"] for card in offered])
selected_instance = offered[decision.index]
```

For a human or external override, use `record_pick` **in place of** `pick`:

```python
bot.record_pick(["Terror", "Black Knight"], "Black Knight")
```

The override must name a card in the offered pack. Empty packs and invalid
inputs raise `ValueError` or `TypeError` without consuming a pick or learning
from the pack. `bot.pool` is an immutable tuple; snapshots are detached copies.

### Save and resume

```python
bot.save("draft-state.json")  # atomic file replacement; parent must exist
resumed = DraftBot.load("draft-state.json")

# Equivalent in-memory / database integration:
state = bot.to_dict()
resumed = DraftBot.from_dict(state)
```

Checkpoints preserve the pool, rules configuration, last draft context, and
pack-signal observations. State is versioned JSON, never pickle. A bad state is
rejected. For a pool supplied by another system without previous pack history:

```python
bot = DraftBot(pool=["Serra Angel", "Swords to Plowshares", "White Knight"])
```

Use one bot per drafter. Mutating calls on a shared instance require caller-side
serialization. Persisted files are checkpoints, not a multi-writer database.
Your application also owns retry handling: calling `pick` twice records two picks.

### Draft context and signals

By default, the bot assumes 15 picks per round and an eight-player table. It
infers round and pick numbers from previous calls; the input pack's length does
not determine the pick number. Supply explicit context for a draft already in
progress, unusual pack schedules, or accurate wheel tracking:

```python
from beta_draft import DraftContext

decision = bot.pick_with_details(
    ["Prodigal Sorcerer", "Phantom Monster", "Flight"],
    context=DraftContext(pack_number=1, pick_number=7, pack_id="round1-origin4"),
)
```

Round and pick numbers are **one-based**. `pack_id` is an optional identity of the
physical pack: preserve it when the same pack returns on the wheel. Use IDs
consistently throughout a draft. Without IDs, the bot approximates a pack's
origin using pick number modulo table size, which assumes ordinary pack passing.

The bot ignores opening-pack quality as a signal. Good colored cards surviving
later in a round provide bounded evidence that the color may be available.
Repeated views of the same pack retain the strongest evidence instead of
counting as independent packs. Opposite passing directions are tracked separately;
the next round from the same direction reuses old evidence with decay. It does
not infer a neighbor's exact colors from a single absent card.

```python
for plan in bot.color_plans()[:3]:
    print("".join(plan.colors), plan.weight)
```

These are normalized heuristic hypothesis weights, not calibrated probabilities
or a proposed deck list. A card can still be a useful splash outside the main plan.

## JSON-lines interface

Start a long-lived process and send one request per line:

```bash
python -m beta_draft --state draft-state.json
```

Input lines may be just a pack array:

```json
["Fireball", "Grizzly Bears", "Healing Salve"]
["Lightning Bolt", "Hill Giant", "Purelace"]
```

Each produces one JSON response containing the chosen `card`, zero-based `index`,
`score`, `eligible`, score `components`, `reasons`, `pool_size`, and current `pool`.
There are no prompts or logging on stdout. Output is flushed after each request.
Without `--state`, memory lasts for the lifetime of the process.

The object form supports additional operations:

| Operation | Request shape | Changes state? |
| --- | --- | --- |
| Pick | `{"op":"pick","pack":["Terror","Dark Ritual"]}` | Yes |
| Preview | `{"op":"rank","pack":["Terror","Dark Ritual"]}` | No |
| Override | `{"op":"record","pack":["Terror","Dark Ritual"],"card":"Dark Ritual"}` | Yes |
| Export | `{"op":"state"}` | No |
| New draft | `{"op":"reset","config":{"total_picks":45}}` | Yes |
| Restore | `{"op":"restore","state":...}` | Yes |

Omitting `op` defaults to `pick`. Pick, preview, and override requests may contain
`"context":{"pack_number":1,"pick_number":7,"pack_id":"round1-origin4"}`.

Blank lines are ignored. Malformed JSON, invalid cards, empty packs, bad context,
and unsupported operations return an `error` object and leave the draft state
unchanged. The process continues to the next line. With `--state`, an existing
checkpoint is loaded on startup and successful mutations are atomically saved.
A checkpoint-write failure also leaves the in-memory draft unchanged. An invalid
startup checkpoint stops the process instead of silently starting a new draft.

## Rules and configuration

The default strategy assumes one-on-one Limited using printed Beta wording,
the repository's 1993 rules and period rulings, a normal 40-card Limited target,
and free basic lands. In particular, its evaluations account for mana burn,
interrupts and fast-effect batches, tapped continuous artifacts, and other
historical behavior that differs from modern Oracle rules. The common
45-pick and free-basic-land conventions are described in Wizards' [Booster Draft
overview](https://magic.wizards.com/en/formats/booster-draft). These conventions
calibrate pool balance; the bot never constructs a deck.

```python
from beta_draft import DraftBot, DraftConfig

bot = DraftBot(config=DraftConfig(
    total_picks=45,
    pack_size=15,
    table_size=8,
    allow_ante=False,
    allow_dexterity=False,
    chaos_orb_hit_rate=0.75,
    banned_cards=(),
))
```

| Setting | Meaning |
| --- | --- |
| `total_picks` | Expected draft length for commitment and pool-balance urgency; not a hard stopping limit. |
| `pack_size` | Picks per round for inferred chronology; explicit pick numbers must be within it. |
| `table_size` | Number of seats for approximate wheel tracking. |
| `allow_ante` | Enables Contract from Below, Darkpact, and Demonic Attorney. Off by default. |
| `allow_dexterity` | Enables Chaos Orb. Off by default. |
| `chaos_orb_hit_rate` | A 0–1 multiplier on Chaos Orb's base value when enabled; no physical flip simulation. |
| `banned_cards` | Additional Beta card names to treat as unavailable for play. |

An enabled Chaos Orb uses a rough hit-rate valuation, not a specific Old School
house-rule implementation. Custom ante rewards, later errata, alternative
historical interpretations, and changing the free-basic-land assumption need
strategy changes.

The bot accepts every Beta name even when the configured rules exclude the card.
Excluded cards rank below every eligible card, including free basics. If an
entire pack is excluded, it still returns a deterministic forced choice with
`eligible=False`; this keeps the pick protocol usable when dead cards remain.
Drafted basic lands and excluded cards do not establish color commitment.

## How strategy works

1. **Card-specific quality.** Every distinct card has an explicit base rating,
   strategic roles, and an original explanation in `beta_draft/data/ratings.tsv`.
   There is no unknown-card fallback. Rarity, market price, and constructed-format
   reputation do not enter the score.
2. **Flexible color plans.** The engine weighs all five mono-color and ten
   two-color options using playable pool quality and bounded passing signals.
   Commitment grows with draft progress and actual useful cards, so early picks
   remain flexible and late off-color cards pay a substantial opportunity cost.
3. **Mana realism.** Colored-pip density and a hypergeometric source estimate
   price difficult casting costs. Splashes require suitable high-impact cards and
   receive credit only for relevant fixing. Dual lands, on-plan Birds, Moxen,
   and slow filtering have different values. Recurring colored-mana requirements
   are not treated as easy single-pip splashes.
4. **Pool balance.** Creatures, early plays, removal, card advantage, ramp,
   expensive spells, and defensive bodies receive scarcity or saturation
   adjustments. X spells have practical deployment costs rather than being
   mistaken for one-drops. Extra tricks, narrow buildarounds, and duplicate
   sideboard cards have diminishing value.
5. **Beta interactions.** Existing partners change pick values in either pick
   order. Synergy bonuses are bounded and discounted when a color plan cannot
   realistically cast both cards. Independently good cards retain their value
   when a speculative combo is incomplete.

Examples of deliberate card-specific handling:

| Card or interaction | Evaluation consequence |
| --- | --- |
| Fireball, Disintegrate, Swords, Terror | Different flexibility, target restrictions, regeneration/exile behavior, and splash value. |
| Prodigal Sorcerer, Orcish Artillery, Rod of Ruin | Repeatable damage is valuable against Beta's small bodies; mana cost and self-damage differ. |
| Drain Life, Nightmare, Frozen Shade | Reward dense black mana or actual Swamps; Drain Life cannot use Channel's colorless mana for X. |
| Lure + Thicket Basilisk / Cockatrice | Recognizes the forced-block destruction interaction. |
| Pestilence | Prices symmetric damage, fragile allies, durable creatures, and protection from black. |
| Sedge Troll | Distinguishes controlling a Swamp from merely having black mana. |
| Channel + Fireball / Disintegrate | Rewards the actual mana payoff, with life and colored-pip requirements remaining. |
| Time Vault + Twiddle | One extra turn per untap spell; Icy Manipulator does not untap Time Vault. |
| Time Vault + Animate Artifact + Instill Energy | Recognizes the three-card repeated-turn engine; Instill Energy alone cannot enchant Time Vault. |
| Instill Energy | Attack permission does not remove summoning sickness for tap abilities. |
| Plague Rats and tribal lords | Rewards real density and the specific tribe; a rat cluster also contributes color commitment. |
| Verduran Enchantress | Counts independently playable enchantments instead of rewarding bad Auras. |
| Winter Orb / Howling Mine + Icy Manipulator | Recognizes that tapping the artifact can break symmetry at the right time. |
| Tapped continuous artifacts | Treats tapping cards such as Meekstone, Howling Mine, and Winter Orb as switching off their continuous effects. |
| Power Surge and mana sinks | Accounts for mana burn: spare lands cannot be tapped harmlessly, while repeatable sinks make excess mana safer. |
| Camouflage | Values the Beta concealed-pile procedure, in which the attacker rearranges creatures after blockers choose piles, rather than modern random assignment. |
| Clone / Vesuvan Doppelganger | Treats the copy choice as a target that must be legal when the creature is summoned or changes form. |
| Wheel, Timetwister, Balance, Wrath, Armageddon | Symmetric effects depend on pressure, mana, and pool composition. |
| Illusionary Mask | Does not evade colored costs, but concealed characteristics can invalidate opposing targeted spells under the period rulings. |

Metadata contains mana costs, types, keywords, printed power/toughness, printed
Beta rules text, produced mana, rarity, and a per-card source URL. Strategic
roles and notes are authored separately. Card images are not redistributed.

## Validation and limitations

The test suite covers all 292 cards, changing color commitment, supported
splashes, mana restrictions, curve and creature shortages, real and false combo
interactions, rat density, configurable exclusions, duplicate card indices,
signal direction and wheel identity, invalid inputs, and a complete eight-seat /
three-round / 360-pick integration run with card conservation.

It also verifies all three historical 121-slot print sheets, pack composition,
basic-land multiplicities, duplicate behavior, and seeded reproducibility.
Those tests establish functional behavior and selected strategic expectations.
They **do not measure match win rate**: no game engine, trained draft dataset,
or human playtest results are included. The integration packs are arbitrary
Beta-card packs, not a reconstruction of historical print-sheet collation.

The model is deliberately approximate. It does not predict unseen packs, model
each opposing drafter, evaluate every possible card interaction, optimize a
final mana base, estimate the exact joint draw probability of a combo, or solve
optimal sideboarding. Its color weights and source estimates are drafting
heuristics. Early speculation, corner-case effects, and unusual house rules
will sometimes warrant a human override.

To tune the strategy, edit the per-card ratings and notes in
`beta_draft/data/ratings.tsv`, then adjust pool, mana, and interaction weights in
`beta_draft/strategy.py`. Preserve the behavioral tests and add regression cases
for observed drafting mistakes. Restart the process after editing data, since
the catalog is cached in memory.

An optional metadata maintenance command fetches the current Beta catalog from
the [Scryfall API](https://scryfall.com/docs/api/cards):

```bash
python tools/refresh_cards.py
```

This is the only command that needs a network connection. It checks the complete
292-name inventory before updating metadata. Review Oracle changes and related
heuristics separately: refreshing metadata does not rewrite strategic judgments.

### Optional card images

Card artwork is not stored in the repository. In the complete Beta Magic
workspace, the gameplay and draft clients share one image library. From the
repository root, run:

```bash
python tools/download_card_images.py
```

The script retrieves the 292 unique Beta card records from Scryfall, then saves
an art crop to the root `card_images/art_crops` directory and a large full-card
JPEG to `card_images/full_cards` for each card. It spaces requests, retries transient
failures, writes files atomically, and skips existing nonempty files, so an
interrupted download can be resumed with the same command. Use `--force` to
replace existing files or `--full-size png` for lossless full-card images.

The root `card_images/manifest.json` maps canonical card names to their generated paths
and Scryfall IDs. The entire `card_images` directory is ignored by Git. See the
[Scryfall image API documentation](https://scryfall.com/docs/api/images) and
Scryfall's current usage guidance before redistributing or making heavy use of
downloaded images.

When the manifest and corresponding files are present, the draft UI
automatically uses the full-card image in its mouse-over preview pane. It falls
back to the generated text card when an image is absent, so downloading artwork
is never required to run the draft tools.

The current-pack tiles and compact drafted-pool stacks likewise use the art
crops when available. Their color-coded frames and text overlays remain in
place, with outlined light text for readability over varied artwork.

## Files

| File | Purpose |
| --- | --- |
| `beta_draft/bot.py` | Public API, pool memory, context, signals, checkpoints. |
| `beta_draft/strategy.py` | Color plans, mana, needs, fixing, synergies, and scoring. |
| `beta_draft/cards.py` | Validated offline catalog and practical card attributes. |
| `beta_draft/packs.py` | Historical 121-slot print sheets and booster generation. |
| `beta_draft/session.py` | Human-and-bot draft rounds, picks, and pack passing. |
| `beta_draft/ui.py` | QML-facing draft state and desktop entry point. |
| `beta_draft/qml/Main.qml` | Responsive pack, pool, and card-preview interface. |
| `beta_draft/models.py` | Configuration, context, and result types. |
| `beta_draft/__main__.py` | JSON-lines process interface. |
| `beta_draft/data/cards.json` | Complete Beta metadata snapshot. |
| `beta_draft/data/ratings.tsv` | Individual ratings, role tags, and authored notes. |
| `examples/sequential.py` | Runnable sequential-pick example. |
| `tests/test_bot.py` | Behavioral and integration regression suite. |
| `tests/test_packs.py` | Print-sheet and pack-generation tests. |
| `tests/test_session.py` | Draft progression and card-conservation tests. |
| `tests/test_ui.py` | Draft presentation and interaction-state tests. |
| `tools/refresh_cards.py` | Optional explicit metadata refresh. |
| `../tools/download_card_images.py` | Shared resumable local Scryfall image downloader. |

See `LICENSE` for the original code license and `NOTICE.md` for card-data attribution.
