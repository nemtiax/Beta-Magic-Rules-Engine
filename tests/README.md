We want to have three kinds of tests:

- General functionality tests. This covers things like UI, the core engine, etc.
- Rules tests. These cover individual Magic rules.
- Card tests. Many cards in Beta have unique effects, we will want to give these their own tests.

Import engine façade types such as `GameState`, `Card`, and `TurnPhase` from
`beta_magic`. Import printed cards from their module under
`beta_magic.card_defs`, and import declarative ability/effect types from
`beta_magic.abilities` or `beta_magic.effects`. Mechanic-focused card tuples
used only as shared test expectations live in `tests.card_groups`.
