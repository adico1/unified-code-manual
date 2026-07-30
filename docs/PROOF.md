# Reproducible proof

## Claim under test

```text
pinned recursive seed graph
→ generic build-time compilation
→ exact standalone application and generated tests
```

Application meaning is represented by each seed's semantic contract,
transitions, interface, boundaries, and acceptance cases. The compiler owns
only parsing, validation, generic AST construction, rendering,
emission, hashing, traceability, verification, and atomic installation.

## Reproduce

```bash
python3 tools/verify_all.py --generate-only
```

The operation requires:

1. exactly one pinned בלי_מה root, one family base and ten leaf מה seeds;
2. ten distinct generated application sources;
3. all seed-declared acceptance cases to pass;
4. generated tests for every application;
5. copied execution without seed, compiler, or repository access;
6. byte-identical second builds in independent directories;
7. no seed or compiler loading path in generated runtime source;
8. zero selected application vocabulary in the compiler;
9. exact seed, compiler, file, and tree hashes;
10. declaration-section and event-route to generated-source traceability;
11. rejection of altered, floating, cyclic and conflicting base authority.
12. zero stored leaf ASTs and ten build-time-generated ASTs.

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
seed-graph rejection proofs = 4/4
stored leaf ASTs = 0
build-time-generated ASTs = 10/10
```

Open all ten generated Tk applications:

```bash
python3 tools/verify_all.py
```

## Honest boundary

- `examples/original_handwritten_calculator.py` remains a handwritten learning
  artifact, but it is not an input to generation.
- The concise declarations now generate the Python AST; it is no longer copied
  into each application seed.
- Recursive seed ancestry is content-addressed, and every formula, operation,
  transition, control and acceptance case remains explicit data.
- Adding behavior expressible by the registered declaration vocabulary requires
  only a seed change.
- A genuinely new semantic primitive requires a generic language extension.
- A new target language requires a generic compiler projection.
- This does not prove every possible calculator, every GUI toolkit, full
  Standard Ten conformance, or root-seed self-hosting.
