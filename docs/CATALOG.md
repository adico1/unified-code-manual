# Application Profile Catalog

This catalog maps application variation without presenting every named profile
as an implemented proof.

```text
64 named profiles
├── 32 calculator profiles
└── 32 Todo profiles
```

Each entry in [`seed/catalog.seed.json`](../seed/catalog.seed.json) has one of
two states:

- `proven` — a checked seed exists in the application suite and generates a
  runnable, self-testing application.
- `catalogued` — the application variation has a canonical identity and a
  bounded capability declaration, but no runnable proof is claimed yet.

The current counts are:

| Family | Profiles | Proven | Catalogued |
| --- | ---: | ---: | ---: |
| Calculator | 32 | 12 | 20 |
| Todo | 32 | 1 | 31 |
| Total | 64 | 13 | 51 |

## What the catalog measures

The profiles enumerate semantic capability combinations, not brands, websites,
or duplicate products. A branded application can implement several profiles,
and several branded applications can implement the same profile.

The catalog is therefore larger than the present proof without making the
false claim that every profile is already generatable. Promotion from
`catalogued` to `proven` requires:

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

## Expansion rule

New names are useful only when they introduce a distinct capability contract.
Aliases and competing brand names do not increase the language proof.
Eventually, a versioned seed language should generate every valid capability
combination expressible in that language. The catalog records the bounded
frontier; it does not claim an enumerable total for every calculator or Todo
application on Earth.
