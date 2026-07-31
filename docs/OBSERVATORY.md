# Development Observatory

The Development Observatory is the fourth user-facing product group generated
by the manual application language.

```text
seed/applications/development-observatory.seed.json
→ generic stateful compiler
→ API + responsive Tk APP + CLI
→ generated tests, traceability and manifest
```

Run the complete assembly, then open the product:

```bash
./uc
python3 build/dashboards/development-observatory@1/application/main.py
```

The initial snapshot separates past, present and future development records.
The generated responsive surface presents a concise SDLC table, a measured
summary, and a separate read-only detail panel; records are not flattened into
one presentation string. Table columns, headings, detail fields and their
order are declared by the application seed and verified by generated GUI
self-tests.
Its second generated tab enumerates all 74 proven products with product group,
variation, canonical identity and proof status. The portfolio is declared in
the application seed; the generic compiler contains none of those identities.
All eight controls are exercised through nine generated Tk interaction paths:
request, both complete and reopen directions, open-code OUTWARD routing,
delete, and all four temporal filters. The proof asserts selected-record
effects, visible counts, restart persistence, error outcome and captured
outward calls rather than counting coverage.
Every record carries four observation verdicts:

- `הבט` — physical presence;
- `ראה` — canonical identity and relation;
- `חקור` — measured execution evidence;
- `הבן` — authority, meaning and next decision.

`מלך_עולם` records the canonical authority still required or already engraved.
`אדון_הכל` records which physical projections—such as API, APP, CLI or the
repository—have manifested and passed. These are engineering identifiers, not
historical or theological claims.

The `Ask AI` control stores a durable local request as a future observation.
It does not silently contact an AI service or create a GitHub issue. External
writes require a separately authorized OUTWARD boundary. `Open Code` is an
explicit outward URL boundary and is replaceable in tests.

The callable API remains one Thing in and one Thing out. The CLI accepts the
same case envelope:

```bash
python3 build/dashboards/development-observatory@1/application/main.py \
  --case-json '{"steps":[{"command":"create","arguments":{"title":"Review request"}}]}'
```

## Honest boundary

The current product embeds a deterministic, commit-addressed development
snapshot at build time. It does not poll Git, GitHub or an AI service at
runtime. A future live observer must add generic, audited read boundaries and
must not place repository-specific vocabulary in the compiler.
