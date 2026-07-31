# Standard Ten — converged contract

Version: `TEN-1`.

1. Every public Part receives one canonical Thing and returns one canonical Thing.
2. Composition is nested Parts, not object graphs.
3. `seed/ROOT.seed.json` is the one pinned semantic authority.
4. Application source and application tests are generated from declarations.
5. Domain and composition use plain data and functions; no user-defined classes.
6. Application choice and repetition are declared as events, routes and audited primitives.
7. UEM is the canonical machine interface; physical hosts remain independent boundaries.
8. INWARD and OUTWARD boundaries name every physical effect and failure.
9. Generation, results and ordered evidence are deterministic.
10. Acceptance, mutation, isolation, traceability and fixed-point evidence are generated.

Canonical Thing states remain distinct:

```text
unknown | absent | false | formed | valid | invalid
```

Every generated application exposes `part(thing) → thing`. The generated
Tk/process implementation is a physical boundary. Application meaning remains
in the resolved seed. Runtime files neither load a seed nor import the compiler.

Exactly ten semantic depths are pinned by `בלי_מה`; generation passes may
repeat, but may not create an eleventh semantic depth.
