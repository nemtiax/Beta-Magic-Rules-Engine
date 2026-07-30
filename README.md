The goal of this project is to build a faithful rules engine for Magic: the Gathering as it existed in 1993. The rules are as described in the Beta rulebook, and card text is as it was printed in Beta.

The project will support a simple graphical UI, which allows users to play the game. Local hotseat will be supported, but online/network play will be left for a possible future.

## Card definition organization

Supported cards are exposed through `beta_magic.card_defs`, organized by
stable printed characteristics rather than whichever mechanic happened to be
implemented first:

- `white`, `blue`, `black`, `red`, and `green`
- `artifacts`
- `lands`

`beta_magic.card_defs.catalog` owns the authoritative `ALL_CARDS` tuple and
read-only `CARDS_BY_NAME` mapping. `card_named()` provides checked lookup by
printed name. The UI builds its all-cards demo deck from this registry rather
than duplicating a list of mechanic collections.

The older mechanic-named modules remain import-compatible during the
migration. They feed a private compatibility intake, while new definitions
should be added to the appropriate printed-characteristic module and exposed
through the central catalog.

Seeded deck lists and their `GameState` factories live in
`beta_magic.decks`. Deck entries are resolved by printed name through the
card catalog, ensuring every seeded deck uses the canonical definition.
`beta_magic.ui` imports those factories for command-line selection but no
longer owns game content.

The card model is split by responsibility:

- `beta_magic.cards` owns `CardDefinition` and mutable `Card` instances.
- `beta_magic.abilities` owns target requirements and activated-ability
  descriptions.
- `beta_magic.effects` owns continuous, spell, upkeep, and variable-stat
  effect descriptions.

`beta_magic.cards` re-exports the ability and effect names for compatibility,
but engine code imports from the focused modules directly.

## Current foundation

The `beta_magic` package contains the initial rules-engine data model:

- immutable `CardDefinition` objects for printed card characteristics;
- mutable `Card` objects for individual physical copies;
- `ManaCost` and enums for colors, card types, zones, and game status;
- `PlayerState` zone management, drawing, and deck construction; and
- `GameState` setup, Beta's six turn phases, turn tracking, and structural
  validation.

The turn sequence is Untap, Upkeep, Draw, Main, Discard, and End. Entering
Untap untaps the active player's permanents, entering Draw draws a card, and
the engine will not leave Discard while that player has more than seven cards.
Combat will be modeled as an action within Main, matching the Beta rulebook.

The five basic lands are available as `PLAINS`, `ISLAND`, `SWAMP`, `MOUNTAIN`,
and `FOREST`. A player may play one land from their hand during their Main
phase and tap controlled basic lands for mana during either player's turn.
The ten original dual lands are also supported. They have their two proper
land subtypes but are not basic lands, and expose one activated mana ability
for each color. Double-clicking a permanent with one ability activates it
immediately; double-clicking a dual land opens its ability menu. Right-clicking
any permanent with activated abilities always opens that menu.

Llanowar Elves and Birds of Paradise use this same activated-ability system.
The Elves produce green mana directly; Birds opens a five-color choice menu.
Because their abilities have a tap cost, neither creature can use its mana
ability until it has begun one of its controller's turns in play.

Shivan Dragon, Frozen Shade, Granite Gargoyle, and Dragon Whelp add paid
pump abilities. Repeated activations stack, use the normal ability menu, and
expire during end-of-turn cleanup alongside marked creature damage. Dragon
Whelp may be pumped three times safely each turn; a fourth activation schedules
it to be destroyed at the end of that turn.

Ordinary activated abilities are fast effects, not interrupts. Pump abilities,
Goblin Balloon Brigade's temporary Flying, and targeted abilities such as
Prodigal Sorcerer and Royal Assassin pay their costs when declared, enter the
current simultaneous fast-effect batch, and give the opponent the first chance
to respond. Their effects occur only after both players pass. Mana abilities
remain immediate interrupts, while regeneration is used only in its dedicated
damage-resolution window.

