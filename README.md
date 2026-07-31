# From Seeds to Apps — Twelve Calculators and Todo

This repository is the handwritten learning track beside
[Unified Code](https://github.com/adico1/unified-code). It is an experimental
proof of one precise boundary:

```text
one pinned בלי_מה authority
→ canonical interface registries
→ calculator and stateful-list family seeds
→ thirteen application מה seeds
→ one generic build-time assembly compiler
→ thirteen exact specialized applications
```

It does not claim full Standard Ten, UEM, self-hosting, or representation of
every possible calculator.

## One operation

Generate, build, install, execute, exercise, and close all thirteen applications:

```bash
python3 tools/single_api.py
```

This is the public development boundary. It resolves every seed into a
specialized specification and Python AST, atomically installs every generated
application, runs generated acceptance tests, invokes every real Tk Key through
its generated GUI, closes every window, and verifies a byte-identical rebuild.
Each generated application owns this self-test. Normal startup performs it once
before entering the lazy Tk event loop; proof mode performs it and exits.

Publish the verified repository and article through one words-in operation:

```bash
python3 tools/publish.py \
  "publish Todo application-family proof" \
  --execute
```

The operation verifies everything before its first external write, pushes the
exact verified commit to GitHub `main`, resolves one article from the words,
and idempotently creates or updates it through WordPress REST. It uses
`ADICO_WORDPRESS_USER` and `ADICO_WORDPRESS_APP_PASSWORD` when supplied;
otherwise it uses the authenticated WordPress session in Brave as the REST
authorization boundary. Credentials are never stored in the repository.

## Source boundary

- `examples/original_handwritten_calculator.py` is the author's original
  handwritten work. The compiler never reads or edits it.
- `seed/bases/בלי_מה.seed.json` contains invariant construction authority.
- `seed/registries/calculator-keys.seed.json` defines every reusable Key once
  under a globally unique identity.
- `seed/registries/stateful-interface-controls.seed.json` defines reusable
  stateful-interface controls and their argument sources.
- `seed/families/calculator.seed.json` specializes that authority for the
  calculator family.
- `seed/families/stateful-list.seed.json` supplies domain-neutral state,
  collection, persistence, and interface boundaries.
- `seed/applications/*.seed.json` are thirteen application-specific מה seeds.
- `tools/modify_seeds.py` deterministically migrates and re-pins the complete seed
  graph.
- `src/seed_compiler.py` is the generic structured-program compiler.
- `seed/suite.seed.json` lists the thirteen seed paths and output paths; it
  contains no application behavior.
- `tools/verify_all.py` performs generation, acceptance, isolation, deterministic
  rebuilding, source-separation checks, and parallel application self-starts
  behind the single API.
- `tools/single_api.py` is the one public seed-to-closed-GUI operation.
- `build/` contains disposable applications and evidence and is ignored.

The thirteen applications are:

```text
normal
regular
scientific
programmer
financial
statistical
graphing
matrix-vector
engineering-units
rpn
ohms-law
quadratic-polynomial
todo
```

## Seed authority

Each application מה seed declares:

```text
canonical identity and calculator variation
numeric laws and operations
state fields
GUI title, theme, layout, Key identities and positions
acceptance cases
```

The canonical Key registry supplies each selected key's label, action and
emitted value exactly once. The family base supplies callback argument
contracts, the six ordered build-time stampers for one body, registered control
routes, physical boundaries, rendering defaults, and error rules.
Transitions, reachable errors, and negative cases are derived from each leaf's
selected Keys and operations, so those truths are not repeated in every
calculator seed.

The resolved declarations are the complete application program. At build time
the calculator declaration language composes the six stampers around the
selected computation core and translates the result into a specialized Python
AST. No leaf seed contains an AST or source blob. The generic compiler writes
the application and generated tests, records seed-to-source traceability,
verifies positive and derived negative acceptance, and installs the result
atomically.

The Todo seed uses the same authority resolver, assembly operation, atomic
emitter, generated-test boundary, traceability, deterministic rebuild, and
clean-room verifier. Its stateful-interface declaration selects generic
commands, guards, collection transformations, persistence, controls, and
acceptance sequences. The compiler contains no Todo application vocabulary.
The generated application persists its exact state atomically and proves the
same state after restart without loading its seed at runtime.

Generated tests structurally verify every emitted Key callback against its
generated route signature. Traceability records both the leaf placement and
the exact registry definition, plus the selected backend capability when one
is required.

Here `יה` names building blocks and `יהוה` names organs inside the one body.
`צבאות` is reserved for their lawful parallel coordination; the current
calculator assembly does not claim that parallelism proof.

Every leaf references its immediate base by exact canonical identity, relative
path and SHA-256. Resolution rejects floating references, altered bases,
conflicting truths and ancestry cycles.

Maintain or verify the complete graph:

```bash
python3 tools/modify_seeds.py --apply
python3 tools/modify_seeds.py --check
```

The generated runtime does not load its seed, import the compiler, or require
the repository. Each output contains only:

```text
main.py
test_generated.py
traceability.json
manifest.json
```

No shared all-calculators engine is copied into an application.

## Generated evidence

Every `manifest.json` records:

```text
seed SHA-256
ordered base identities and SHA-256 values
compiler SHA-256
specialized source and test hashes
traceability hash
complete artifact-tree hash
acceptance totals
manual application code = 0
manual application tests = 0
runtime seed files = 0
runtime shared-engine files = 0
```

The aggregate operation independently rebuilds every seed in a second temporary
tree and requires byte-identical outputs. It then copies each generated
application without the repository or seed and runs its generated tests again.

Start with [how to read and review the project](docs/HOW_TO_READ.md), then see
[the proof](docs/PROOF.md) for measured evidence,
[the multi-family article](docs/TODO_ARTICLE.md), and
[the language specification](docs/LANGUAGE.md) for the language boundary.
Publication-ready article and announcement copy are collected in
[the publication package](docs/PUBLICATION.md).
