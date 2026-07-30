# Reproducible proof

## Claim under test

```text
pinned recursive seed graph
→ generic build-time compilation
→ exact standalone application and generated tests
```

Application meaning is represented by each leaf seed's semantic contract,
state, interface, operations, and acceptance cases. Pinned family authority
supplies shared boundaries, rendering defaults, registered routes, error rules,
negative vectors, and six ordered build-time stamp identities. The compiler
resolves and specializes those declarations into exact applications.

## Reproduce

```bash
python3 tools/verify_all.py --generate-only
```

The operation requires:

1. exactly one pinned בלי_מה root, one family base and twelve leaf מה seeds;
2. twelve distinct generated application sources;
3. all seed-declared and derived negative acceptance cases to pass;
4. generated tests for every application;
5. copied execution without seed, compiler, or repository access;
6. byte-identical second builds in independent directories;
7. no seed or compiler loading path in generated runtime source;
8. zero selected application vocabulary in the compiler;
9. exact seed, compiler, file, and tree hashes;
10. declaration-section and event-route to generated-source traceability;
11. rejection of altered, floating, cyclic, conflicting, and escaping base
    authority;
12. zero stored leaf ASTs and twelve build-time-generated ASTs.
13. exactly six registered build-time stampers;
14. leaf transition tables, boundaries, reachable errors, and duplicated
    numeric-law indexes are absent and deterministically derived.

Current measured result:

```text
applications = 12
acceptance = 57/57
isolated copied applications = 12/12
deterministic = PASS
runtime seed access = 0
manual application code = 0
manual application tests = 0
compiler application-vocabulary hits = 0/71
seed-graph rejection proofs = 5/5
stored leaf ASTs = 0
build-time-generated ASTs = 12/12
registered build-time stampers = 6
derived transitions = 287
derived reachable errors = 25
generated editable-input checks = 3 per application
complete tree =
371f159f7a724fcf10b965adac06fd9d17bfdf3e6f5dd600b8acfeed95cab73d
```

Open all twelve generated Tk applications:

```bash
python3 tools/verify_all.py
```

## Honest boundary

- `examples/original_handwritten_calculator.py` remains a handwritten learning
  artifact, but it is not an input to generation.
- The concise declarations now generate the Python AST; it is no longer copied
  into each application seed.
- Recursive seed ancestry is content-addressed, and every formula, operation,
  control and positive acceptance case remains explicit leaf data.
- Shared transitions, boundaries, reachable errors, and negative cases are
  derived from pinned calculator-family authority.
- Adding behavior expressible by the registered declaration vocabulary requires
  only a seed change.
- A genuinely new semantic primitive requires a generic language extension.
- A new target language requires a generic compiler projection.
- This does not prove every possible calculator, every GUI toolkit, full
  Standard Ten conformance, generated parallelism, or root-seed self-hosting.