The five Moxen and Sol Ring can be cast as artifacts and tapped immediately
for mana; artifacts are not affected by creature summoning sickness. Black
Lotus presents five three-mana choices, then destroys itself after producing
the selected color. Zero-cost artifacts display `0` on their card faces.
Unspent mana empties at every phase boundary and causes one point of mana burn
per mana, following the 1993 rules.

## Qt Quick UI

Launch the two-player hotseat interface with:

```console
python -m beta_magic.ui
```

For faster, repeatable playtesting, launch with:

```console
python -m beta_magic.ui --test-decks
```

This uses two intentionally ordered 20-card decks: blue/green **Verdant
Tides** and red/green **Stonefire**. Both contain ordinary creatures, Walls,
Flying, and First Strike, with repeatable opening hands and draws.

For a deterministic matchup focused on variable casting costs, launch with:

```console
python -m beta_magic.ui --x-test-decks
```

Blue/black **Arcane Depths** exercises Braingeyser and Howl from Beyond.
Red/green **Elemental Surge** exercises Earthquake, Hurricane, and Stream of
Life. Both 20-card decks supply Sol Ring and put flying and non-flying
creatures in their opening hands, making the damage filters and larger values
of X practical to test quickly.

For a deterministic protection matchup, launch with:

```console
python -m beta_magic.ui --protection-test-decks
```

White/black **Aegis Wards** contains all five Wards and both Knights.
**Spectrum Assault** supplies creatures and targeted effects in every color,
plus untargeted Earthquake damage for comparison.

Castle continuously gives its controller's untapped, non-attacking creatures
+0/+2; tapping or attacking removes the bonus immediately. Serra Angel flies
and does not tap to attack, but still obeys summoning sickness and loses
Castle's bonus while attacking. Ancestral Recall draws three cards for either
player, Jump grants Flying until end of turn, and Unsummon returns a creature
to its owner's hand while the normal attachment cleanup sends its Auras to
their owners' graveyards.

Rod of Ruin, Jayemdae Tome, and Icy Manipulator add reusable Mono Artifact
effects that pay mana, tap their source, and wait through the ordinary
fast-effect response batch before dealing damage, drawing, or tapping a
target. Giant Spider and Web share the historical ability to block Flying
without gaining Flying; Web also gives its enchanted creature +0/+2.

To play a second deterministic matchup focused on the global creature-buff
enchantments, launch with:

```console
python -m beta_magic.ui --enchantment-test-decks
```

This pits white/red **Radiant Charge**, using Crusade and Orcish Oriflamme,
against black/red **Moonlit Horde**, using Bad Moon and Orcish Oriflamme.
Their opening hands also include Holy Strength and Unholy Strength. Double-click
one of these creature enchantments, then click a creature in play to target it.
The engine keeps that cast pending until a legal target is chosen; the UI
highlights legal choices and offers **Cancel target** without spending mana.
Moonlit Horde also includes Weakness, which gives its target -2/-1. Creatures
whose toughness becomes zero or less are immediately put into the graveyard.
Lance and Flight use the same targeting flow to grant First Strike and Flying.
They are included in the Radiant Charge and Verdant Tides opening hands,
respectively.

Lightning Bolt and Psionic Blast introduce targeted instant damage. During
target selection, legal creatures remain clickable and each legal player gets
a **Target player** button. After casting, the instant waits in a response batch for
both players to pass priority, then emits its damage events and enters its
owner's graveyard.

Spells and responses collect into a 1993-style fast-effect batch rather than a
modern last-in, first-out stack. The opponent receives the first opportunity
to respond; use **Pass priority** from each player's perspective to close the
batch after everyone passes consecutively. Casting a response resets the pass
count. Target legality is captured when the batch closes, all legal effects
are applied as one instant, and state-based checks happen only after the full
batch has taken effect.

Giant Growth and Righteousness add targeted temporary pumps to these batches.
Because all effects take effect in one instant, Giant Growth can save a
creature from Lightning Bolt regardless of which of those two spells was
declared first. Righteousness is only castable with a creature that is
currently blocking as its target.

Bog Wraith and Shanodin Dryads implement Swampwalk and Forestwalk. Landwalk
checks the defending player's current land subtypes, so dual lands count for
each subtype they possess: Bayou, for example, enables both Swampwalk and
Forestwalk. Landwalk does not care whether the matching land is basic.

