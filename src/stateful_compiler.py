"""Compile a declarative stateful interface into one specialized Python AST."""

from __future__ import annotations

import ast
import re

from semantic_expression import function_source


LANGUAGE = "stateful-interface-declaration-1"


def safe_name(value):
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def value_source(
    node,
    *,
    arguments="arguments",
    record="record",
    calculations=None,
):
    if set(node) == {"literal"}:
        return repr(node["literal"])
    if set(node) == {"argument"}:
        return f"{arguments}[{node['argument']!r}]"
    if set(node) == {"state"}:
        return f"state[{node['state']!r}]"
    if set(node) == {"record"}:
        return repr(node["record"])
    if set(node) == {"matched_field"}:
        return f"{record}[{node['matched_field']!r}]"
    if set(node) == {"not"}:
        return (
            f"(not {value_source(node['not'], arguments=arguments, record=record, calculations=calculations)})"
        )
    if set(node) == {"add"}:
        left, right = node["add"]
        return (
            f"({value_source(left, arguments=arguments, record=record, calculations=calculations)} + "
            f"{value_source(right, arguments=arguments, record=record, calculations=calculations)})"
        )
    if set(node) == {"calculate"}:
        calculation = node["calculate"]
        definition = (
            (calculations or {}).get(calculation.get("call"))
            if isinstance(calculation, dict)
            else None
        )
        if (
            not isinstance(calculation, dict)
            or set(calculation) != {"call", "arguments"}
            or definition is None
            or not isinstance(calculation["arguments"], list)
        ):
            raise ValueError("unknown-stateful-calculation")
        if len(calculation["arguments"]) != definition["arity"]:
            raise ValueError("invalid-stateful-calculation-arity")
        values = ", ".join(
            value_source(
                value,
                arguments=arguments,
                record=record,
                calculations=calculations,
            )
            for value in calculation["arguments"]
        )
        return f"{definition['source']}({values})"
    if set(node) == {"object"}:
        return (
            "{"
            + ", ".join(
                f"{name!r}: {value_source(value, arguments=arguments, record=record, calculations=calculations)}"
                for name, value in node["object"].items()
            )
            + "}"
        )
    raise ValueError("unknown-stateful-value")


def guard_source(guard, calculations):
    operation = guard["op"]
    value = value_source(guard["value"], calculations=calculations)
    if operation == "non_empty":
        return f"(isinstance({value}, str) and bool({value}.strip()))"
    if operation == "integer_range":
        if set(guard) != {"op", "value", "minimum", "maximum", "error"}:
            raise ValueError("invalid-stateful-range")
        return (
            f"(isinstance({value}, int) and "
            f"{guard['minimum']!r} <= {value} <= {guard['maximum']!r})"
        )
    collection = f"state[{guard['collection']!r}]"
    field = guard["field"]
    comparison = f"record[{field!r}] == {value}"
    if operation == "exists":
        return f"any({comparison} for record in {collection})"
    if operation == "unique":
        return f"all(not ({comparison}) for record in {collection})"
    raise ValueError("unknown-stateful-guard")


def effect_lines(effect, calculations):
    operation = effect["op"]
    if operation == "append":
        return [
            f"    state[{effect['collection']!r}].append("
            f"{value_source(effect['value'], calculations=calculations)})"
        ]
    if operation == "increment":
        return [
            f"    state[{effect['field']!r}] += "
            f"{value_source(effect['amount'], calculations=calculations)}"
        ]
    if operation == "set":
        return [
            f"    state[{effect['field']!r}] = "
            f"{value_source(effect['value'], calculations=calculations)}"
        ]
    if operation == "remove":
        match = effect["match"]
        value = value_source(match["value"], calculations=calculations)
        return [
            f"    state[{effect['collection']!r}] = [",
            f"        record for record in state[{effect['collection']!r}]",
            f"        if record[{match['field']!r}] != {value}",
            "    ]",
        ]
    if operation == "update":
        match = effect["match"]
        value = value_source(match["value"], calculations=calculations)
        lines = [
            f"    for record in state[{effect['collection']!r}]:",
            f"        if record[{match['field']!r}] == {value}:",
        ]
        lines.extend(
            f"            record[{field!r}] = "
            f"{value_source(replacement, record='record', calculations=calculations)}"
            for field, replacement in effect["changes"].items()
        )
        return lines
    raise ValueError("unknown-stateful-effect")


