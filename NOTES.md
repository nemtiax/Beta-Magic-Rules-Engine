# Deferred tasks

## Era rulings adopted after the reference compilation

- Graveyard ordering (bethmo, 1994-05-03): "If multiple cards go to the
  graveyard at the same time, you may choose what order they get stacked in."
  We interpret "you" as the owner of that graveyard. Each affected owner
  orders their own simultaneous group from bottom to top before play resumes.

- Add player choice for true timing paradoxes, where simultaneous effects
  require an order. The FAQ gives that choice to the caster of the last effect.
- Generalize response windows beyond spells and the existing combat windows,
  especially after land plays and before phase endings.
- Vesuvan Doppelganger currently clears all counters gained while wearing its
  old form. This matches every implemented Beta counter source, which places
  counters through the copied creature's own abilities. If a future external
  effect can place counters on it, track counter provenance so counters from
  enchantments or other outside effects survive a form change as ruled.
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
