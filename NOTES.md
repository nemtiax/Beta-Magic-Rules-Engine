# Deferred tasks

## Era rulings adopted after the reference compilation

- Graveyard ordering (bethmo, 1994-05-03): "If multiple cards go to the
  graveyard at the same time, you may choose what order they get stacked in."
  We interpret "you" as the owner of that graveyard. Each affected owner
  orders their own simultaneous group from bottom to top before play resumes.

- Add player choice for true fast-effect-batch timing paradoxes, where effects
  described as simultaneous nevertheless require an order. The FAQ gives that
  choice to the caster of the last effect. This is distinct from upkeep actions,
  whose ordering is now explicitly chosen before they begin resolving.
- Vesuvan Doppelganger currently clears all counters gained while wearing its
  old form. This matches every implemented Beta counter source, which places
  counters through the copied creature's own abilities. If a future external
  effect can place counters on it, track counter provenance so counters from
  enchantments or other outside effects survive a form change as ruled.

# Announcement priority

- We resolve the rulebook's simultaneous-announcement conflict by giving the
  active player the first announcement in every otherwise neutral action
  window. Only one player may announce at a time; an ordinary spell or fast
  effect hands the next response to the opponent. This serialization is not
  the modern stack: ordinary effects still resolve in a simultaneous Beta
  batch, and interrupts retain their separate immediate ordering.
- A land play is a completed non-fast action. The opponent receives the first
  response opportunity and may initiate successive fast-effect batches before
  declining. Tapping a land for mana remains an immediate interrupt-speed
  action which does not itself surrender priority.
- The FAQ's statement that interrupts are always allowed applies inside the
  prevention, redirection, and regeneration parts of damage resolution and
  inside a destroy effect's regeneration window. Such an interrupt opens a
  nested interrupt sequence; once it finishes, the surrounding resolution
  window resumes without advancing. Any destruction caused by an interrupt
  is likewise completed before its surrounding damage or destruction window.
- A spell announced for use in the damage-prevention step still receives the
  ordinary dedicated interrupt window for a spell. This applies to Healing
  Salve, Guardian Angel, Reverse Damage, and Simulacrum. Activated prevention
  abilities remain fast effects rather than spells and do not gain a separate
  Counterspell-style interrupt window.
- Death Ward may likewise be announced when a creature is facing death in a
  damage or destroy-effect regeneration window, and receives the same normal
  spell interrupt window before it regenerates its target. Beta has no spell
  assigned specifically to the redirection step: its implemented redirectors
  are permanent abilities or automatic effects, so they do not create a
  Counterspell-style window. Simulacrum belongs to prevention under its ruling.

# Interrupt windows

- Announcing any spell first opens a dedicated interrupt-only window around
  that spell. Its targets, modes, X value, and costs have already been fixed,
  but it is not yet successfully cast. The opponent receives the first
  opportunity, then the caster; both must explicitly decline before ordinary
  instants and fast effects may be announced in response.
- During that window, only interrupt spells, abilities expressly usable as
  interrupts, and mana abilities usable at interrupt speed may be announced.
  Mana production resolves immediately, retains the acting player's
  opportunity, and invalidates passes already made in the current window.
- Interrupts create nested interrupt opportunities and resolve before their
  subject. Spell and activated interrupts share the rulebook's special
  ordering: those controlled by the caster of the interrupted spell take
  effect before the opponent's interrupts to that same spell, while an
  interrupt that targets another interrupt is resolved before its target.
- Once both players decline further interrupts, a surviving non-interrupt
  spell becomes successfully cast and joins the ordinary simultaneous batch.
  A fresh ordinary-response round begins with its caster's opponent. A
  successfully cast spell is no longer a legal target for Counterspell,
  Spell Blast, or an Elemental Blast's counter mode.
- Announcing a later ordinary spell therefore permanently closes the earlier
  spell's interrupt window and opens a new interrupt window only for the later
  spell. Interrupts in that new window cannot reach backward to the earlier
  spell. For example, after Lightning Bolt's interrupt window closes, casting
  Giant Growth in response makes Giant Growth (and interrupts cast upon it),
  not Lightning Bolt, the current interruptible spell.

# Upkeep action ordering

- The active player explicitly arranges all queued permanent upkeep actions
  from first to last, following the FAQ's permission to resolve their upkeep
  in any order. Each action then receives its own response window before
  resolution.
