# Deferred tasks

- Add a UI damage-assignment step when an attacker is blocked by multiple
  creatures. The rules engine already accepts explicit assignments, but the
  UI currently assigns all combat damage to the first blocker automatically.
- Extend 1993 timing batches with a separate interrupt layer. Interrupts
  resolve immediately and use their era-specific ordering rather than joining
  the simultaneous fast-effect batch.
- Add player choice for true timing paradoxes, where simultaneous effects
  require an order. The FAQ gives that choice to the caster of the last effect.
- Generalize response windows beyond spells and the existing combat windows,
  especially after land plays and before phase endings.
- Represent non-mana activated fast effects as explicit members of the current
  batch. They currently take effect immediately, which is sufficient for the
  implemented self-pump abilities but will not cover every future interaction.