def command_source(command, calculations):
    function = "command_" + safe_name(command["id"])
    lines = [f"def {function}(arguments):"]
    for argument in command["arguments"]:
        name = argument["name"]
        lines.extend(
            [
                f"    if {name!r} not in arguments:",
                f"        return _failure({('missing-' + name)!r})",
            ]
        )
        if argument["type"] == "integer":
            lines.extend(
                [
                    "    try:",
                    f"        arguments[{name!r}] = int(arguments[{name!r}])",
                    "    except (TypeError, ValueError):",
                    f"        return _failure({('invalid-' + name)!r})",
                ]
            )
        elif argument["type"] != "string":
            raise ValueError("unknown-stateful-argument-type")
    for guard in command.get("guards", ()):
        lines.extend(
            [
                f"    if not {guard_source(guard, calculations)}:",
                f"        return _failure({guard['error']!r})",
            ]
        )
    for effect in command.get("effects", ()):
        lines.extend(effect_lines(effect, calculations))
    if command.get("persist", True):
        lines.append("    persist_state()")
    lines.extend(
        [
            "    present_state()",
            "    return _success()",
            "",
        ]
    )
    return lines


def argument_source(argument):
    source = argument["source"]
    if source == "input":
        return f"_inputs[{argument['identity']!r}].get()"
    if source == "selection":
        return (
            f"selected_value({argument['identity']!r}, "
            f"{argument['field']!r})"
        )
    if source == "literal":
        return repr(argument["value"])
    raise ValueError("unknown-control-argument-source")


def control_source(control, index):
    callback = f"control_{index}"
    arguments = ", ".join(
        f"{name!r}: {argument_source(argument)}"
        for name, argument in control.get("arguments", {}).items()
    )
    route = "command_" + safe_name(control["command"])
    return [
        f"def {callback}():",
        "    global _last_outcome",
        f"    _last_outcome = {route}({{{arguments}}})",
        "    _status.set(_last_outcome['error'] or 'ok')",
        "    return _last_outcome",
        "",
    ]


