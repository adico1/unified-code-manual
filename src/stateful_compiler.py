"""Compile a declarative stateful interface into one specialized Python AST."""

from __future__ import annotations

import ast
import re

from semantic_expression import function_source


LANGUAGE = "stateful-interface-declaration-1"


def verify_record_contract(seed):
    contract = seed["semantics"].get("record_contract")
    if contract is None:
        return
    if set(contract) != {
        "collection",
        "derived_fields",
        "required_fields",
        "watchers",
        "signs",
    }:
        raise ValueError("invalid-record-contract")
    required = contract["required_fields"]
    watchers = contract["watchers"]
    signs = contract["signs"]
    if (
        not required
        or len(required) != len(set(required))
        or len(watchers) != len(set(watchers))
        or len(signs) != len(set(signs))
        or not set((*watchers, *signs)) <= set(required)
        or contract["collection"]
        != seed["presentation"]["collection"]["state_field"]
    ):
        raise ValueError("invalid-record-contract")
    records = seed["state"]["initial"].get(contract["collection"])
    if not isinstance(records, list) or any(
        set(record) != set(required) for record in records
    ):
        raise ValueError("record-contract-field-missing")
    append_records = [
        effect.get("value", {}).get("object")
        for command in seed["semantics"]["commands"]
        for effect in command.get("effects", ())
        if effect.get("op") == "append"
        and effect.get("collection") == contract["collection"]
    ]
    if not append_records or any(
        not isinstance(record, dict) or set(record) != set(required)
        for record in append_records
    ):
        raise ValueError("record-contract-append-missing")


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
    if set(node) == {"derived_percentage"}:
        payload = node["derived_percentage"]
        if set(payload) != {"numerator", "denominator", "scale"}:
            raise ValueError("invalid-stateful-derived-percentage")
        numerator = value_source(
            payload["numerator"],
            arguments=arguments,
            record=record,
            calculations=calculations,
        )
        denominator = value_source(
            payload["denominator"],
            arguments=arguments,
            record=record,
            calculations=calculations,
        )
        return f"(({numerator} * {payload['scale']!r}) // {denominator})"
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
    if operation == "record_field_equals":
        match = guard["match"]
        match_value = value_source(match["value"], calculations=calculations)
        expected = value_source(guard["value"], calculations=calculations)
        return (
            f"any(record[{match['field']!r}] == {match_value} and "
            f"record[{guard['field']!r}] == {expected} for record in "
            f"state[{guard['collection']!r}])"
        )
    value = value_source(guard["value"], calculations=calculations)
    if operation == "non_empty":
        return f"(isinstance({value}, str) and bool({value}.strip()))"
    if operation == "https_url":
        return f"(isinstance({value}, str) and {value}.startswith('https://'))"
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
    if operation == "open_url":
        return [
            "    _open_url("
            + value_source(effect["value"], calculations=calculations)
            + ")"
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
    lines = [
        f"def {callback}():",
        "    global _last_outcome",
    ]
    confirmation = control.get("confirmation")
    if confirmation is not None:
        lines.extend(
            [
                f"    if not _confirm({confirmation['title']!r}, {confirmation['message']!r}):",
                "        _last_outcome = _failure('confirmation-declined')",
                "        _status.set(_last_outcome['error'])",
                "        return _last_outcome",
            ]
        )
    lines.extend([
        f"    _last_outcome = {route}({{{arguments}}})",
        "    _status.set(_last_outcome['error'] or 'ok')",
        "    return _last_outcome",
        "",
    ])
    return lines


def render_source(seed):
    verify_record_contract(seed)
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
    outward_urls = any(
        effect.get("op") == "open_url"
        for command in seed["semantics"]["commands"]
        for effect in command.get("effects", ())
    )
    confirmations = any(control.get("confirmation") for control in controls)
    if any(
        set(control["confirmation"]) != {"message", "title"}
        for control in controls
        if control.get("confirmation") is not None
    ):
        raise ValueError("invalid-control-confirmation")
    projections = set(seed["program"].get("projections", ("API", "APP")))
    if not projections <= {"API", "APP", "CLI"}:
        raise ValueError("unknown-stateful-projection")
    rendering = presentation.get("rendering", {})
    table = collection.get("table")
    if table is not None:
        if set(table) != {"columns", "detail_fields", "heading", "metrics", "portfolio"}:
            raise ValueError("invalid-stateful-table")
        portfolio = table["portfolio"]
        if (
            not table["columns"]
            or not table["detail_fields"]
            or not table["metrics"]
            or any(set(column) != {"field", "label", "width"} for column in table["columns"])
            or any(set(field) != {"field", "label"} for field in table["detail_fields"])
            or any(set(metric) != {"label", "value"} for metric in table["metrics"])
            or set(portfolio) != {"columns", "records", "tab_labels"}
            or not portfolio["columns"]
            or not portfolio["records"]
            or any(set(column) != {"field", "label", "width"} for column in portfolio["columns"])
            or any(set(record) != {column["field"] for column in portfolio["columns"]} for record in portfolio["records"])
            or set(portfolio["tab_labels"]) != {"overview", "portfolio"}
            or any(column["field"] not in collection["display_fields"] for column in table["columns"])
            or any(field["field"] not in collection["display_fields"] for field in table["detail_fields"])
        ):
            raise ValueError("invalid-stateful-table")
    for interface_case in presentation["self_tests"]:
        assertions = interface_case.get("assertions")
        if assertions is not None and set(assertions) != {
            "collection_count",
            "error",
            "outward",
            "record",
            "state_fields",
            "visible_count",
        }:
            raise ValueError("invalid-interface-assertions")
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
        *(("import webbrowser",) if outward_urls else ()),
        "from tkinter import Button, Entry, Frame, Label, Listbox, StringVar, Text, Tk",
        *(("from tkinter.messagebox import askyesno",) if confirmations else ()),
        *(("from tkinter.ttk import Notebook, Scrollbar, Treeview",) if table else ()),
        "",
        f"APPLICATION_ID = {seed['identity']['canonical']!r}",
        "THING_STATES = ('unknown', 'absent', 'false', 'formed', 'valid', 'invalid')",
        "TEN_DEPTHS = ('01_identity', '02_authority', '03_declaration', '04_composition', '05_processing', '06_state', '07_boundary', '08_manifestation', '09_evidence', '10_fixed_point')",
        f"INITIAL_STATE = {initial!r}",
        f"COLLECTION_FIELD = {collection['state_field']!r}",
        f"IDENTITY_FIELD = {collection['identity_field']!r}",
        f"DISPLAY_FIELDS = {collection['display_fields']!r}",
        *((f"TABLE_COLUMNS = {table['columns']!r}",) if table else ()),
        *((f"DETAIL_FIELDS = {table['detail_fields']!r}",) if table else ()),
        *((f"DASHBOARD_METRICS = {table['metrics']!r}",) if table else ()),
        *((f"PORTFOLIO_COLUMNS = {table['portfolio']['columns']!r}",) if table else ()),
        *((f"PORTFOLIO_RECORDS = {table['portfolio']['records']!r}",) if table else ()),
        f"FILTER_FIELD = {collection.get('filter_field')!r}",
        f"FILTERS = {filters!r}",
        f"VISIBILITY = {collection.get('visibility')!r}",
        f"DEFAULT_STATE_PATH = {persistence['default_path']!r}",
        f"STATE_ENVIRONMENT = {persistence['environment']!r}",
        "state = deepcopy(INITIAL_STATE)",
        "_state_path = None",
        "_root = None",
        "_inputs = {}",
        "_collections = {}",
        "_details = {}",
        "_record_by_row = {}",
        "_buttons = {}",
        "_metric_cards = {}",
        "_portfolio = None",
        "_tabs = None",
        "_summary = None",
        "_status = None",
        "_last_outcome = None",
        *(("_open_url = webbrowser.open",) if outward_urls else ()),
        *(("_confirm = askyesno",) if confirmations else ()),
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
            "    records = list(state[COLLECTION_FIELD])",
            "    if VISIBILITY:",
            "        records = [record for record in records if record.get(VISIBILITY['field'], VISIBILITY['equals']) == VISIBILITY['equals']]",
            "    selected = state.get(FILTER_FIELD) if FILTER_FIELD else None",
            "    rule = FILTERS.get(selected)",
            "    if not rule:",
            "        return list(records)",
            "    return [record for record in records if record[rule['field']] == rule['equals']]",
            "",
            "def display_record(record):",
            "    return ' · '.join(f'{field}={record[field]}' for field in DISPLAY_FIELDS)",
            "",
            *(
                (
                    "def selected_record(identity):",
                    "    selected = _collections[identity].selection()",
                    "    return _record_by_row.get(selected[0]) if selected else None",
                    "",
                    "def present_detail(identity):",
                    "    detail = _details[identity]",
                    "    record = selected_record(identity)",
                    "    detail.delete('1.0', 'end')",
                    "    detail.insert('1.0', '\\n\\n'.join(f'{item[\"label\"]}\\n{record[item[\"field\"]]}' for item in DETAIL_FIELDS) if record else 'Select an observation')",
                    "",
                    "def present_state():",
                    "    records = visible_records()",
                    "    _record_by_row.clear()",
                    "    for identity, widget in _collections.items():",
                    "        widget.delete(*widget.get_children())",
                    "        for record in records:",
                    "            row = str(record[IDENTITY_FIELD])",
                    "            _record_by_row[row] = record",
                    "            widget.insert('', 'end', iid=row, values=tuple(record[column['field']] for column in TABLE_COLUMNS))",
                    "        if records:",
                    "            widget.selection_set(str(records[0][IDENTITY_FIELD]))",
                    "        present_detail(identity)",
                    "    if _summary is not None:",
                    "        _summary.set(f'{len(records)} shown / {len(state[COLLECTION_FIELD])} total · filter={state.get(FILTER_FIELD, \"all\")}')",
                    "",
                    "def selected_value(identity, field):",
                    "    record = selected_record(identity)",
                    "    return record[field] if record else None",
                    "",
                )
                if table
                else (
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
                )
            ),
        ]
    )
    for index, control in enumerate(controls):
        lines.extend(control_source(control, index))
    lines.extend(
        [
            "def build_interface():",
            "    global _root, _status, _summary, _portfolio, _tabs",
            "    _inputs.clear()",
            "    _collections.clear()",
            "    _details.clear()",
            "    _buttons.clear()",
            "    _metric_cards.clear()",
            "    _root = Tk()",
            f"    _root.title({presentation['title']!r})",
            f"    _root.geometry({presentation['geometry']!r})",
            *(
                f"    _root.columnconfigure({column!r}, weight=1)"
                for column in rendering.get("responsive_columns", ())
            ),
            *(
                f"    _root.rowconfigure({row!r}, weight=1)"
                for row in rendering.get("responsive_rows", ())
            ),
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
    if table:
        lines.extend(
            [
                "    surface = Frame(_root, padx=12, pady=10)",
                f"    surface.grid(row={collection['row']!r}, column={collection['column']!r}, columnspan={collection.get('columnspan', 4)!r}, sticky='nsew')",
                "    surface.columnconfigure(0, weight=3)",
                "    surface.columnconfigure(2, weight=2)",
                "    surface.rowconfigure(3, weight=1)",
                f"    Label(surface, text={table['heading']!r}, font=('Helvetica', 18, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 4))",
                "    _summary = StringVar(value='')",
                "    Label(surface, textvariable=_summary, foreground='#4a5568').grid(row=1, column=0, columnspan=3, sticky='w', pady=(0, 8))",
                "    metrics = Frame(surface)",
                "    metrics.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(0, 10))",
                "    for index, metric in enumerate(DASHBOARD_METRICS):",
                "        metrics.columnconfigure(index, weight=1)",
                "        card = Frame(metrics, highlightbackground='#cbd5e0', highlightthickness=1, padx=12, pady=8)",
                "        card.grid(row=0, column=index, sticky='nsew', padx=(0, 8))",
                "        _metric_cards[metric['label']] = card",
                "        Label(card, text=metric['value'], font=('Helvetica', 18, 'bold')).pack(anchor='w')",
                "        Label(card, text=metric['label'], foreground='#4a5568').pack(anchor='w')",
                "    _tabs = Notebook(surface)",
                "    _tabs.grid(row=3, column=0, columnspan=3, sticky='nsew')",
                "    overview_surface = Frame(_tabs)",
                "    overview_surface.columnconfigure(0, weight=3)",
                "    overview_surface.columnconfigure(2, weight=2)",
                "    overview_surface.rowconfigure(0, weight=1)",
                "    portfolio_surface = Frame(_tabs)",
                "    portfolio_surface.columnconfigure(0, weight=1)",
                "    portfolio_surface.rowconfigure(0, weight=1)",
                f"    _tabs.add(overview_surface, text={table['portfolio']['tab_labels']['overview']!r})",
                f"    _tabs.add(portfolio_surface, text={table['portfolio']['tab_labels']['portfolio']!r})",
                f"    _collections[{collection['identity']!r}] = Treeview(overview_surface, columns=tuple(column['field'] for column in TABLE_COLUMNS), show='headings', selectmode='browse')",
                f"    table_widget = _collections[{collection['identity']!r}]",
                "    for column in TABLE_COLUMNS:",
                "        table_widget.heading(column['field'], text=column['label'])",
                "        table_widget.column(column['field'], width=column['width'], minwidth=70, stretch=True)",
                "    table_widget.grid(row=0, column=0, sticky='nsew')",
                "    table_scroll = Scrollbar(overview_surface, orient='vertical', command=table_widget.yview)",
                "    table_scroll.grid(row=0, column=1, sticky='ns')",
                "    table_widget.configure(yscrollcommand=table_scroll.set)",
                f"    _details[{collection['identity']!r}] = Text(overview_surface, width=46, wrap='word', padx=12, pady=10)",
                f"    _details[{collection['identity']!r}].grid(row=0, column=2, sticky='nsew', padx=(12, 0))",
                f"    _details[{collection['identity']!r}].bind('<Key>', lambda _event: 'break')",
                f"    table_widget.bind('<<TreeviewSelect>>', lambda _event: present_detail({collection['identity']!r}))",
                "    _portfolio = Treeview(portfolio_surface, columns=tuple(column['field'] for column in PORTFOLIO_COLUMNS), show='headings')",
                "    for column in PORTFOLIO_COLUMNS:",
                "        _portfolio.heading(column['field'], text=column['label'])",
                "        _portfolio.column(column['field'], width=column['width'], minwidth=80, stretch=True)",
                "    for index, record in enumerate(PORTFOLIO_RECORDS):",
                "        _portfolio.insert('', 'end', iid=str(index), values=tuple(record[column['field']] for column in PORTFOLIO_COLUMNS))",
                "    _portfolio.grid(row=0, column=0, sticky='nsew')",
                "    portfolio_scroll = Scrollbar(portfolio_surface, orient='vertical', command=_portfolio.yview)",
                "    portfolio_scroll.grid(row=0, column=1, sticky='ns')",
                "    _portfolio.configure(yscrollcommand=portfolio_scroll.set)",
            ]
        )
    else:
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
            "def part(thing):",
            "    result = run_case(thing['value'])",
            "    return {'value': result, 'depths': TEN_DEPTHS, 'axes': tuple(thing.get('axes', ())), 'evidence': tuple(thing.get('evidence', ())) + ('boundary:inward', 'part:run_case', 'boundary:outward'), 'state': 'valid'}",
            "",
            "def run_acceptance():",
            f"    cases = {seed['acceptance']!r}",
            "    results = [run_case(case['input']) == case['expected'] for case in cases]",
            "    return {'passed': sum(results), 'total': len(results), 'cases': [case['id'] for case in cases]}",
            "",
            "def verify_interface_assertions(assertions, outward):",
            "    checks = [",
            "        _last_outcome['error'] == assertions['error'],",
            "        len(state[COLLECTION_FIELD]) == assertions['collection_count'],",
            "        len(visible_records()) == assertions['visible_count'],",
            "        all(state.get(field) == value for field, value in assertions['state_fields'].items()),",
            "        outward == assertions['outward'],",
            "    ]",
            "    rule = assertions['record']",
            "    if rule is not None:",
            "        matches = [record for record in state[COLLECTION_FIELD] if record.get(rule['match']['field']) == rule['match']['equals']]",
            "        checks.append(bool(matches) == rule['present'])",
            "        if rule['present'] and matches:",
            "            checks.append(all(matches[0].get(field) == value for field, value in rule['fields'].items()))",
            "    return all(checks)",
            "",
            "def self_test_interface():",
            "    global "
            + ", ".join(
                identity
                for enabled, identity in (
                    (True, "_state_path"),
                    (outward_urls, "_open_url"),
                    (confirmations, "_confirm"),
                )
                if enabled
            ),
            "    checks = []",
            "    closed = False",
            "    outward = []",
            "    previous_state_path = _state_path",
            *(("    previous_open_url = _open_url", "    _open_url = outward.append") if outward_urls else ()),
            *(("    previous_confirm = _confirm",) if confirmations else ()),
            "    with tempfile.TemporaryDirectory(prefix='generated-stateful-gui-') as directory:",
            "        configure_state_path(Path(directory) / 'state.json')",
            "        root = build_interface()",
            "        root.withdraw()",
            *(
                (
                    f"        table_widget = _collections[{collection['identity']!r}]",
                    "        checks.append(tuple(table_widget['columns']) == tuple(column['field'] for column in TABLE_COLUMNS))",
                    "        checks.append(all(table_widget.heading(column['field'], 'text') == column['label'] for column in TABLE_COLUMNS))",
                    "        checks.append(tuple(_metric_cards) == tuple(metric['label'] for metric in DASHBOARD_METRICS))",
                    "        checks.append(len(_portfolio.get_children()) == len(PORTFOLIO_RECORDS))",
                    "        _tabs.select(1)",
                    "        checks.append(_tabs.index(_tabs.select()) == 1)",
                    "        _tabs.select(0)",
                    f"        checks.append(bool(table_widget.get_children()) and bool(_details[{collection['identity']!r}].get('1.0', 'end').strip()))",
                )
                if table
                else ()
            ),
            f"        cases = {presentation['self_tests']!r}",
            "        for case in cases:",
            "            outward.clear()",
            *(("            _confirm = lambda _title, _message: case.get('confirmation', True)",) if confirmations else ()),
            "            reset_state()",
            "            for setup in case.get('setup', ()):",
            "                run_command(setup['command'], setup.get('arguments', {}))",
            "            for identity, value in case.get('inputs', {}).items():",
            "                _inputs[identity].delete(0, 'end')",
            "                _inputs[identity].insert(0, value)",
            "            present_state()",
            "            if 'selection' in case:",
            "                widget = _collections[case['selection']['identity']]",
            *(
                (
                    "                widget.selection_remove(*widget.selection())",
                    "                widget.selection_set(widget.get_children()[case['selection']['index']])",
                )
                if table
                else (
                    "                widget.selection_clear(0, 'end')",
                    "                widget.selection_set(case['selection']['index'])",
                )
            ),
            "            _buttons[case['control']].invoke()",
            "            if case.get('restart'):",
            "                state.clear()",
            "                load_state()",
            "            checks.append(verify_interface_assertions(case['assertions'], outward) if 'assertions' in case else _last_outcome == case['expected']['outcome'] and snapshot() == case['expected']['state'])",
            "        root.destroy()",
            *(("        _open_url = previous_open_url",) if outward_urls else ()),
            *(("        _confirm = previous_confirm",) if confirmations else ()),
            "        _state_path = previous_state_path",
            "        closed = True",
            "    return {'self_test': {'passed': sum(checks), 'total': len(checks)}, 'interactions': [case.get('id', case['control']) for case in cases], 'closed': closed}",
            "",
            "def launch():",
            "    proof = self_test_interface()",
            "    if proof['self_test']['passed'] != proof['self_test']['total']:",
            "        raise RuntimeError('generated-self-test-failed')",
            "    configure_state_path(state_path())",
            "    root = build_interface()",
            "    load_state()",
            "    root.mainloop()",
            "",
            "def main():",
            *(
                (
                    "    if '--case-json' in sys.argv:",
                    "        position = sys.argv.index('--case-json')",
                    "        print(json.dumps(run_case(json.loads(sys.argv[position + 1])), sort_keys=True))",
                    "        return 0",
                )
                if "CLI" in projections
                else ()
            ),
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
