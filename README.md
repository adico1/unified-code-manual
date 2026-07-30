# From Seeds to Apps — Ten Calculators

This repository is the handwritten learning track beside
[Unified Code](https://github.com/adico1/unified-code). It is an experimental
proof of one precise boundary:

```text
one pinned בלי_מה authority
→ one calculator-family base seed
→ ten application מה seeds
→ one generic build-time assembly compiler
→ ten exact specialized applications
```

It does not claim full Standard Ten, UEM, self-hosting, or representation of
every possible calculator.

## One operation

Generate and verify all ten applications:

```bash
python3 tools/verify_all.py --generate-only
```

Generate, verify, and open all ten GUIs:

```bash
python3 tools/verify_all.py
```

List the registered seed programs:

```bash
python3 tools/verify_all.py --list
```

Publish the verified repository and article through one words-in operation:

```bash
python3 tools/publish.py \
  "publish From Seeds to Apps with the proven technical claim" \
  --execute
```

The operation verifies everything before its first external write, pushes the
exact verified commit to GitHub `main`, and idempotently creates or updates the
canonical adico.tech article through WordPress REST. WordPress authority is
read from `ADICO_WORDPRESS_USER` and `ADICO_WORDPRESS_APP_PASSWORD`; credentials
are never stored in the repository.

## Source boundary

- `examples/original_handwritten_calculator.py` is the author's original
  handwritten work. The compiler never reads or edits it.
- `seed/bases/בלי_מה.seed.json` contains invariant construction authority.
- `seed/families/calculator.seed.json` specializes that authority for the
  calculator family.
- `seed/applications/*.seed.json` are ten application-specific מה seeds.
- `tools/modify_seeds.py` deterministically migrates and re-pins the complete seed
  graph.
- `src/seed_compiler.py` is the generic structured-program compiler.
- `seed/suite.seed.json` lists the ten seed paths and output paths; it
  contains no application behavior.
- `tools/verify_all.py` performs generation, acceptance, isolation, deterministic
  rebuilding, source-separation checks, and optional launch.
- `build/` contains disposable applications and evidence and is ignored.

The ten applications are:

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
```

## Seed authority

Each application מה seed declares:

```text
canonical identity and calculator variation
numeric laws and operations
state fields
GUI title, theme, layout, controls, identities and arguments
acceptance cases
```

The family base supplies the six ordered build-time stampers for one body,
registered
control routes, physical boundaries, rendering defaults, and error rules.
Transitions, reachable errors, and negative cases are derived from each leaf's
selected controls and operations, so those truths are not repeated ten times.

The resolved declarations are the complete application program. At build time
the calculator declaration language composes the six stampers around the
selected computation core and translates the result into a specialized Python
AST. No leaf seed contains an AST or source blob. The generic compiler writes
the application and generated tests, records seed-to-source traceability,
verifies positive and derived negative acceptance, and installs the result
atomically.

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

See [the proof](docs/PROOF.md) for measured evidence and
[the language specification](docs/LANGUAGE.md) for the language boundary.
Publication-ready article and announcement copy are collected in
[the publication package](docs/PUBLICATION.md).
