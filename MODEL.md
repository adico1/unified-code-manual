# Seed, flow, boundaries, and manifestation

## Normal case

`main.py` is the original handwritten learning artifact.
`normal/reference.py` is its frozen reference snapshot. They help compare human
construction with seed construction, but they are not generator inputs.

The generated normal calculator is authoritative from:

```text
seeds/normal.seed.json
```

## Seed

A seed is the complete application program in structured data:

```text
identity
+ semantic contract
+ state and transitions
+ presentation and controls
+ boundaries and effects
+ structured executable program
+ acceptance cases
```

A seed does not select hidden calculator implementations in the compiler.

## Flow

Flow is behavior over time:

```text
control event
→ named route
→ generated state transition
→ generated result or error
→ generated presentation
```

The exact physical functions implementing that flow are present in
`program.ast` and become specialized source before runtime.

## Boundaries

Each seed names its authority crossings:

| Boundary | Direction | Meaning |
| --- | --- | --- |
| `tk.input` | inward | A control event enters the generated program |
| `tk.display` | outward | Generated state becomes visible |
| `tk.window` | outward | Tk owns the physical window and event loop |
| `process.case` | inward-outward | Canonical JSON enters and leaves the acceptance interface |

Additional boundaries must be declared by the seed that uses them.

## Build time and runtime

```text
build time:
seed → validate → decode structured program → specialize → test → hash → install

runtime:
generated main.py + user events → results and GUI effects
```

The runtime does not parse or interpret the seed. It contains only the selected
program.

## Authority law

```text
seed describes and programs the application
compiler translates generic structure
generated application executes
```

If changing application behavior requires adding calculator vocabulary to the
compiler, the boundary has regressed.