Burrowing grants Mountainwalk through the existing Enchant Creature system.
Lord of Atlantis buffs all printed Merfolk on either battlefield and grants
them Islandwalk; Goblin King does the same for cards printed as Summon Goblins
and grants Mountainwalk. The card-specific rulings say neither lord affects
itself, so their historical creature categories are kept distinct from
`Merfolk` and `Goblins`.

Blessing, Holy Armor, and Firebreathing put repeatable pump abilities on
Enchant Creature permanents. The Aura's controller pays the activation cost,
and the temporary bonus is applied to its enchanted creature. Holy Armor also
supplies its continuous +0/+2 bonus. An activated bonus lasts through the end
of the turn even if its Aura subsequently leaves play.

Disenchant and Shatter use the same targeting flow for enchantments and
artifacts. Tranquility is cast only at sorcery speed and removes every
enchantment in play, including global enchantments and attached creature
enchantments. These cards are included in the deterministic test decks.

Stone Rain, Sinkhole, and Ice Storm use the targeting flow to destroy any
single land. Armageddon destroys every land, while Flashfires and Tsunami
filter by the historical Plains and Island land subtypes. These subtype checks
include dual lands; global destruction spells may also be cast when no
matching lands are in play.

Regrowth, Raise Dead, and Resurrection target cards in their caster's
graveyard. Regrowth returns any card to hand, Raise Dead returns a creature
card to hand, and Resurrection puts a creature directly into play with the
normal summoning restrictions. While choosing such a target, the UI exposes
the full graveyard and allows legal cards there to be clicked.

Copper Tablet introduces mandatory timed events. At the beginning of each
upkeep, every untapped Tablet creates a separate pending event for one damage
to the active player. The event itself is not placed in the simultaneous
fast-effect batch. Instead, the UI displays the pending event and gives both
players priority; any declared responses resolve as an ordinary batch, after
which both players must pass again before the event occurs. If the Tablet has
left play or is tapped by then, its pending event has no effect.

Run `python -m beta_magic.ui --timed-event-test-decks` for deterministic
20-card timed-effect decks. Their opening hands contain Copper Tablet and Sol
Ring, with Lightning Bolt available for exercising response windows.

Cursed Land, Feedback, Wanderlust, and Warp Artifact extend timed events to
attached permanents. They enchant a land, enchantment, creature, or artifact
respectively, and create their damage event only during that permanent's
controller's upkeep. Destroying the Aura or its enchanted permanent during
the response window prevents the pending event from dealing damage. The timed
event test decks include all four Auras and suitable targets.

Phantasmal Forces adds optional mana upkeep. Its controller must explicitly
pay `{U}` or decline before passing the event's initial priority. Paying or
declining hands priority to the opponent, and the choice takes effect only
after the response window closes. Declining destroys the Forces; paying keeps
it in play. If it leaves play during responses, no payment is required. The UI
shows dedicated Pay Upkeep and Decline Upkeep controls and updates the payment
button as mana is produced.

Force of Nature uses the same prompt for its `{G}{G}{G}{G}` upkeep. Declining
deals eight damage to its controller instead of destroying the creature, so
Force of Nature remains available to attack that turn. The damage is emitted
as ordinary card-source damage, leaving room for the era's damage-prevention
effects when those are implemented.

Keldon Warlord, Nightmare, and Plague Rats have continuously calculated power
and toughness. Keldon Warlord counts its controller's non-Wall creatures,
Nightmare counts its controller's lands with the Swamp subtype (including dual
lands), and Plague Rats counts Rats controlled by either player. Their base
stats update as permanents enter and leave play, before ordinary continuous and
temporary bonuses are applied; a creature that consequently reaches zero
toughness is put into its owner's graveyard immediately.

Prodigal Sorcerer and Orcish Artillery add targeted tap abilities. Activating
one enters target-selection mode without tapping the creature; choosing a
creature or player pays the tap cost and declares the ability into the current
fast-effect batch. The opponent may respond before it resolves. Prodigal
Sorcerer deals one damage to its target, while Orcish Artillery deals two to
its target and three to its controller. Both creatures obey summoning
sickness, and a declared ability remains in the batch if its source leaves
play.

