# Normal case, seed, flow, and boundaries

## Normal case

`main.py` is the handwritten normal case: the first concrete example from
which variations can be understood.

```text
normal case + no variation → byte-identical normal manifestation
normal case + variation seed → deliberately changed manifestation
```

The normal case is not automatically a universal law. It may contain mistakes,
unsafe choices, or accidental details. Those remain visible so each later
variation can state exactly what it changes.

## Seed

A seed is the smallest declarative statement that selects a known normal case
and records meaningful differences.

The normal seed records:

- the archetype identity and source hash;
- the named flow;
- the named physical boundaries;
- available variation seeds.

The safe-expression variation contains a fuller semantic declaration because
it changes evaluation, controls, validation, and acceptance behavior.

## Flow

Flow is the ordered movement of meaning through the application:

```text
button press
→ callback
→ expression state changes
→ display changes
```

```text
equals press
→ expression crosses evaluation boundary
→ result or error
→ display changes
```

```text
clear press
→ expression becomes empty
→ display becomes empty
```

Flow is behavior over time. It is not the button, function, or state by itself.

## Boundaries

A boundary is where the calculator crosses between authorities:

| Boundary | Direction | Meaning |
| --- | --- | --- |
| `tk.input` | inward | Tk button callback enters the program |
| `python.eval` | outward | expression is delegated to Python evaluation |
| `tk.display` | outward | program state becomes visible text |
| `tk.window` | outward | Tk owns the window and event loop |

The original `eval` call is therefore not merely an implementation line. It is
an unsafe outward authority boundary. A safer variation replaces that boundary
with a restricted arithmetic parser.

## Current truth

The normal generator uses `main.py` as an explicitly hashed archetype and
therefore reproduces it byte-for-byte. This is an archetype-plus-seed model,
not yet a seed-only proof. A future step can move every normal-case meaning
into declarative vocabulary, after which `main.py` becomes entirely disposable.
