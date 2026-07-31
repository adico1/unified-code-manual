# How to read and review this project

Read this repository from authority to manifestation—not alphabetically and not
by starting with generated Python.

```text
בלי_מה construction laws
→ canonical Key registry
→ calculator-family contract
→ application מה seed
→ generic build-time compiler
→ exact generated application
→ generated tests and traceability
→ complete-suite verification
```

## Three kinds of files

| Kind | Role | Review rule |
| --- | --- | --- |
| Seeds and registries | Authoritative application programs | Meaning should be declared here |
| Compiler and verification code | Generic construction machinery | It must not contain calculator-specific behavior |
| `build/**` | Disposable generated applications and evidence | Inspect it, but never correct it manually |

A generated file is not an authority. When generated output is wrong, correct
the seed, registry, family contract, or generic compiler and regenerate it.

## Reading order

### 1. Begin with the public contract

Read [`README.md`](../README.md). Identify exactly what the repository claims
and what it explicitly does not claim.

### 2. Read the invariant authority

Read [`seed/bases/בלי_מה.seed.json`](../seed/bases/בלי_מה.seed.json).

Ask:

- Which laws are shared by every generated product?
- Which values are intentionally not application choices?
- Are invariant truths duplicated in leaf seeds?

### 3. Inspect the canonical Key registry

Read
[`seed/registries/calculator-keys.seed.json`](../seed/registries/calculator-keys.seed.json).

Trace three representative identities:

```text
digit.7
operator.expression.add
action.evaluate
```

Each identity should have one unambiguous definition. A leaf application should
select and position a Key rather than redefine its generic meaning.

### 4. Read the calculator-family contract

Read
[`seed/families/calculator.seed.json`](../seed/families/calculator.seed.json).

Focus on:

- boundaries;
- callback argument contracts;
- error rules;
- registered routes;
- the six ordered build-time stampers;
- fields required from every application seed.

### 5. Read one product seed

Read
[`seed/applications/normal.seed.json`](../seed/applications/normal.seed.json).

Separate its declarations into:

```text
identity
selected operations and numeric laws
state
Key identities and grid positions
acceptance cases
presentation
```

The resolved seed is the application program. It should describe behavior, not
contain Python source or an opaque AST.

### 6. Compare a different product

Compare the normal calculator with
[`seed/applications/financial.seed.json`](../seed/applications/financial.seed.json)
or another application seed.

Ask:

- Are their differences expressed by data and semantic declarations?
- Does either product require a name-specific compiler branch?
- Does each generated application contain only its selected capabilities?

### 7. Inspect suite selection

Read [`seed/suite.seed.json`](../seed/suite.seed.json). It should select
applications and output locations without defining application behavior.

### 8. Follow seed resolution

Read [`src/seed_compiler.py`](../src/seed_compiler.py) in this order:

```text
resolve_base
→ load_seed
→ validate
→ materialize
→ render_program / render_tests
→ generate
```

`materialize` is the important joining point. It binds the pinned base,
canonical registry, family authority, and leaf application without inventing
application meaning.

### 9. Follow specialization

Read
[`src/declaration_compiler.py`](../src/declaration_compiler.py), beginning with
`compile_declaration`.

Then inspect:

```text
expression
action_routes
expression_runtime
route_source
gui_source
stamp_01_outer_to_inner
...
stamp_06_inner_to_outer
```

The compiler should translate the selected semantic graph into a specialized
Python AST. It should not carry a universal runtime containing every
calculator's behavior.

### 10. Finish at the public operation

Read:

- [`tools/single_api.py`](../tools/single_api.py)
- [`tools/verify_all.py`](../tools/verify_all.py)

The single API should orchestrate the established stages. It must not become a
second application generator or a source of calculator behavior.

## Trace one Key end to end

Start with `digit.7`:

```text
registry definition
→ application placement
→ materialized declaration
→ generated Tk Button
→ generated callback
→ callback execution
→ self-test result
→ traceability record
```

Run:

```bash
jq '.provides.key_registry[] | select(.identity == "digit.7")' \
  seed/registries/calculator-keys.seed.json

jq '.what.presentation.keys[] | select(.key == "digit.7")' \
  seed/applications/normal.seed.json

python3 tools/single_api.py

jq '.controls[] | select(.identity == "digit.7")' \
  build/normal/traceability.json

python3 build/normal/main.py --self-test
```

Repeat with `operator.expression.add`. Verify that:

1. the registry defines the Key identity, label, emitted value, and required
   capability;
2. the leaf seed selects its placement and the required operation;
3. validation rejects a missing or incompatible capability;
4. the generated callback invokes the declared route;
5. the self-test checks the resulting application effect.

## Review checklist

Record each item as `PASS`, `QUESTION`, or `BLOCK`.

### Authority

- Is application behavior declared in a seed?
- Does each meaning have one registered authority?
- Are calculator names, equations, layouts, and product behaviors absent from
  the generic compiler?
- Can a new expressible calculator be added without changing compiler code?

### Specialization

- Does the generated application contain only selected capabilities?
- Are unrelated calculator operations absent?
- Does runtime avoid loading seeds, registries, or compiler modules?
- Is generated application and test code entirely disposable?

### GUI and callback correctness

For every selected Key, verify:

- unique identity;
- correct label and grid position;
- correct route and emitted value;
- exact callback argument contract;
- execution of the real callback;
- declared visible result or deterministic error.

### Traceability

Every generated control should identify:

```text
leaf placement authority
+ canonical Key authority
+ backend capability authority, when required
+ pinned source hashes
```

A generated location alone is not proof of provenance.

### Verification honesty

- Self-tests invoke real callbacks rather than only inspecting source strings.
- Discovering zero controls cannot count as a pass.
- Acceptance assertions test semantic effects.
- Determinism compares two independently generated trees.
- Clean-room applications run without the repository or seeds.
- Normal launch self-tests once, resets state, and then enters the lazy Tk
  event loop.
- CI executes the same public operation.
- Total verification obeys the five-second law.

### Failure behavior

Deliberately inspect at least one rejected case:

- unknown Key identity;
- missing required operation;
- duplicate identity or placement;
- altered pinned base hash;
- invalid callback contract;
- failed staged installation.

Confirm that it fails before accepting a partial or misleading application.

## Working vocabulary

**Seed**  
The complete declarative application program and its pinned authorities.

**Flow**  
The ordered transformations from seed resolution through specialization,
emission, execution, and evidence.

**Boundary**  
A named crossing between semantic computation and a physical effect, such as a
Tk event, window, display update, file, or process.

**Registry**  
A canonical collection of globally unique identities and reusable contracts.

**Generated code**  
A deterministic manifestation of authority. It is inspected and executed, but
never independently authored.

## Review without drowning

Use four passes:

1. **Contract:** read the README, invariant base, family, and one leaf.
2. **Vertical slice:** trace one digit and one operator through generation and
   execution.
3. **Variation:** compare two calculators and identify shared versus specialized
   structure.
4. **Proof:** inspect failure cases, deterministic rebuilding, clean-room
   execution, traceability, and CI.

Do not accept a measured total merely because it is green. Inspect what was
counted, how it was discovered, what semantic effect was asserted, and which
authority produced it.