All damage now passes through structured `DamageIncident` and `DamagePacket`
objects before it is applied. A packet records its source, controller, colors,
recipient, combat status, Trample status, and First Strike status. Spell and
activated-ability batches accumulate all of their damage in one incident;
each combat-damage wave and timed upkeep effect creates its own incident.
Resolved incidents are retained on the game for inspection and future rules
processing. Prevention, redirection, and regeneration are distinct priority
windows requiring consecutive passes from both players. Damage is applied
after the redirection window, while lethal creatures remain in play until the
regeneration window closes. The UI pauses at all three windows and shows the
pending packets. Engine clients may auto-skip them while no implemented card
can act there. First Strike combat resumes with regular combat damage only
after its complete incident has finished. Mana burn remains separate because
the era rules classify it as loss of life.

Drudge Skeletons, Uthden Troll, Will-o'-the-Wisp, Wall of Bone, and Wall
of Brambles add paid regeneration. Their abilities become usable only while
the creature faces lethal damage or an ordinary destroy effect in the
Regeneration window. Mana abilities remain available during damage resolution,
allowing the controller to generate the payment after damage is known.
Regenerating pays the printed cost, taps the creature as an effect, removes all
marked damage, preserves attachments, and prevents its pending destruction.
A creature regenerated during combat remains part of combat but deals and
receives no further combat damage that attack.

Ordinary destroy effects use a separate `DestructionIncident`; they do not
enter damage accumulation, prevention, or redirection. A destruction incident
has only a Regeneration window followed by destruction of the permanents that
were not saved. This pathway is type-agnostic so future regenerating artifact
creatures and other regenerable permanents can use it as well. Regeneration
permission is recorded per destruction target: Tunnel destroys only Walls and
marks its target as unable to regenerate, while other targets in the same
incident can still use their own regeneration abilities.

Living Wall and Sedge Troll add more printed regeneration abilities; Sedge
Troll's +1/+1 updates continuously as its controller gains or loses Swamps.
The Regeneration Aura activates through its controller but regenerates the
creature it enchants. Zombie Master continuously grants swampwalk and `{B}`
regeneration to every other Zombie in play, including opposing Zombies, and
both grants disappear when the Master leaves play. Death Ward can respond in a
fast-effect batch to lethal damage or an ordinary destroy effect, but cannot
override an effect such as Tunnel that expressly forbids regeneration.

Mana costs now retain printed `{X}` symbols separately from fixed generic and
colored requirements. The caster declares X before choosing targets, pays the
resulting cost, and that value remains attached to the spell through response
and resolution. Stream of Life is the first supported X spell. In the UI,
double-clicking it opens a modal `-`/`+` picker initialized to the highest
currently affordable value, with the affordable range displayed explicitly.
The same casting flow now supports Braingeyser, Howl from Beyond, Earthquake,
and Hurricane, and the chosen X remains visible beside the spell in the UI's
response-batch display. Earthquake and Hurricane use the normal simultaneous
damage pipeline and determine Flying from the battlefield state at resolution.

Dwarven Demolition Team, Royal Assassin, and Northern Paladin extend targeted
tap abilities to destruction. Their legal-target highlighting filters for
Walls, tapped creatures, and black permanents respectively; Northern Paladin
also charges `{W}{W}` when its target is committed. Royal Assassin follows its
era ruling that tapped status matters when the target is chosen, so untapping
that creature during responses does not save it. Goblin Balloon Brigade uses
the temporary-effect system to gain Flying for `{R}` until end of turn, and
may activate repeatedly even though additional instances of Flying have no
further effect.

The UI uses PySide6 and Qt Quick. Install its dependency with:

```console
python -m pip install -r requirements.txt
```

The demo gives each player a deck of currently supported cards. It shows hands,
libraries, graveyards, set-aside cards, cards in play, life totals, mana pools,
the active player, and the current phase. Select a card rectangle and use the
controls to play, tap, cast, or discard it. Switching perspectives hides the
other player's hand.

The engine also includes Beta's fifteen vanilla, non-Wall creatures. During
their Main phase, the active player can cast one by paying its colored and
generic mana cost. The UI demo decks contain all fifteen creatures and
twenty-five basic lands; select a creature in hand and choose **Cast selected
creature** after producing the required mana.

