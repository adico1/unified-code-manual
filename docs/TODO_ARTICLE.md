---
title: "When a Calculator Generator Produced a Todo App"
slug: "when-a-calculator-generator-produced-a-todo-app"
status: ready
date: 2026-07-31
keywords: todo, task, application language, calculator, seed
evidence: TODO_PUBLICATION.md
---

# When a Calculator Generator Produced a Todo App

Yesterday this repository generated calculators. Today I asked it for
something outside that family: a persistent Todo application.

The question was deliberately narrow:

> Can one seed-to-application assembly operation generate both calculators and
> a stateful Todo product without hiding Todo behavior in the compiler?

The answer is now **yes, within the explicitly registered language**.

## What changed

The calculator work had already established:

```text
calculator seed
→ build-time specialization
→ standalone calculator
→ generated tests
→ real GUI callback verification
```

The next seed required different meaning:

```text
add A
→ add B
→ complete A
→ persist
→ restart
→ recover A completed and B open
```

That behavior could not honestly be represented by the calculator declaration
language. I did not add branches such as `if application == "todo"` or
`if command == "complete"` to the generator.

Instead, the declaration language gained domain-neutral vocabulary:

```text
typed command arguments
guards: non_empty, exists, unique
collection effects: append, update, remove
state effects: increment, set
values: literal, argument, state, matched field, not, add, object
interface sources: input, selection, literal
atomic persistence
```

The Todo seed then supplied all application-specific meaning:

```text
application identity
tasks, title and completed fields
initial state
commands and errors
state transitions
filter behavior
GUI controls and positions
persistence identity
acceptance sequences
real GUI self-test cases
```

The compiler does not contain `todo`, `tasks`, `completed`,
`duplicate-title`, or `unknown-item` behavior. It translates generic
declarations into exact Python syntax before Python compilation.

## One operation, two application families

The repository now has one public operation:

```bash
python3 tools/single_api.py
```

That operation resolves the same pinned authority graph and performs the same
assembly stages for:

- twelve calculator applications;
- one persistent Todo application.

The calculator projection specializes mathematical expression declarations.
The stateful-interface projection specializes commands, guards, collection
effects, persistence, and controls. Both use the same authority resolution,
atomic installation, generated-test, traceability, isolation, deterministic
rebuild, and real-GUI verification boundaries.

This is not one universal runtime. Every generated product contains only its
selected code. The Todo runtime does not contain calculator functions, and the
calculators do not contain stateful-list behavior.

## Measured result

```text
applications                              13
calculator applications                   12
persistent Todo applications               1
positive and negative acceptance           59/59
isolated copied execution                  13/13
generated callback wiring                 294/294
application-owned real GUI self-tests     294/294
Todo GUI controls                            7/7
self-test applications closed              13/13
compiler application-vocabulary hits        0/135
manual application code                     0
manual application tests                    0
runtime seed access                         0
deterministic repeated build                PASS
complete-tree SHA-256
21e369f99867cd2488603298948dad1cb15a166d01d4b178117d44f41dbe754b
single API elapsed                          3.68 seconds
```

The Todo acceptance evidence includes:

- invalid input leaves state unchanged;
- duplicate titles are rejected;
- unknown identities are rejected;
- valid work continues after rejected input;
- state is written through an atomic filesystem boundary;
- restart reloads the exact persisted state;
- every generated Tk button invokes its real callback;
- every proof window closes.

Two independent complete builds produce byte-identical application trees.
Copied applications run their generated tests without their source seeds,
compiler, or repository checkout.

## What this proves

The experiment now crosses an application-family boundary:

```text
one pinned construction authority
+ independent application seeds
+ registered declaration languages
+ one assembly and verification operation
= different standalone products
```

That is evidence that the project is becoming a language for generating
applications rather than remaining only a calculator generator.

## What this does not prove

It does not prove:

- arbitrary programs;
- every stateful application;
- every GUI toolkit or physical target;
- full Standard Ten conformance;
- UEM Python/C equivalence;
- root-seed self-hosting;
- that the compiler will never need another generic language primitive.

The compiler itself changed during this experiment. That fact matters. The
Todo seed exposed a missing generic stateful vocabulary, so the language was
extended without adding Todo-specific behavior. The stronger future test is a
previously unseen application expressible with no compiler change.

The honest result is still meaningful:

> One deterministic assembly operation now generates twelve calculators and a
> persistent Todo application from independent seeds, while the compiler
> remains free of the Todo application's vocabulary.

Run and inspect the proof:

[github.com/adico1/unified-code-manual](https://github.com/adico1/unified-code-manual)
