# Reproducible proof

This repository is an experimental, handwritten companion to
[Unified Code](https://github.com/adico1/unified-code). It does not claim full
Standard Ten, UEM, self-hosting, or arbitrary-program conformance.

## Claim under test

```text
semantic calculator seed
→ build-time specialization
→ exact standalone calculator source
```

The seed declares calculator identities, selected operators, mathematical
equations as expression trees, constants, controls, layout, presentation, and
acceptance cases. The generated application does not load the seed or a shared
all-calculators runtime.

## Run

```bash
python3 run_all.py --generate-only
```

The command:

1. compiles the handwritten normal reference and nine seed-programmed
   variations;
2. runs all declared acceptance cases;
3. requires each specialization to contain only `main.py` and `manifest.json`;
4. generates every calculator a second time;
5. requires byte-identical outputs;
6. rejects runtime seed/profile loading.

Expected summary:

```text
acceptance = 19/19
exact-output = PASS
deterministic = PASS
runtime-authority-leak = 0
```

Open all ten Tk applications:

```bash
python3 run_all.py
```

## Honest boundary

- `main.py` is the author's live handwritten work in progress.
- `normal/reference.py` is the frozen runnable normal reference.
- The other nine applications are specialized from
  `calculator_suite.seed.json`.
- New behavior expressible through the registered semantic nodes requires only
  a seed change.
- A genuinely new semantic node or target projection still requires a generic
  language/compiler extension.
- This does not prove all possible calculators or all possible GUI behavior.