Rules actions emit structured events for spell casts, zone changes, combat
damage, and mana burn. The UI renders its status messages from those events
instead of inferring causes from changed totals. Global and attached
characteristic changes share one declarative continuous-effect model, capable
of modifying power/toughness and granting keyword abilities.

Combat is an optional, once-per-turn action inside Main. It follows Beta's
Declare Attackers, Declare Blockers, Fast Effects, and Damage Dealing
sub-steps. Attackers tap, untapped defending creatures may block, combat damage
is simultaneous, lethal damage sends creatures to their owners' graveyards,
and unblocked damage reduces the defending player's life. Mana pools empty and
cause mana burn when an attack begins and ends.

The clarified attack timing includes fast-effect windows before attackers,
between attacker and blocker declarations, and after blockers before damage.
The declarations themselves are atomic. Attack-start mana burn occurs after
the first response window closes. No actions may be taken during Untap.

Wall of Ice, Wall of Stone, and Wall of Wood are supported. In keeping with
Beta, the `Wall` creature type itself prevents these creatures from attacking;
there is no modern Defender keyword. Walls cast and block like other creatures.

Flying is supported for Air Elemental, Mahamoti Djinn, Phantom Monster, Roc of
Kher Ridges, Scryb Sprites, Wall of Air, and Wall of Swords. A creature with
Flying may block any creature, while a flying attacker can only be blocked by
another creature with Flying. The flying Walls still cannot attack because
they have the Wall creature type.

First Strike is supported for Elvish Archers. Combat damage resolves in a
first-strike wave followed by a regular wave; lethal creatures are removed
between them, so a creature killed by first-strike damage does not deal regular
combat damage. First strikers fighting each other deal damage simultaneously.

Protection from color follows the contemporary FAQ rather than modern rules.
White Knight and Black Knight cannot be damaged, blocked, or targeted by the
opposing protected color, and cannot receive new Auras of that color. Global
effects still apply. In keeping with the pre-Revised rule noted by the FAQ,
gaining protection does not remove Auras that are already attached.
Black Ward, Blue Ward, Green Ward, Red Ward, and White Ward grant those same
protection abilities while attached. The Ward itself remains attached when
its continuous effect begins granting protection.

Healing Salve can either give a player 3 life through the ordinary targeting
flow or, when cast during a damage-prevention window, prevent up to 3 assigned
damage to one creature or player. Samite Healer taps during that same window
to prevent 1 damage. The UI exposes individual damage packets so the player
can choose which source's conceptual damage tokens to remove, as required by
the FAQ.

All five Beta Circles of Protection are supported, including Circle of
Protection: Black. Each costs `1` to activate during prevention and removes
all damage against its controller from one selected source of the named
color. Circles do not tap, and each separate damage event requires another
activation. The `--protection-test-decks` matchup includes all five Circles.

Trample is supported for War Mammoth. Excess damage assigned beyond a
blocker's remaining toughness is redirected to the defending player. Against
multiple blockers, damage may be piled onto one blocker, and all damage gets
through if every blocker has left combat.

Crusade, Bad Moon, and Orcish Oriflamme are supported as global
enchantments. Their bonuses are continuous, multiple copies stack, and current
power/toughness is used by both combat and lethal-damage checks. Crusade and
Bad Moon affect matching creatures on both sides; Orcish Oriflamme affects
only its controller's attacking creatures.

Cards are GPU-rendered, color-coded QML components. Double-click a
land in hand to play it, a creature in hand to cast it, or a land in play to
tap it for mana. Single-click still selects cards for discarding and combat.

In the UI, choose **Begin attack**, select any number of creatures in play, and
declare them as attackers. Switch to the defending perspective, select
blockers, choose an attacker in the drop-down, and declare the defense. The
advance button then moves through Fast Effects and Damage. For a multiple
block, the UI asks the attacker how to distribute combat damage.

Libraries use the end of the Python list as the top, so `library.pop()` draws the
top card. Run the dependency-free test suite with:

```console
python -m unittest discover -s tests -v
```
