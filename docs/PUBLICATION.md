# Publication package

## Canonical title

**A Seed Must Describe Meaning, Not Select Hidden Code**

Website source: [ARTICLE.md](ARTICLE.md)

## One-sentence result

One pinned seed graph and one build-time compiler deterministically generate
ten independent, standalone calculator applications with generated tests,
zero handwritten application code, and no runtime seed interpreter.

## Evidence summary

```text
applications                              10
positive + derived negative acceptance    40/40
isolated copied execution                 10/10
build-time-generated ASTs                 10/10
registered stampers                       6
derived control transitions               238
derived reachable errors                  21
seed-graph rejection proofs               5/5
compiler application-vocabulary hits      0/62
runtime seed access                       0
manual application code                   0
manual application tests                  0
deterministic rebuild                     PASS
verification time                         1.82 seconds
complete tree SHA-256
a32ab7ed59713152dc9ab70c5dd29fb65d031ad158e98bb27a98e74a1c5ecb62
```

Reproduce:

```bash
git clone https://github.com/adico1/unified-code-manual.git
cd unified-code-manual
python3 tools/verify_all.py --generate-only
```

Open all ten generated applications:

```bash
python3 tools/verify_all.py
```

## LinkedIn announcement

I built ten different calculator products from one shared construction
infrastructure.

Not ten templates selecting hidden handwritten behavior. Each application seed
declares its own identity, mathematical operations, formulas, state, controls,
layout, and acceptance behavior. A pinned calculator-family seed supplies the
unchanging family law once. One build-time compiler specializes the selected
meaning into ten exact standalone Python applications.

Measured proof:

- 10 independently generated applications;
- 40/40 positive and derived negative acceptance cases;
- deterministic byte-identical rebuilding;
- generated tests and seed-to-source traceability;
- zero handwritten application code or tests;
- zero runtime seed access;
- complete verification in 1.82 seconds locally.

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
generate ten exact, standalone calculators with generated tests, deterministic
hashes, and no runtime seed interpreter.

Technical reuse is proven at this scale. Large economic savings remain an open
measurement question.

https://github.com/adico1/unified-code-manual

## Claim-safety table

| Claim | Status | Publication wording |
| --- | --- | --- |
| Ten calculators are generated | Proven locally | “Ten generated applications” |
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