- Applicability is checked again when an action is reached. If an earlier
  action removed its source or otherwise made it inapplicable, it is skipped;
  it does not retain an effect merely because it appeared in the initial list.

# Life-total loss timing

- Ordinary damage and life loss may leave a player at zero or less without
  immediately ending the duel. Life totals are checked after phase-ending
  mana burn and at the beginning and end of each attack, following the FAQ;
  the player may recover before the next such checkpoint. Decking, concession,
  and Lich's explicit loss conditions remain irreversible.

# Trample damage resolution

- Under the FAQ sequence, trample is redirection rather than an early combat
  assignment. The full assigned packet first accumulates on its blocker;
  protection and optional prevention apply there before unprevented excess is
  redirected to the defending player as a new packet. Non-trample damage uses
  the blocker's remaining toughness before trample damage does.
- A creature that regenerated before combat damage remains an attacker or
  blocker, but combat damage cannot be assigned to or dealt by it. A sole
  regenerated blocker therefore keeps a trampler blocked without producing a
  packet from which damage can trample over. If other blockers remain, damage
  is assigned among those eligible blockers and excess can trample normally.
  A regenerated Banding blocker still grants its controller the right to
  distribute damage among the remaining blockers (WotC Rules Team 9/15/94).

# Berserk and continuous-effect order

- Power modifiers are replayed in the order they began, as required by the
  Berserk ruling. Berserk therefore doubles bonuses that were already active,
  but a modifier created after Berserk applies afterward. Changes to a
  creature's underlying or variable power recalculate the complete ordered
  sequence rather than snapshotting the doubled value.

# Summoning and attack restrictions

- `summoned_turn` records only a nonartifact creature cast as a Summon spell;
  it is deliberately distinct from entering play this turn or changing
  controller. Siren's Call and Nettling Imp exempt true summons, but affect
  summoning-sick creatures produced by Resurrection, Animate Dead, animation,
  artifact casting, or a control change, as specified by their rulings.

# Copied characteristics on battlefield departure

- A copy reverts to its printed card as it leaves play, but death processing
  first snapshots its last battlefield definition and name. Abilities such as
  Personal Incarnation's owner life loss therefore still apply to Clone and
  Vesuvan Doppelganger copies that go from play to the graveyard; exile and
  other destinations do not trigger that penalty.

# Cyclopean Tomb

- We apply the November 1994 erratum that its mire effects begin unwinding
  when Cyclopean Tomb *leaves play*, not only when it is destroyed.
- Mire effects are tracked individually. This preserves the 1994 ruling that
  one Tomb can affect the same land more than once when a newer land-type
  effect temporarily makes it non-Swamp, and that cleanup may remove an older
  effect before a newer one.

# Replaceable color and basic-land words

- Card objects carry runtime color-word and basic-land-word mappings. Rules
  code resolves declarative effect fields through the source card; printed
  mana costs, a card's own color, proper names, and player-chosen land types
  are intentionally not mapped.
- Word changes end when the affected card leaves play. Clone, Copy Artifact,
  Vesuvan Doppelganger, and Fork copies inherit the copied object's mappings,
  following the card-specific copy rulings.
- Effects created from text record the resolved word when they are created.
  This currently includes Cyclopean Tomb mire effects and Island Sanctuary's
  turn-long attack restriction.
- Targeted spells retain the requirement under which their targets were
  legally declared, but re-evaluate those targets using their current wording
  after interrupts. A wording change may invalidate a target; it cannot make
  an illegal declaration retroactively legal. Each invalid target portion
  fizzles independently, while X, target count, and damage division remain
  the values declared during casting.
- An activated fast effect snapshots the wording of its ability when it is
  activated. Later changes to the source card do not rewrite an effect that
  has already been generated.
- The Clone and Vesuvan Doppelganger rulings explicitly make Hack/Sleight
  modifications part of the copied text. We apply the same copied-text rule
  to Copy Artifact and Fork. Each copy receives an independent snapshot when
  the copy is created; later changes to the original do not propagate.
  Copy Artifact nevertheless remains blue, Vesuvan Doppelganger remains blue,
  and Fork's copy remains the color named by Fork, as their individual rules
  specify. These color-setting rules are distinct from copying color words in
  a text box.
- When Vesuvan Doppelganger changes form, its former copied object is treated
  as leaving play. Its former Hack/Sleight mappings are therefore replaced by
  the new target's mappings rather than accumulated across forms.
