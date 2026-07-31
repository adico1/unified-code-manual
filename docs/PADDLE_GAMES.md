# Paddle-game application family

## Bounded claim

This repository does not claim to enumerate every branded Pong-like product.
The market has no closed, authoritative list, and new variations continue to
appear. It instead records a capability taxonomy and proves the profiles that
the current bounded-simulation language can generate honestly.

Market examples show recurring axes:

- classic local scoring and multiplayer;
- deterministic or adaptive computer opponents;
- wall-return survival;
- doubles and four-sided play;
- multiple simultaneous projectiles;
- obstacles, altered geometry and environmental hazards;
- power-ups and specialized projectiles;
- timed and score-attack contracts;
- online authoritative multiplayer;
- progression, bosses and role-playing systems;
- ball-control puzzles and three-dimensional arenas.

Representative sources include Atari's
[PONG Quest](https://atari.com/products/pong-quest), which combines classic
matches, multiplayer, progression and specialized balls; Atari's
[qomp2](https://atari.com/products/qomp2), which turns the ball into a puzzle
subject; and [spinserve.io](https://spinserve.io/about/), which documents an
authoritative network host, power-ups and several input projections.

## Proven profiles

Eight profiles are generated and verified:

```text
classic local duel
solo deterministic opponent
wall-return training
two-versus-two doubles
multiball duel
power-up zone arena
obstacle arena
timed score attack
```

They share one generic build-time language:

```text
bounded simulation seed
→ resolve controls and family authority
→ specialize motion, controllers, boundaries, collisions and thresholds
→ generate exact Python AST, Tk canvas, callbacks and tests
→ atomically install
→ execute acceptance and real-GUI self-tests
```

The compiler contains construction vocabulary such as `motion`, `boundary`,
`collision`, `threshold`, `controller`, `render`, and `tick`. Product names,
entity identities, arena layouts, speeds, scoring fields, controls and
acceptance outcomes remain in seeds.

## Catalogued but not yet proven

Six market categories remain explicit open profiles:

```text
four-way arena
authoritative online multiplayer
progression and bosses
ball-control puzzle
three-dimensional arena
alternate geometry
```

They are not runnable products yet. Network play requires a pinned network and
latency boundary; 3D requires a projection and collision contract; progression
requires inventory and campaign state; alternate geometry requires non-axis-
aligned collision primitives. Marking these profiles `catalogued` prevents a
name or decorative field from being presented as working behavior.

## What the third family proves

The same public operation now assembles calculators, persistent record
managers, a cross-family calculated Todo, and bounded real-time simulations.
That is stronger evidence that the repository contains an application
language, rather than only a calculator generator. It is not proof of arbitrary
games, arbitrary applications, network correctness, or every commercial
product.
