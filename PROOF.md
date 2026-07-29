# Reproducible proof

## Claim under test

```text
complete seed program
→ generic build-time compilation
→ exact standalone application and generated tests
```

Application meaning is represented by each seed's structured program, semantic
contract, transitions, interface, boundaries, and acceptance cases. The
compiler owns only parsing, validation, generic AST construction, rendering,
emission, hashing, traceability, verification, and atomic installation.

## Reproduce

```bash
python3 run_all.py --generate-only
```

The operation requires:

1. exactly ten independent seed files;
2. ten distinct generated application sources;
3. all seed-declared acceptance cases to pass;
4. generated tests for every application;
5. copied execution without seed, compiler, or repository access;
6. byte-identical second builds in independent directories;
7. no seed or compiler loading path in generated runtime source;
8. zero selected application vocabulary in the compiler;
9. exact seed, compiler, file, and tree hashes;
10. top-level seed-AST to generated-source line traceability.

Current measured result:

```text
applications = 10
acceptance = 19/19
isolated copied applications = 10/10
deterministic = PASS
runtime seed access = 0
manual application code = 0
manual application tests = 0
compiler application-vocabulary hits = 0
```

Open all ten generated Tk applications:

```bash
python3 run_all.py
```

## Honest boundary

- The original `main.py` and `normal/reference.py` remain handwritten learning
  artifacts, but neither is an input to generation.
- `program.ast` is intentionally a low-level structured language. It proves
  complete seed authority more strongly than the earlier profile selector, but
  it is more verbose.
- The semantic and presentation summaries currently coexist with the
  authoritative structured program. Traceability hashes both; a future
  higher-level compiler can derive the AST from those summaries.
- Adding behavior expressible with Python AST requires only a seed change.
- A new target language requires a generic compiler projection.
- This does not prove every possible calculator, every GUI toolkit, full
  Standard Ten conformance, or root-seed self-hosting.
