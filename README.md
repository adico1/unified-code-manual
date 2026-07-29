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
python3 run_all.py --generate-only
```

Generate, verify, and open all ten GUIs:

```bash
python3 run_all.py
```

List the registered seed programs:

```bash
python3 run_all.py --list
```

## Source boundary

- `main.py` is the author's original handwritten work and remains available
  for comparison. The compiler never reads or edits it.
- `normal/reference.py` is the frozen handwritten reference.
- `seeds/bases/בלי_מה.seed.json` contains invariant construction authority.
- `seeds/bases/calculator-family.seed.json` specializes that authority for the
  calculator family.
- `seeds/*.seed.json` are ten application-specific מה seeds.
- `seed_modifier.py` deterministically migrates and re-pins the complete seed
  graph.
- `universal_generator.py` is the generic structured-program compiler.
- `calculator_suite.seed.json` lists the ten seed paths and output paths; it
  contains no application behavior.
- `run_all.py` performs generation, acceptance, isolation, deterministic
  rebuilding, source-separation checks, and optional launch.
- `generated*/` contains disposable specialized applications.

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
validation and deterministic errors
state fields and state-transition routes
GUI title, theme, layout, controls, identities and arguments
physical boundaries and effects
complete structured program
acceptance cases
```

`program.ast` is executable structured data, not the name of behavior hidden in
the compiler. It contains the exact program to compile. The compiler translates
generic Python AST nodes, writes the specialized application and generated
tests, records seed-to-source line traceability, verifies acceptance, and
installs the result atomically.

Every leaf references its immediate base by exact canonical identity, relative
path and SHA-256. Resolution rejects floating references, altered bases,
conflicting truths and ancestry cycles.

Maintain or verify the complete graph:

```bash
python3 seed_modifier.py --apply
python3 seed_modifier.py --check
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

See [PROOF.md](PROOF.md) for measured evidence and
[CALCULATOR_LANGUAGE.md](CALCULATOR_LANGUAGE.md) for the language boundary.
