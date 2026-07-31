# Cross-family composition proof

## Question

Can a Todo application use calculator semantics without adding Todo or
calculator behavior to the compiler?

## Measured construction

```text
stateful-list declaration
+ semantic-expression declaration
+ interface-control registry
→ one Costed Todo seed program
→ one exact standalone application
```

[`costed-todo.seed.json`](../seed/applications/costed-todo.seed.json) declares:

- persistent task records;
- create, update, toggle, remove, and filter transitions;
- bounded integer inputs from `0` through `1,000,000`;
- one `line_total(quantity, unit_price)` expression;
- GUI inputs, controls, layout, errors, acceptance, and self-tests.

Both calculator functions and the Costed Todo calculation are compiled by
[`semantic_expression.py`](../src/semantic_expression.py). The calculator and
stateful compilers select from that authority at build time. The generated
Costed Todo source contains exactly one specialized calculation:

```python
def _calculation_0(quantity, unit_price):
    return quantity * unit_price
```

It contains no seed loader, expression interpreter, compiler import, unused
calculator operation, or shared runtime engine.

## Traceability

The generated `traceability.json` connects:

```text
/semantics/calculations/functions/0/body
→ line_total
→ generated _calculation_0 source lines
→ create/update calls
```

The aggregate verifier mutates the declared calculation identity while leaving
its call unchanged, then independently mutates its call arity. Compilation must
reject both before emission.

## Result

```text
Costed Todo acceptance = 2/2
Costed Todo GUI self-tests = 2/2
Costed Todo Key callbacks = 7/7
cross-family mutations = 2/2
runtime expression-interpreter files = 0
manual application code = 0
manual application tests = 0
```

## Honest boundary

This proves one real composition of persistent state transitions and bounded
arithmetic through a shared declaration language. It does not prove arbitrary
cross-family composition or every possible application. A new semantic
primitive still requires a generic language extension.
