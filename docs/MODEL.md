# Seed, flow, boundaries, and manifestation

## Normal case

`examples/original_handwritten_calculator.py` is the original handwritten
learning artifact. It helps compare human construction with seed construction,
but it is not a generator input.

The generated normal calculator is authoritative from:

```text
seed/applications/normal.seed.json
```

## Recursive seeds

A seed may be the base authority of another seed:

```text
בלי_מה
→ calculator-family seed
→ application מה seed
→ generated application
```

`בלי_מה` contains invariant construction laws. The calculator-family seed adds
family invariants. The leaf מה seed contains the complete selected application:

```text
identity
+ semantic contract
+ state
+ presentation and controls
+ structured executable program
+ acceptance cases
```

A base reference contains exact identity, relative path and content hash. A
child cannot silently select a floating version or override a conflicting
truth.

The calculator-family authority contains the unchanging family law:

```text
six ordered stamp identities
+ control-action routes
+ physical boundaries
+ GUI rendering defaults
+ error derivation rules
+ negative verification vectors
```

The leaf does not repeat those truths. During base resolution, the compiler
derives one transition from each control, derives only reachable errors, and
adds the matching negative cases.

## Six build-time stampers

The compiler assembles six transformations around the selected computation
core:

```text
יה inward:
01 outer_to_inner

יהוה internal:
02 inner_to_core
03 core_prepare
04 core_collect
05 core_to_inner

יה outward:
06 inner_to_outer
```

Together the six are the registered `צבאות` assembly surface. They run before
Python compilation. They are not runtime templates, and the generated
application contains no stamper registry or seed interpreter.

## Flow

Flow is behavior over time:

```text
control event
→ named route
→ generated state transition
→ generated result or error
→ generated presentation
```

The build-time declaration compiler derives the transitions and exact physical
functions, then generates the Python AST. No transition table or AST is stored
in a leaf seed.

## Boundaries

The calculator-family seed names the shared authority crossings:

| Boundary | Direction | Meaning |
| --- | --- | --- |
| `tk.input` | inward | A control event enters the generated program |
| `tk.display` | outward | Generated state becomes visible |
| `tk.window` | outward | Tk owns the physical window and event loop |
| `process.case` | inward-outward | Canonical JSON enters and leaves the acceptance interface |

An application-specific boundary must first be registered by the authoritative
family vocabulary before a leaf can select it.

## Build time and runtime

```text
build time:
resolve pinned bases → validate מה → decode program → specialize
→ test → hash → install

runtime:
generated main.py + user events → results and GUI effects
```

The runtime does not parse or interpret the seed. It contains only the selected
program.

## Authority law

```text
בלי_מה defines invariant construction authority
base seeds specialize lawful potential
מה describes and programs the selected application
compiler translates generic structure
generated application executes
```

If changing application behavior requires adding calculator vocabulary to the
compiler, the boundary has regressed.