- Magical Hack and Sleight of Mind can target only a card being cast or a
  permanent whose current text box contains an applicable word. Card-name
  occurrences are excluded as proper nouns. Written words such as "red" and
  "Island" are replaceable; mana symbols such as `{R}` and a basic land's
  type-line name are not. The Beta dual-land text writes both its land types
  and mana colors, so Hack can change its counted land subtype independently
  of Sleight changing the color its corresponding mana ability produces.
- The old word, new word, target, and all other casting decisions are fixed
  before opponents may interrupt. If an earlier interrupt removes the chosen
  old word, the later Hack or Sleight fizzles rather than silently changing a
  different occurrence.
- Animate Dead targets a creature card while it is in a graveyard, where
  protection abilities do not function; it can therefore return White Knight.
  The returned card is newly summoned under Animate Dead's caster's control,
  retains its own casting cost, and receives -1 power but no toughness change.
  If the enchantment leaves play, the linked creature is returned to its
  owner's graveyard; moving the creature elsewhere first merely discards the
  now-unattached enchantment.
- Clone and Vesuvan Doppelganger choices made while entering through Animate
  Dead use the ordinary copy-choice UI. In accordance with their individual
  rulings, a Clone or Doppelganger that copies a creature currently sustained
  by Animate Dead immediately dies; animating the dead copy card itself does
  not cause that outcome.

# Face-down creatures

- Beta face-down creatures retain their real characteristics; they are not
  modern nameless 2/2 creatures. Their continuous effects and abilities keep
  working, but players who have not seen the face know only the creature's
  public game state. Target declarations may therefore gamble on hidden
  characteristics and fizzle when the real card is checked on resolution.
- A creature's controller may see its face. If control changes while it is
  face down, the new controller may also look and prior knowledge is retained.
  Counters and the number of attached enchantments remain public, while the
  attached enchantment faces are concealed along with the creature.
- The concealment reason is recorded explicitly. Illusionary Mask creatures
  turn face up upon actually tapping or dealing or receiving unprevented
  damage. Camouflage creatures wait for Camouflage's eventual combat reveal
  procedure. Moving a face-down card out of play reveals it.
- Illusionary Mask's ability does not tap the Mask. It casts only a genuine
  nonartifact Summon card from its controller's hand, paying the card's real
  colored/generic (and, where applicable, real X) cost plus an independent
  nonnegative Mask X. The spell is concealed during its interrupt window;
  opponents may gamble with characteristic-dependent interrupts, which are
  checked against the true spell only on resolution. The Mask X is an
  additional disguise payment and is not part of the creature spell's
  casting cost for effects such as Spell Blast. Any normal casting decision,
  such as Clone's copy choice, is still made before the concealed spell is
  committed. Destroying the Mask does not reveal creatures it summoned.
- Clone and Vesuvan Doppelganger use the concealed creature's true copyable
  characteristics internally. Those copied traits remain hidden from a
  player who could not see the original until the original is revealed.
- Camouflage is an ordinary instant and may be cast outside combat (where it
  does nothing), but it conceals attackers only while fast effects are being
  played after attackers and before blockers. The engine shuffles those
  attackers once and preserves that order through blocker declaration and UI
  perspective changes. The defender assigns blockers to the concealed
  positions; all attackers are then revealed and block assignments that are
  impossible because of concealed characteristics are removed. Camouflage's
  special concealed-defense procedure supersedes ordinary Lure and Blaze of
  Glory assignment requirements for that declaration, while already-public
  Raging River sides remain binding.

# Controlled casting decisions

- Spell state distinguishes the player who actually casts a spell from the
  player who makes that spell's decisions. Ordinary spells use the same player
  for both roles. The actual caster still pays, controls the spell/permanent,
  and receives cast-related effects; the decision-maker chooses targets and
  caster-owned resolution choices such as a Demonic Tutor search.
- Land-only payment planning is non-mutating. It includes the prospective
  payer's pool, current land mana modes, and mana added by effects such as Wild
  Growth, Mana Flare, and Gauntlet of Might, while excluding nonland mana
  sources. A selected plan can also be checked against Word of Command's
  ruling that excess land mana may not be produced when an exact plan exists.
- Word of Command is allowed to resolve before its private hand choice begins,
  so it can still be countered normally but cannot be countered after the hand
  has been seen. If a legal card exists, its caster must choose one; the
  commanded card is then announced as a spell cast by the opponent and opens
  a fresh interrupt window. The Word caster chooses X, modes, targets, lands,
  land mana modes, and the colors spent from an existing mana pool.
