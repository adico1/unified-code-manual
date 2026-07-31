# Todo application-family publication

## Canonical title

**When a Calculator Generator Produced a Todo App**

Website source: [TODO_ARTICLE.md](TODO_ARTICLE.md)

## Evidence

```text
applications                              13
acceptance                                59/59
isolated copied execution                 13/13
generated callback wiring                294/294
application-owned real GUI self-tests    294/294
self-test applications closed             13/13
compiler application-vocabulary hits       0/135
runtime seed access                         0
manual application code                     0
manual application tests                    0
deterministic rebuild                     PASS
complete tree SHA-256
21e369f99867cd2488603298948dad1cb15a166d01d4b178117d44f41dbe754b
single API elapsed                        3.68 seconds
```

## LinkedIn announcement

Yesterday my seed compiler generated calculators. Today it generated something
outside that family: a persistent Todo application.

The Todo seed declares its fields, commands, validation, transitions, errors,
layout, controls, persistence, acceptance cases, and GUI self-tests. The
compiler contains none of the Todo application's vocabulary.

One operation now generates and verifies twelve calculators plus Todo:

```text
13 applications
59/59 acceptance cases
294/294 generated GUI callbacks
294/294 application-owned real GUI self-tests
byte-identical repeated builds
runtime seed access = 0
manual application code and tests = 0
```

This is not proof of arbitrary software. The experiment required a generic
stateful-language extension, and that limitation is documented. It is,
however, the first measured evidence that the project is becoming a language
for generating applications rather than only a calculator generator.

Read the article and run the proof:

https://github.com/adico1/unified-code-manual

#CodeGeneration #SoftwareEngineering #DeterministicSystems #OpenSource

## Claim safety

| Claim | Status |
| --- | --- |
| Twelve calculators and one Todo application are generated | Proven locally |
| Todo state persists and survives restart | Proven locally |
| Todo application vocabulary is absent from compiler sources | Proven locally |
| Repeated application trees are byte-identical | Proven locally |
| The compiler did not change for Todo | False; do not claim |
| Arbitrary applications are supported | Not proven |
| Full Standard Ten or root self-hosting is complete | Not proven |