def render_source(seed):
    presentation = seed["presentation"]
    collection = presentation["collection"]
    persistence = seed["persistence"]
    initial = seed["state"]["initial"]
    controls = presentation["controls"]
    filters = collection.get("filters", {})
    calculation_definitions = (
        seed["semantics"].get("calculations", {}).get("functions", ())
    )
    calculation_lines, calculation_names = function_source(
        calculation_definitions,
        prefix="_calculation",
    )
    calculations = {
        identity: {
            "source": source,
            "arity": len(definition["parameters"]),
        }
        for definition, (identity, source) in zip(
            calculation_definitions,
            calculation_names,
        )
    }
    lines = [
        '"""Generated stateful application. Do not edit."""',
        "from copy import deepcopy",
        "import json",
        "import os",
        "from pathlib import Path",
        "import sys",
        "import tempfile",
        "from tkinter import Button, Entry, Label, Listbox, StringVar, Tk",
        "",
        f"APPLICATION_ID = {seed['identity']['canonical']!r}",
        f"INITIAL_STATE = {initial!r}",
        f"COLLECTION_FIELD = {collection['state_field']!r}",
        f"IDENTITY_FIELD = {collection['identity_field']!r}",
        f"DISPLAY_FIELDS = {collection['display_fields']!r}",
        f"FILTER_FIELD = {collection.get('filter_field')!r}",
        f"FILTERS = {filters!r}",
        f"DEFAULT_STATE_PATH = {persistence['default_path']!r}",
        f"STATE_ENVIRONMENT = {persistence['environment']!r}",
        "state = deepcopy(INITIAL_STATE)",
        "_state_path = None",
        "_root = None",
        "_inputs = {}",
        "_collections = {}",
        "_buttons = {}",
        "_status = None",
        "_last_outcome = None",
        "",
        "def state_path():",
        "    selected = os.environ.get(STATE_ENVIRONMENT)",
        "    return Path(selected) if selected else Path.home() / DEFAULT_STATE_PATH",
        "",
        "def configure_state_path(path):",
        "    global _state_path",
        "    _state_path = Path(path)",
        "",
        "def active_state_path():",
        "    return _state_path or state_path()",
        "",
        "def snapshot():",
        "    return deepcopy(state)",
        "",
        "def reset_state():",
        "    state.clear()",
        "    state.update(deepcopy(INITIAL_STATE))",
        "    present_state()",
        "",
        "def persist_state():",
        "    destination = active_state_path()",
        "    destination.parent.mkdir(parents=True, exist_ok=True)",
        "    descriptor, temporary = tempfile.mkstemp(prefix='.' + destination.name + '-', dir=destination.parent)",
        "    try:",
        "        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:",
        "            json.dump(state, stream, ensure_ascii=False, sort_keys=True, separators=(',', ':'))",
        "            stream.write('\\n')",
        "        os.replace(temporary, destination)",
        "    except BaseException:",
        "        Path(temporary).unlink(missing_ok=True)",
        "        raise",
        "",
        "def load_state():",
        "    destination = active_state_path()",
        "    loaded = json.loads(destination.read_text(encoding='utf-8')) if destination.exists() else deepcopy(INITIAL_STATE)",
        "    state.clear()",
        "    state.update(loaded)",
        "    present_state()",
        "    return snapshot()",
        "",
        "def _success():",
        "    return {'result': snapshot(), 'error': None}",
        "",
        "def _failure(identity):",
        "    return {'result': None, 'error': identity}",
        "",
        *calculation_lines,
    ]
    for command in seed["semantics"]["commands"]:
        lines.extend(command_source(command, calculations))
    lines.extend(
        [
            "COMMANDS = {",
            *(
                f"    {command['id']!r}: command_{safe_name(command['id'])},"
                for command in seed["semantics"]["commands"]
            ),
            "}",
            "",
            "def run_command(identity, arguments):",
            "    operation = COMMANDS.get(identity)",
            "    return operation(dict(arguments)) if operation else _failure('unknown-command')",
            "",
            "def visible_records():",
            "    records = state[COLLECTION_FIELD]",
            "    selected = state.get(FILTER_FIELD) if FILTER_FIELD else None",
            "    rule = FILTERS.get(selected)",
            "    if not rule:",
            "        return list(records)",
            "    return [record for record in records if record[rule['field']] == rule['equals']]",
            "",
            "def display_record(record):",
            "    return ' · '.join(f'{field}={record[field]}' for field in DISPLAY_FIELDS)",
            "",
            "def present_state():",
            "    for identity, widget in _collections.items():",
            "        widget.delete(0, 'end')",
            "        for record in visible_records():",
            "            widget.insert('end', display_record(record))",
            "",
            "def selected_value(identity, field):",
            "    widget = _collections[identity]",
            "    selected = widget.curselection()",
            "    if not selected:",
            "        return None",
            "    return visible_records()[selected[0]][field]",
            "",
        ]
    )
    for index, control in enumerate(controls):
        lines.extend(control_source(control, index))
    lines.extend(
        [
            "def build_interface():",
            "    global _root, _status",
            "    _root = Tk()",
            f"    _root.title({presentation['title']!r})",
            f"    _root.geometry({presentation['geometry']!r})",
        ]
    )
    for widget in presentation["inputs"]:
        identity = widget["identity"]
        lines.extend(
            [
                f"    Label(_root, text={widget['label']!r}).grid(row={widget['row']!r}, column={widget['column']!r}, sticky='w')",
                f"    _inputs[{identity!r}] = Entry(_root, width={widget.get('width', 32)!r})",
                f"    _inputs[{identity!r}].grid(row={widget['row']!r}, column={widget['column'] + 1!r}, columnspan={widget.get('columnspan', 3)!r}, sticky='ew')",
            ]
        )
    lines.extend(
        [
            f"    _collections[{collection['identity']!r}] = Listbox(_root, width={collection.get('width', 52)!r}, height={collection.get('height', 12)!r})",
            f"    _collections[{collection['identity']!r}].grid(row={collection['row']!r}, column={collection['column']!r}, columnspan={collection.get('columnspan', 4)!r}, sticky='nsew')",
        ]
    )
    for index, control in enumerate(controls):
        lines.extend(
            [
                f"    _buttons[{control['id']!r}] = Button(_root, text={control['label']!r}, command=control_{index})",
                f"    _buttons[{control['id']!r}].grid(row={control['row']!r}, column={control['column']!r}, sticky='nsew')",
            ]
        )
    lines.extend(
        [
            "    _status = StringVar(value='ready')",
            f"    Label(_root, textvariable=_status).grid(row={presentation['status']['row']!r}, column={presentation['status']['column']!r}, columnspan={presentation['status'].get('columnspan', 4)!r}, sticky='w')",
            "    present_state()",
            "    return _root",
            "",
            "def run_case(case):",
            "    results = []",
            "    with tempfile.TemporaryDirectory(prefix='generated-stateful-case-') as directory:",
            "        configure_state_path(Path(directory) / 'state.json')",
            "        reset_state()",
            "        for step in case['steps']:",
            "            if step.get('restart'):",
            "                state.clear()",
            "                results.append({'result': load_state(), 'error': None})",
            "            else:",
            "                results.append(run_command(step['command'], step.get('arguments', {})))",
            "        return {'results': results, 'state': snapshot()}",
            "",
            "def run_acceptance():",
            f"    cases = {seed['acceptance']!r}",
            "    results = [run_case(case['input']) == case['expected'] for case in cases]",
            "    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}",
            "",
            "def self_test_interface():",
            "    checks = []",
            "    closed = False",
            "    with tempfile.TemporaryDirectory(prefix='generated-stateful-gui-') as directory:",
            "        configure_state_path(Path(directory) / 'state.json')",
            "        root = build_interface()",
            "        root.withdraw()",
            f"        cases = {presentation['self_tests']!r}",
            "        for case in cases:",
            "            reset_state()",
            "            for setup in case.get('setup', ()):",
            "                run_command(setup['command'], setup.get('arguments', {}))",
            "            for identity, value in case.get('inputs', {}).items():",
            "                _inputs[identity].delete(0, 'end')",
            "                _inputs[identity].insert(0, value)",
            "            present_state()",
            "            if 'selection' in case:",
            "                widget = _collections[case['selection']['identity']]",
            "                widget.selection_clear(0, 'end')",
            "                widget.selection_set(case['selection']['index'])",
            "            _buttons[case['control']].invoke()",
            "            checks.append(_last_outcome == case['expected']['outcome'] and snapshot() == case['expected']['state'])",
            "        root.destroy()",
            "        closed = True",
            "    return {'self_test': {'passed': sum(checks), 'total': len(checks)}, 'closed': closed}",
            "",
            "def launch():",
            "    proof = self_test_interface()",
            "    if proof['self_test']['passed'] != proof['self_test']['total']:",
            "        raise RuntimeError('generated-self-test-failed')",
            "    configure_state_path(state_path())",
            "    load_state()",
            "    root = build_interface()",
            "    root.mainloop()",
            "",
            "def main():",
            "    if '--self-test' in sys.argv:",
            "        report = self_test_interface()",
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


def compile_declaration(seed):
    if seed["program"]["language"] != LANGUAGE:
        raise ValueError("unsupported-stateful-language")
    return ast.parse(render_source(seed))
