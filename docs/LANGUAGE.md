# Calculator language of languages

## Governing claim

```text
one calculator generator
+ one resolved calculator seed
= one specialized calculator
```

The `+` is a build-time operation. The seed is a program: equations are semantic
expression trees, operators and external boundaries are explicit declarations,
and every calculator selects and composes those declarations with its state and
interface. Before Python compilation, the domain-blind generator resolves only
the selected semantic graph and emits one standalone program. The compiler then
compiles that exact program. The generated runtime does not interpret the seed
and does not carry a shared all-calculators engine.

The honest bound is:

> One generator can create every calculator expressible by the registered
> calculator vocabulary. A calculator that introduces new mathematical meaning
> requires a new generic vocabulary primitive—not an application-specific
> branch hidden in the generator.

This is stronger and testable. “All possible calculators” remains a direction,
not a completed claim.

## Bring the calculator family to the table

| Family | Distinguishing semantics | Typical interface differences |
| --- | --- | --- |
| Simplest/default | digits, decimal point, `+ - * /`, clear, evaluate | small fixed grid |
| Regular | percent, sign, memory, backspace, parentheses | memory row and editing controls |
| Scientific | powers, roots, logarithms, trigonometry, constants, angle mode | shift/function layers |
| Programmer | integer bases, bit width, signedness, bitwise operators | base and word-size modes |
| Financial | time value, cash flows, rates, date conventions | worksheet-oriented keys |
| Statistical | datasets, aggregates, distributions, regressions | data-entry and result views |
| Graphing | functions, variables, domains, plots, tables | viewport, graph navigation |
| Matrix/vector | dimensions, indexing, linear algebra | structured value editor |
| Units/engineering | quantities, dimensions, conversions, prefixes | unit selectors |
| RPN | stack evaluation and stack operations | stack display, Enter, swap, roll |
| Symbolic/CAS | exact algebra, simplification, differentiation, solving | structured expression display |
| Named physical model | exact documented behavior and layout of one version | model-specific licensed profile |

The families differ along independent axes. They are not separate generators.

```text
number system
× notation
× operator/function registry
× precision and rounding
× state and memory
× modes
× error contract
× layout
× theme
× host target
```

## Default-of-defaults resolution

```text
"calculator"
→ uc://calculator-profiles/default@1
→ simplest complete calculator
```

```text
"regular calculator"
→ uc://calculator-profiles/regular@1
```

```text
"scientific calculator"
→ uc://calculator-profiles/scientific@1
```

```text
exact manufacturer/model/version
→ exact registered profile
→ pinned behavior contract
→ licensed or user-provided theme assets
```

Resolution must be deterministic. Unknown names remain unknown. A natural
language or image interpreter may produce a **draft seed**, but it must mark
uncertain controls and semantics unresolved; it cannot silently invent them.

Do not scrape or redistribute proprietary themes, firmware, logos, fonts, or
trade dress without authorization. A model profile records provenance and
licenses for every imported asset.

## GUI writes backend requirements

The GUI is not decoration added after the backend. Its selected Keys form a
requirement projection. Reusable meaning is declared once in the canonical
registry:

```json
{
  "identity": "operator.expression.add",
  "label": "+",
  "action": "append",
  "value": "+",
  "requires": "operation.add"
}
```

The application declares only the unique identity and placement:

```json
{"key": "operator.expression.add", "row": 2, "column": 3}
```

The compiler derives:

```text
control identity
→ required backend capability
→ expression grammar token
→ event route
→ state transition
→ result/error behavior
→ generated test
```

Required laws:

1. Every visible Key has one globally unique identity.
2. Every label, emitted value and action come from that identity.
3. Every position is explicit and non-overlapping.
4. Every function resolves to one registered semantic capability.
5. Every expression token is admitted by the selected grammar.
6. Every backend capability names its numeric domain and error behavior.
7. Every mode-changing control exposes the active mode.
8. Accessibility and keyboard projections must resolve from the same identity
   when declared.
9. Every event route has an acceptance case.
10. No theme may change mathematical meaning.

Validation rejects:

```text
unknown-key
invalid-key-definition
duplicate-key-identity
overlapping-grid-position
grammar-token-missing
backend-capability-missing
mode-not-visible
unlicensed-asset
unresolved-model-behavior
```

## Backend contract derived from the GUI

The backend must provide the union of requirements declared by:

- buttons and other controls;
- editable-expression grammar;
- selected numeric domain;
- state, memory, history, variables, and modes;
- output presentation;
- acceptance and error cases;
- API/CLI capabilities explicitly declared as non-GUI.

Example:

```text
buttons: 0–9, ., +, −, ×, ÷, =, clear
display: editable expression
numeric type: decimal real
division: true division

→ backend requirements:
  digits
  decimal literal grammar
  add/subtract/multiply/divide
  precedence and parentheses policy
  expression editing state
  evaluation
  division-by-zero error
  deterministic result presentation
```

A scientific `sin` button adds more than a button:

```text
sin button
→ function-call grammar
→ sine capability
→ angle-unit state
→ domain/precision contract
→ mode indicator
→ test vectors
```

## Seed layers

```text
L0 — declaration-to-AST language
     values, names, formulas, routes, state, controls and effects

L1 — expression language
     grammar, notation, precedence, evaluation semantics

L2 — calculator-family language
     regular/scientific/RPN/graphing/financial semantic contracts

L3 — interface language
     grid, display, controls, identity, accessibility, theme

L4 — projection language
     Tk, web, mobile, CLI, API, hardware keys

L5 — intent language
     “create a scientific calculator” or a GUI description
     resolves to a pinned draft seed
```

This is the “language of languages of languages”:

```text
human intent
→ semantic-contract language
→ calculator semantic language
→ interface language
→ target language
→ manifested calculator
```

Each layer translates meaning; no layer is allowed to silently invent meaning.

## Normal cases and variations

```text
normal calculator seed program
+ semantic variation
+ interface variation
+ target projection
= manifested calculator
```

The current proof uses an immutable content-addressed seed graph:

```text
seed/bases/בלי_מה.seed.json
→ seed/registries/calculator-keys.seed.json
→ seed/families/calculator.seed.json
→
seed/applications/normal.seed.json
seed/applications/regular.seed.json
seed/applications/scientific.seed.json
seed/applications/programmer.seed.json
seed/applications/financial.seed.json
seed/applications/statistical.seed.json
seed/applications/graphing.seed.json
seed/applications/matrix-vector.seed.json
seed/applications/engineering-units.seed.json
seed/applications/rpn.seed.json
seed/applications/ohms-law.seed.json
seed/applications/quadratic-polynomial.seed.json
```

The twelve leaves are application-specific מה seeds. Every base reference pins an
exact identity, relative path and SHA-256. `tools/modify_seeds.py` migrates and
re-pins the graph deterministically; the compiler rejects cycles, conflicts,
floating references and tampering.

The leaf seeds contain complete concise application declarations. Reusable
Key meaning is pinned once in the canonical registry; leaves select unique Key
identities and positions.
`src/declaration_compiler.py` generates the specialized AST from registered
numeric, state, transition and presentation vocabulary. It contains no
calculator identity, selected equation or concrete layout.

## Suite operation

`tools/verify_all.py` reads `seed/suite.seed.json`, regenerates every enabled seed,
runs generated acceptance tests in isolation, performs a second independent
build, checks seed ancestry and compiler/application vocabulary separation, and
optionally opens all twelve GUIs.
