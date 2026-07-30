# Publication package

## Canonical title

**A Seed Must Describe Meaning, Not Select Hidden Code**

Website source: [ARTICLE.md](ARTICLE.md)

## One-sentence result

One pinned seed graph and one build-time compiler deterministically generate
twelve independent, standalone calculator applications with generated tests,
zero handwritten application code, and no runtime seed interpreter.

## Evidence summary

```text
applications                              12
positive + derived negative acceptance    57/57
isolated copied execution                 12/12
build-time-generated ASTs                 12/12
registered stampers                       6
derived control transitions               287
derived reachable errors                  25
seed-graph rejection proofs               5/5
compiler application-vocabulary hits      0/128
generated editable-input checks           3 per application
runtime seed access                       0
manual application code                   0
manual application tests                  0
deterministic rebuild                     PASS
complete tree SHA-256
3a5e8a57aaecccd4c9d9de517243534cb64213ef2c02d2aa01d2ae1ac6b0445b
```

Reproduce:

```bash
git clone https://github.com/adico1/unified-code-manual.git
cd unified-code-manual
python3 tools/verify_all.py --generate-only
```

Open all twelve generated applications:

```bash
python3 tools/verify_all.py
```

## LinkedIn announcement

I built twelve different calculator products from one shared construction
infrastructure.

Not twelve templates selecting hidden handwritten behavior. Each application
seed declares its own identity, mathematical operations, formulas, state,
selected Key identities, layout, and acceptance behavior. A pinned canonical
registry defines reusable Key meaning once, and a pinned calculator-family seed
supplies the unchanging family law once. One build-time compiler specializes
the selected meaning into twelve exact standalone Python applications.

Measured proof:

- 12 independently generated applications;
- 57/57 positive and derived negative acceptance cases;
- deterministic byte-identical rebuilding;
- generated tests and seed-to-source traceability;
- zero handwritten application code or tests;
- zero runtime seed access;
- generated editable-input checks for every application.

This raises a larger economic question. Companies often rebuild equivalent
foundations while competing through product-specific interfaces and services.
Shared deterministic infrastructure could preserve independent products while
redirecting duplicated engineering effort toward meaningful differentiation.

The calculator experiment proves technical reuse. It does not prove a monetary
saving. Claims of billions or trillions remain research hypotheses until
measured transparently.

Read the article and run the proof:

https://github.com/adico1/unified-code-manual

#SoftwareEngineering #CodeGeneration #DeterministicSystems #OpenSource

## Short announcement

From seeds to apps: one pinned seed graph and one build-time compiler now
generate twelve exact, standalone calculators with generated tests, deterministic
hashes, and no runtime seed interpreter.

Technical reuse is proven at this scale. Large economic savings remain an open
measurement question.

https://github.com/adico1/unified-code-manual

## Claim-safety table

| Claim | Status | Publication wording |
| --- | --- | --- |
| Twelve calculators are generated | Proven locally | “Twelve generated applications” |
| Generated outputs are deterministic | Proven locally | “Byte-identical repeated builds” |
| Applications run without seeds | Proven locally | “Runtime seed access is zero” |
| Application code and tests are handwritten | Rejected by evidence | “Manual application code and tests are zero” |
| The architecture represents every calculator | Not proven | “Every calculator expressible by the registered vocabulary” |
| The current proof implements `צבאות` parallelism | Not proven | “One-body composition; parallel proof remains open” |
| Shared infrastructure saves money | Research hypothesis | “Could reduce duplicated engineering effort” |
| The work proves trillions in savings | Not proven | Do not publish as fact |

## Terminology

```text
בלי_מה  invariant potential and construction authority
מה      selected application meaning
יה      building block
יהוה    organs inside one body
צבאות   lawful parallel coordination of building blocks and organs
```

The current calculator proof demonstrates one-body composition. It does not
claim generated `צבאות` parallel execution.

## Pre-publication checklist

- Run `python3 tools/verify_all.py --generate-only`.
- Confirm the reported complete-tree hash matches this document.
- Confirm `git diff --check`.
- Publish the repository commit before linking it.
- Replace draft URLs only after the public repository renders correctly.
- Keep the monetary-savings statement labeled as a research hypothesis.
