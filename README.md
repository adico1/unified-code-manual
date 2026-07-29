# Handwritten and seed-generated calculator

This folder is the handwritten learning track beside Unified Code. It is
published independently from the Unified Code repository and root bootstrap:

<https://github.com/adico1/unified-code-manual>

> **Status: experimental proof, not full Unified Code conformance.**

- `main.py` — your live handwritten Tkinter calculator; the generator never edits it.
- `normal/reference.py` — last verified normal-case snapshot used by the showcase.
- `seed.json` — selects the handwritten normal case and names its flow and boundaries.
- `generator.py` — a small deterministic generator.
- `generated/main.py` — byte-identical manifestation of the normal case.
- `generated/manifest.json` — seed and generated-source hashes.
- `variations/safe-expression.seed.json` — a safer semantic variation.
- `MODEL.md` — precise definitions of normal case, seed, flow, and boundaries.
- `CALCULATOR_LANGUAGE.md` — calculator-family language and GUI/backend law.
- `calculator-language.schema.json` — machine-readable target seed contract.
- `universal_generator.py` — build-time compiler for calculator-family seeds.
- `calculator_suite.seed.json` — nine calculator variations.
- `showcase.json` / `run_all.py` — generate, verify, and open all ten models.

Generate and verify:

```bash
/usr/local/bin/python3 generator.py seed.json --output generated
```

Run the generated GUI:

```bash
/usr/local/bin/python3 generated/main.py
```

Exercise its non-GUI boundary:

```bash
/usr/local/bin/python3 generated/main.py --evaluate "(2+3)*4"
```

The safer variation uses Python's parsed arithmetic syntax but does not use
`eval`, so names, calls, imports, and attribute access are rejected. The normal
case intentionally preserves the original `eval` boundary unchanged.

Generate the safer variation separately:

```bash
/usr/local/bin/python3 generator.py \
  variations/safe-expression.seed.json \
  --output generated-safe
/usr/local/bin/python3 generated-safe/main.py
```

Generate, verify, and open every registered calculator:

```bash
/usr/local/bin/python3 run_all.py
```

Useful non-GUI checks:

```bash
/usr/local/bin/python3 run_all.py --list
/usr/local/bin/python3 run_all.py --generate-only
```

The same command also performs a second byte-identical build and rejects
runtime seed/profile loading. See [PROOF.md](PROOF.md) for the exact claim and
limitations.

Add future calculators to `showcase.json`; the runner needs no code change.

For the nine variations, `calculator_suite.seed.json` is an executable semantic
program rather than a configuration switchboard. It declares the operator
language, function equations, external mathematical boundaries, selected state,
controls, layout, and acceptance behavior. The domain-blind compiler specializes
those declarations at build time.

Each output contains exactly one specialized `main.py` and its build manifest.
The runtime does not contain or load a profile, seed, common calculator engine,
or capabilities belonging only to another calculator. Adding an equation,
operator mapping, calculator, control, layout, or theme changes the seed—not the
compiler. Compiler changes are reserved for a genuinely new semantic node or
target projection.

The current showcase contains ten functional models:

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
