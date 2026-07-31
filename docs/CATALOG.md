# Application Profile Catalog

This catalog maps 78 bounded application variations and currently proves 72.

```text
78 named profiles
├── 32 calculator profiles
├── 32 Todo profiles
└── 14 paddle-simulation profiles
```

Each entry in [`seed/catalog.seed.json`](../seed/catalog.seed.json) has one of
two states:

- `proven` — a checked seed exists in the application suite and generates a
  runnable, self-testing application.
- `catalogued` — reserved for a future entry whose bounded declaration exists
  but whose runnable proof has not passed.

The current counts are:

| Family | Profiles | Proven | Catalogued |
| --- | ---: | ---: | ---: |
| Calculator | 32 | 32 | 0 |
| Todo | 32 | 32 | 0 |
| Paddle simulation | 14 | 8 | 6 |
| Total | 78 | 72 | 6 |

## What the catalog measures

The profiles enumerate semantic capability combinations, not brands, websites,
or duplicate products. A branded application can implement several profiles,
and several branded applications can implement the same profile.

Every profile marked `proven` has completed this promotion:

```text
profile
→ complete seed
→ generated specialized application
→ generated acceptance and GUI self-tests
→ deterministic rebuild
→ single-API verification
```

Catalog verification rejects duplicate canonical identities, false `proven`
claims, missing seeds, mismatched generated-product identities, and empty or
duplicate capability declarations.

Fifteen programs are direct leaf seeds. Another 58 applications carry
content-addressed prototype identities and complete semantic merge
declarations. Generic build-time materialization produces their complete leaf
seeds; generated applications never read the catalog, prototype, seed,
compiler, or repository at runtime.

“Proven” means the exact bounded contract in the profile is implemented and
tested. Todo capabilities ending in `-field` are persisted record fields, not
claims that a notification, network synchronization, cryptographic, or
scheduling engine exists. The three potentially misleading identities were
therefore narrowed to `dependency-plan`, `offline-security-plan`, and
`collaboration-sync-plan`.

The six catalogued paddle profiles require network, 3D, progression, puzzle or
non-rectangular-geometry primitives that are not present. Their names do not
stand in for implementations. See [PADDLE_GAMES.md](PADDLE_GAMES.md).

## Expansion rule

New names are useful only when they introduce a distinct capability contract.
Aliases and competing brand names do not increase the language proof.
The versioned seed language generates every profile currently registered here.
This is a finite, reproducible claim. It does not claim an enumerable total for
every calculator, Todo application or paddle game on Earth, nor that every imaginable
future semantic primitive is already expressible.
