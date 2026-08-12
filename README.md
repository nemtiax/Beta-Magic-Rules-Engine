# Beta Magic

Beta Magic is a rules engine and local two-player interface for **Magic: The
Gathering as it existed in 1993**. The long-term goal is to support every card
in the Beta set using the original rulebook, contemporary FAQ clarifications,
and period card rulings.

This is not a modern Magic simulator with old cards loaded into it. Rules that
changed later—such as interrupt timing, fast-effect batches, mana burn, Walls,
and the original forms of protection and regeneration—are modeled according
to the early game wherever the available sources make that possible.

The project is under active development. A substantial portion of Beta is
playable, but many cards and some difficult rules interactions remain.

## Getting started

Beta Magic requires Python and [PySide6](https://doc.qt.io/qtforpython-6/).
From the repository root, install the UI dependency:

```console
python -m pip install -r requirements.txt
```

Launch the local hotseat UI:

```console
python -m beta_magic.ui
```

The default game gives both players broad demo decks built from all currently
supported cards. It is useful for browsing the card catalog, but the smaller
seeded decks below are usually better for focused playtesting.

## Using the UI

The interface supports two players on one computer. Use **Switch perspective**
to move between players; the opposing hand remains hidden.

Common interactions:

- Double-click a card in hand to play or cast it.
- Double-click a permanent with one activated ability to use that ability.
- Right-click a permanent to choose among multiple activated abilities.
- Click a highlighted card or player when a spell or ability needs a target.
- Use **Pass priority** to decline a response.
- Use **Begin attack**, select attackers, then switch perspective to declare
  blockers.
- Hover over a card to show its full details in the inspection pane.

Spells and ordinary fast effects do not use the modern stack. They collect
into a 1993-style simultaneous batch, while interrupts use their own
LIFO-like resolution sequence. The interface therefore asks both players to
pass at several points where a modern Magic client might behave differently.

The UI is intentionally a rules-development tool rather than a polished game
client. When a creature has multiple combat opponents, a dedicated picker
allows players to divide combat damage before the damage step resolves.

## Seeded playtest decks

The following mutually exclusive command-line options load deterministic
20-card matchups with useful opening hands:

| Option | Focus |
| --- | --- |
| `--test-decks` | General creatures, combat, activated abilities, and common spells |
| `--enchantment-test-decks` | Global and attached enchantments |
| `--timed-event-test-decks` | Upkeep events, Copper Tablet, and timed Auras |
| `--x-test-decks` | Variable `{X}` costs and scalable effects |
| `--protection-test-decks` | Protection, Wards, Circles of Protection, and colored effects |
| `--aura-test-decks` | Cheap Auras and creatures for testing stacked attachments |
| `--banding-test-decks` | Attacking bands, defensive Banding, and mixed evasion |

For example:

```console
python -m beta_magic.ui --protection-test-decks
```

Deck definitions and game factories live in `beta_magic/decks.py`.

## Historical rules sources

The repository keeps its rules sources alongside the engine:

- `RULES.md` describes the core Beta turn and game rules.
- `RULES_FAQ.md` contains contemporary FAQ clarifications, including timing
  and damage-resolution details.
- `RULES_CARDS.md` contains period card-specific rulings.
- `cards/card_checklist.md` tracks implementation coverage across the Beta
  card list.

When early wording is ambiguous, the engine favors these sources over modern
Oracle text and modern Comprehensive Rules. Some historical questions remain
underspecified; assumptions should be documented in tests or notes rather
than silently filled in with modern behavior.

## What the engine currently models

Implemented foundations include:

- player zones (including optional ante), ownership and control, drawing, life totals, and loss state;
- the Beta turn sequence and combat substeps;
- lands, mana pools, mana burn, colored costs, and `{X}` costs;
- casting, targeting, 1993 fast-effect batches, interrupts, and responses;
- activated abilities, summoning sickness, and temporary effects;
- continuous effects and dynamically calculated characteristics;
- combat with blocking restrictions, Flying, First Strike, Trample,
  landwalk, Walls, and regeneration;
- structured damage incidents with prevention, redirection, regeneration,
  and death windows;
- a separate regeneration pathway for ordinary destroy effects;
- upkeep costs, mandatory timed events, and event-conditioned abilities; and
- historical implementations of protection, Auras, control changes, land
  conversion, and other supported card mechanics.

This list describes engine capabilities, not complete Beta card coverage.
Consult the card checklist for the authoritative per-card status.

## Project structure

The public engine façade is `GameState`, with implementation divided by rules
responsibility:

```text
beta_magic/
  game.py                 shared state and cross-system coordination
  turn_flow.py            phases, turns, cleanup, and timed events
  casting.py              casting, targeting, and stack/batch declarations
  ability_activation.py   activated-ability validation and declaration
  priority_resolution.py  priority, interrupts, and fast-effect batches
  combat.py               attackers, blockers, and combat damage
  incident_resolution.py  damage and destruction resolution windows
  characteristics.py      current types, colors, abilities, power, and toughness
  cards.py                card definitions and physical card instances
  abilities.py            activated abilities and target requirements
  effects.py              spell, continuous, upkeep, and combat effects
  decks.py                deterministic UI deck lists
  ui.py                    Qt-facing view model and command-line entry point
  ui_choices.py            transient picker and dialog state
  ui_combat.py             transient combat selection and assignment coordination
  ui_messages.py           per-player UI notifications and prompts
  ui_presentation.py       read-only QML state and card/player presentation
  qml/                     Qt Quick interface
  card_defs/               canonical card definitions and catalog
```

Card definitions are organized by stable printed characteristics:
`white.py`, `blue.py`, `black.py`, `red.py`, `green.py`, `artifacts.py`, and
`lands.py`. `beta_magic.card_defs.catalog` owns the canonical `ALL_CARDS`
collection, `CARDS_BY_NAME` mapping, and checked `card_named()` lookup.
Mechanic-focused collections in `card_defs/groups.py` are views of that
catalog, not duplicate definitions.

## Running tests

The rules-engine tests do not require opening the graphical interface:

```console
python -m unittest discover -s tests -v
```

Tests are the primary specification for implemented interactions. New
mechanics should include focused rules tests, relevant card-definition
coverage, and regression cases for period-specific rulings.

## Development status

This is an incremental implementation, not a complete game release. Useful
places to orient new work are:

- `cards/card_checklist.md` for unsupported cards;
- `TODO.md` for broad mechanics;
- `NOTES.md` for explicitly deferred engine and UI work; and
- the three rules documents for the historical behavior being implemented.

Contributions should preserve the distinction between 1993 Magic and the
modern rules, keep each card definition canonical, and prefer reusable engine
mechanics over card-name-specific branches.
