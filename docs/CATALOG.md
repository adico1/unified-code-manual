# Application Profile Catalog

This catalog maps and proves 64 bounded application variations.

```text
64 named profiles
├── 32 calculator profiles
└── 32 Todo profiles
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
| Total | 64 | 64 | 0 |

## What the catalog measures

The profiles enumerate semantic capability combinations, not brands, websites,
or duplicate products. A branded application can implement several profiles,
and several branded applications can implement the same profile.

All current profiles have completed this promotion:

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

The original 13 programs remain direct leaf seeds. The other 51 profiles carry
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

## Expansion rule

New names are useful only when they introduce a distinct capability contract.
Aliases and competing brand names do not increase the language proof.
The versioned seed language generates every profile currently registered here.
This is a finite, reproducible claim. It does not claim an enumerable total for
every calculator or Todo application on Earth, nor that every imaginable
future semantic primitive is already expressible.
