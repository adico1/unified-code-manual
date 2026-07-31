"""Compile a declarative bounded simulation into one specialized Python AST."""

from __future__ import annotations

import ast
import re


LANGUAGE = "bounded-simulation-declaration-1"


def safe_name(value):
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def path_source(path, root="state"):
    return root + "".join(f"[{part!r}]" for part in path)


def assignment_source(change, indent="    "):
    target = path_source(change["path"])
    operation = change["operation"]
    value = repr(change["value"])
    forms = {
        "set": f"{target} = {value}",
        "increment": f"{target} += {value}",
        "multiply": f"{target} *= {value}",
    }
    if operation not in forms:
        raise ValueError("unknown-simulation-change")
    return indent + forms[operation]


def control_source(control, index):
    lines = [f"def control_{index}():"]
    lines.extend(
        assignment_source(change)
        for change in control.get("changes", ())
    )
    lines.extend(["    present_state()", "    return snapshot()", ""])
    return lines


def motion_source(rule):
    entity = repr(rule["entity"])
    position = repr(rule["position"])
    velocity = repr(rule["velocity"])
    return f"    state['entities'][{entity}][{position}] += state['entities'][{entity}][{velocity}]"


def boundary_source(rule):
    entity = repr(rule["entity"])
    position = repr(rule["position"])
    velocity = repr(rule["velocity"])
    minimum = repr(rule["minimum"])
    maximum = repr(rule["maximum"])
    return [
        f"    if state['entities'][{entity}][{position}] < {minimum}:",
        f"        state['entities'][{entity}][{position}] = {minimum}",
        f"        state['entities'][{entity}][{velocity}] = abs(state['entities'][{entity}][{velocity}])",
        f"    if state['entities'][{entity}][{position}] > {maximum}:",
        f"        state['entities'][{entity}][{position}] = {maximum}",
        f"        state['entities'][{entity}][{velocity}] = -abs(state['entities'][{entity}][{velocity}])",
    ]


def overlap_expression(moving, target):
    left = f"state['entities'][{moving!r}]"
    right = f"state['entities'][{target!r}]"
    return (
        f"({left}['x'] < {right}['x'] + {right}['width'] and "
        f"{left}['x'] + {left}['width'] > {right}['x'] and "
        f"{left}['y'] < {right}['y'] + {right}['height'] and "
        f"{left}['y'] + {left}['height'] > {right}['y'])"
    )


def collision_source(rule):
    moving = rule["moving"]
    target = rule["target"]
    velocity = path_source(["entities", moving, rule["velocity"]])
    lines = [f"    if {overlap_expression(moving, target)}:"]
    lines.append(f"        {velocity} *= {-rule.get('scale', 1)!r}")
    for change in rule.get("changes", ()):
        lines.append(assignment_source(change, indent="        "))
    return lines


def threshold_source(rule):
    observed = path_source(rule["path"])
    operator = {"below": "<", "above": ">"}.get(rule["relation"])
    if operator is None:
        raise ValueError("unknown-simulation-threshold")
    lines = [f"    if {observed} {operator} {rule['value']!r}:"]
    lines.extend(
        assignment_source(change, indent="        ")
        for change in rule["changes"]
    )
    return lines


def controller_source(rule):
    observed = path_source(rule["observed"])
    target = path_source(rule["target"])
    step = rule["step"]
    minimum = rule["minimum"]
    maximum = rule["maximum"]
    return [
        f"    if {observed} < {target}:",
        f"        {target} = max({minimum!r}, {target} - {step!r})",
        f"    if {observed} > {target}:",
        f"        {target} = min({maximum!r}, {target} + {step!r})",
    ]


