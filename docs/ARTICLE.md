---
title: "A Seed Must Describe Meaning, Not Select Hidden Code"
slug: "a-seed-must-describe-meaning-not-select-hidden-code"
status: draft
date: 2026-07-29
---

# A Seed Must Describe Meaning, Not Select Hidden Code

While building ten calculator variations beside the Unified Code project, I
found a defect that passed every visible demonstration: the applications
worked, but the generator already contained their real behavior.

The JSON seed said:

```json
{
  "functions": ["payment", "mean", "determinant2"]
}
```

The formulas for those functions were handwritten inside the generator. The
seed selected implementations; it did not define them.

That distinction matters.

```text
configuration
→ chooses behavior that already exists elsewhere

semantic seed
→ defines behavior that a compiler manifests
```

## The failed design

The first generator knew financial formulas, statistical operations, matrix
operations, unit conversions, graphing behavior, and stack-calculator behavior.
Adding a genuinely new mathematical function required changing Python code in
the generator and then adding its name to JSON.

The generator was therefore an application library disguised as a generic
generator.

The output was generated, but its authority was divided:

```text
seed: names and presentation
generator: application meaning
```

## The correction

The calculator seed now contains its complete concise semantic program. For
example, the contract describes a
two-by-two determinant as an expression tree:

```json
{
  "id": "determinant2",
  "parameters": ["a", "b", "c", "d"],
  "body": {
    "subtract": [
      {
        "multiply": [
          {"parameter": "a"},
          {"parameter": "d"}
        ]
      },
      {
        "multiply": [
          {"parameter": "b"},
          {"parameter": "c"}
        ]
      }
    ]
  }
}
```

The build-time compiler does not contain the determinant formula. It generates
a Python AST from the declared formula, operations, routes, state and controls.
No application seed stores an AST or source blob.

This produces a different boundary:

```text
seed
→ meaning

compiler
→ generic translation

generated source
→ exact physical program
```

The generated runtime does not load the seed, interpret a profile, or import a
shared engine containing every calculator.

## The extension test

An earlier decisive experiment introduced an unseen function:

```text
triple(x) = x × 3
```

It was expressed only through seed vocabulary. The compiler generated it
without receiving a new named implementation, and:

```text
triple(7) = 21
```

The compiler SHA-256 was identical before and after the experiment.

That does not prove that every possible application can be represented.
It proves something narrower and useful:

> When a seed is intended to be the sole application authority, application
> meaning must be expressible in the seed rather than hidden behind names in
> the generator.

## Current evidence

The public experiment now contains ten seed-programmed calculator applications
derived through one content-addressed seed ancestry:

- normal;
- regular;
- scientific;
- programmer;
- financial;
- statistical;
- graphing;
- matrix and vector;
- engineering units;
- reverse Polish notation.

One command performs the build and proof:

```bash
python3 tools/verify_all.py --generate-only
```

Measured locally:

```text
10 seed programs compiled into 10 applications
19/19 acceptance cases passed
byte-identical repeated generation
isolated copied execution = 10/10
runtime seed access = 0
shared all-calculators runtime = 0
manual application code = 0
manual application tests = 0
compiler application-vocabulary hits = 0
altered/floating/cyclic/conflicting base rejection = 4/4
```

The runnable experiment is available at:

[github.com/adico1/unified-code-manual](https://github.com/adico1/unified-code-manual)

## What is not proven

This experiment does not prove:

- every possible calculator;
- every possible GUI interaction;
- full Standard Ten conformance;
- UEM Python/C equivalence;
- root-seed self-hosting;
- that compilers never require extension.

A new Python application expressible through the declaration language
changes only the seed. A new physical target still requires a generic compiler
projection.

The current seed graph separates invariant `בלי_מה` authority, calculator-family
authority and application-specific `מה`. This removes silent base selection
and the former AST duplication inside each leaf.

That boundary is not a weakness to hide. It is the measurement that keeps the
claim honest.

## The larger lesson

Generated code is not enough.

We must ask where the meaning was authored.

```text
If changing application meaning requires changing the generator,
the generator still contains application authority.
```

The goal is not to move handwritten code into a more impressive directory.
The goal is to place each responsibility where it can be named, measured,
reused, and regenerated.

The seed describes the Thing. The compiler manifests it. The generated program
executes it.