def render_source(seed):
    presentation = seed["presentation"]
    semantics = seed["semantics"]
    initial = seed["state"]["initial"]
    controls = presentation["controls"]
    canvas = presentation["surface"]
    lines = [
        '"""Generated bounded simulation. Do not edit."""',
        "from copy import deepcopy",
        "import json",
        "import sys",
        "from tkinter import Button, Canvas, Label, StringVar, Tk",
        "",
        f"APPLICATION_ID = {seed['identity']['canonical']!r}",
        "TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')",
        f"INITIAL_STATE = {initial!r}",
        f"TICK_MILLISECONDS = {semantics['clock']['tick_milliseconds']!r}",
        "state = deepcopy(INITIAL_STATE)",
        "_root = None",
        "_surface = None",
        "_status = None",
        "_buttons = {}",
        "_running = False",
        "",
        "def snapshot():",
        "    return deepcopy(state)",
        "",
        "def reset_state():",
        "    state.clear()",
        "    state.update(deepcopy(INITIAL_STATE))",
        "    present_state()",
        "    return snapshot()",
        "",
    ]
    for index, control in enumerate(controls):
        lines.extend(control_source(control, index))
    lines.extend(["def advance():"])
    for rule in semantics.get("controllers", ()):
        lines.extend(controller_source(rule))
    for rule in semantics["motion"]:
        lines.append(motion_source(rule))
    for rule in semantics.get("boundaries", ()):
        lines.extend(boundary_source(rule))
    for rule in semantics.get("collisions", ()):
        lines.extend(collision_source(rule))
    for rule in semantics.get("thresholds", ()):
        lines.extend(threshold_source(rule))
    lines.extend(
        [
            "    state['tick'] += 1",
            "    present_state()",
            "    return snapshot()",
            "",
            "def present_state():",
            "    if _surface is None:",
            "        return",
            "    _surface.delete('all')",
        ]
    )
    for entity in presentation["entities"]:
        identity = entity["identity"]
        item = f"state['entities'][{identity!r}]"
        lines.extend(
            [
                f"    _surface.create_rectangle({item}['x'], {item}['y'], {item}['x'] + {item}['width'], {item}['y'] + {item}['height'], fill={entity['fill']!r}, outline={entity.get('outline', entity['fill'])!r})"
            ]
        )
    lines.extend(
        [
            f"    _surface.create_text({canvas['width'] // 2!r}, 18, text={presentation['score_text']!r}.format(**state), fill={presentation.get('text_fill', 'white')!r})",
            "    if _status is not None:",
            "        _status.set(str(state.get('status', 'ready')))",
            "",
            "def build_interface():",
            "    global _root, _surface, _status",
            "    _root = Tk()",
            f"    _root.title({presentation['title']!r})",
            f"    _root.geometry({presentation['geometry']!r})",
            f"    _surface = Canvas(_root, width={canvas['width']!r}, height={canvas['height']!r}, bg={canvas['background']!r}, highlightthickness=0)",
            f"    _surface.grid(row=0, column=0, columnspan={max(1, len(controls))!r})",
        ]
    )
    for index, control in enumerate(controls):
        lines.extend(
            [
                f"    _buttons[{control['id']!r}] = Button(_root, text={control['label']!r}, command=control_{index})",
                f"    _buttons[{control['id']!r}].grid(row={control['row']!r}, column={control['column']!r}, sticky='nsew')",
                f"    _root.bind({control['binding']!r}, lambda event, operation=control_{index}: operation())",
            ]
        )
    lines.extend(
        [
            "    _status = StringVar(value='ready')",
            f"    Label(_root, textvariable=_status).grid(row={presentation['status']['row']!r}, column=0, columnspan={max(1, len(controls))!r})",
            "    present_state()",
            "    return _root",
            "",
            "def run_case(case):",
            "    reset_state()",
            "    operations = {",
        ]
    )
    lines.extend(
        f"        {control['id']!r}: control_{index},"
        for index, control in enumerate(controls)
    )
    lines.extend(
        [
            "    }",
            "    for step in case['steps']:",
            "        operation = step.get('control')",
            "        if operation is not None:",
            "            operations[operation]()",
            "        for _ in range(step.get('ticks', 0)):",
            "            advance()",
            "    return snapshot()",
            "",
            "def part(thing):",
            "    result = run_case(thing['value'])",
            "    return {'value': result, 'depths': TEN_DEPTHS, 'axes': tuple(thing.get('axes', ())), 'evidence': tuple(thing.get('evidence', ())) + ('boundary:inward', 'part:run_case', 'boundary:outward'), 'state': 'valid'}",
            "",
            "def run_acceptance():",
            f"    cases = {seed['acceptance']!r}",
            "    results = [run_case(case['input']) == case['expected'] for case in cases]",
            "    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}",
            "",
            "def self_test_application():",
            "    root = build_interface()",
            "    root.withdraw()",
            f"    cases = {presentation['self_tests']!r}",
            "    checks = []",
            "    for case in cases:",
            "        reset_state()",
            "        for step in case['input']['steps']:",
            "            control = step.get('control')",
            "            if control is not None:",
            "                _buttons[control].invoke()",
            "            for _ in range(step.get('ticks', 0)):",
            "                advance()",
            "        checks.append(snapshot() == case['expected'])",
            f"        checks.append(len(_surface.find_all()) == {len(presentation['entities']) + 1!r})",
            "    root.destroy()",
            "    return {'self_test': {'passed': sum(checks), 'total': len(checks)}, 'closed': True}",
            "",
            "def scheduled_tick():",
            "    if _running:",
            "        advance()",
            "        _root.after(TICK_MILLISECONDS, scheduled_tick)",
            "",
            "def launch():",
            "    global _running",
            "    proof = self_test_application()",
            "    if proof['self_test']['passed'] != proof['self_test']['total']:",
            "        raise RuntimeError('generated-self-test-failed')",
            "    reset_state()",
            "    root = build_interface()",
            "    _running = True",
            "    root.after(TICK_MILLISECONDS, scheduled_tick)",
            "    root.mainloop()",
            "",
            "def main():",
            "    if '--self-test' in sys.argv:",
            "        report = self_test_application()",
            "        print(json.dumps(report, sort_keys=True))",
            "        return 0 if report['self_test']['passed'] == report['self_test']['total'] and report['closed'] else 1",
            "    launch()",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(main())",
            "",
        ]
    )
    return "\n".join(lines)


def render_tests(seed):
    cases = [
        {"id": case["id"], "input": case["input"], "expected": case["expected"]}
        for case in seed["acceptance"]
    ]
    controls = seed["presentation"]["controls"]
    lines = [
        '"""Generated bounded-simulation tests. Do not edit."""',
        "import ast",
        "import importlib.util",
        "import json",
        "from pathlib import Path",
        "",
        f"CASES = {cases!r}",
        f"EXPECTED_CALLBACKS = {[f'control_{index}' for index in range(len(controls))]!r}",
        "",
        "def verify_callbacks(path):",
        "    tree = ast.parse(path.read_text(encoding='utf-8'))",
        "    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}",
        "    interface = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'build_interface')",
        "    buttons = sorted((node for node in ast.walk(interface) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Button'), key=lambda node: node.lineno)",
        "    callbacks = [next(item.value for item in button.keywords if item.arg == 'command').id for button in buttons]",
        "    results = [actual == expected and actual in functions for actual, expected in zip(callbacks, EXPECTED_CALLBACKS)]",
        "    return {'passed': sum(results), 'total': len(EXPECTED_CALLBACKS), 'complete': len(callbacks) == len(EXPECTED_CALLBACKS) and all(results)}",
        "",
        "def run(*, emit=True):",
        "    path = Path(__file__).with_name('main.py')",
        "    specification = importlib.util.spec_from_file_location('generated_app', path)",
        "    module = importlib.util.module_from_spec(specification)",
        "    specification.loader.exec_module(module)",
        "    results = [module.run_case(case['input']) == case['expected'] for case in CASES]",
        "    things = [module.part({'value': case['input'], 'depths': (), 'axes': (), 'evidence': (), 'state': 'formed'}) for case in CASES]",
        "    thing_results = [thing['value'] == case['expected'] and thing['state'] == 'valid' and len(thing['depths']) == 10 and thing['evidence'] == ('boundary:inward', 'part:run_case', 'boundary:outward') for thing, case in zip(things, CASES)]",
        "    callbacks = verify_callbacks(path)",
        "    report = {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in CASES], 'things': {'passed': sum(thing_results), 'total': len(thing_results)}, 'editable': {'passed': 0, 'total': 0}, 'key_callbacks': {'passed': callbacks['passed'], 'total': callbacks['total']}}",
        "    if emit:",
        "        print(json.dumps(report, sort_keys=True))",
        "    return 0 if all((*results, *thing_results)) and callbacks['complete'] else 1",
        "",
        "if __name__ == '__main__':",
        "    raise SystemExit(run())",
        "",
    ]
    return "\n".join(lines).encode()


def compile_declaration(seed):
    if seed["program"]["language"] != LANGUAGE:
        raise ValueError("unsupported-simulation-language")
    return ast.parse(render_source(seed))
