"""Compile calculator declarations into a specialized Python syntax tree."""

from __future__ import annotations

import ast
import re

from stateful_compiler import LANGUAGE as STATEFUL_LANGUAGE
from stateful_compiler import compile_declaration as compile_stateful_declaration
from stateful_compiler import render_source as render_stateful_source


LANGUAGE = "calculator-declaration-1"
LANGUAGES = (LANGUAGE, STATEFUL_LANGUAGE)
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
QUALIFIED = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def checked_name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("invalid-declaration-name")
    return value


def checked_qualified(value):
    if not isinstance(value, str) or not QUALIFIED.fullmatch(value):
        raise ValueError("invalid-declaration-target")
    return value


def expression(value):
    if not isinstance(value, dict):
        raise ValueError("invalid-semantic-expression")
    if set(value) == {"call", "arguments"}:
        target = checked_qualified(value["call"])
        arguments = ", ".join(expression(item) for item in value["arguments"])
        return f"{target}({arguments})"
    if len(value) != 1:
        raise ValueError("invalid-semantic-expression")
    operation, payload = next(iter(value.items()))
    if operation == "literal":
        return repr(payload)
    if operation == "parameter":
        return checked_name(payload)
    if operation == "variadic":
        return checked_name(payload)
    if operation == "spread":
        return "*" + checked_name(payload)
    if operation == "list":
        return f"list({expression(payload)})"
    if operation == "negate":
        return f"-({expression(payload)})"
    binary = {
        "add": "+",
        "subtract": "-",
        "multiply": "*",
        "divide": "/",
        "power": "**",
        "equal": "==",
    }
    if operation in binary:
        if not isinstance(payload, list) or len(payload) != 2:
            raise ValueError("invalid-semantic-arity")
        return (
            f"({expression(payload[0])} {binary[operation]} "
            f"{expression(payload[1])})"
        )
    if operation == "call":
        target = checked_qualified(payload)
        return target
    if operation == "arguments":
        raise ValueError("orphan-semantic-arguments")
    if operation == "choose":
        if set(payload) != {"when", "then", "otherwise"}:
            raise ValueError("invalid-semantic-choice")
        return (
            f"({expression(payload['then'])} if "
            f"{expression(payload['when'])} else "
            f"{expression(payload['otherwise'])})"
        )
    if "call" in value and "arguments" in value:
        raise ValueError("invalid-semantic-call")
    raise ValueError("unknown-semantic-expression")


def semantic_body(value):
    return expression(value)


def required_imports(seed):
    targets = [
        item.get("target", "")
        for group in seed["semantics"]["operations"].values()
        for item in group
    ]
    def calls(value):
        if isinstance(value, list):
            return {
                item
                for child in value
                for item in calls(child)
            }
        if not isinstance(value, dict):
            return set()
        direct = {value["call"]} if isinstance(value.get("call"), str) else set()
        return direct | {
            item
            for child in value.values()
            for item in calls(child)
        }

    targets.extend(
        calls(item.get("body"))
        for item in seed["semantics"]["operations"].get("functions", ())
    )
    flattened = [
        item
        for target in targets
        for item in (target if isinstance(target, set) else (target,))
    ]
    roots = {
        target.split(".", 1)[0]
        for target in flattened
        if "." in target
    }
    return sorted(roots - {"ast", "operator"})


def operation_map(items):
    return ", ".join(
        f"{checked_qualified(item['syntax'])}: "
        f"{checked_qualified(item['target'])}"
        for item in items
    )


def function_source(items):
    lines = []
    names = []
    for index, item in enumerate(items):
        internal = f"_semantic_{index}"
        parameters = item.get("parameters")
        if parameters is None:
            parameters = ["*" + checked_name(item["variadic"])]
        else:
            parameters = [checked_name(value) for value in parameters]
        lines.extend(
            [
                f"def {internal}({', '.join(parameters)}):",
                f"    return {semantic_body(item['body'])}",
                "",
            ]
        )
        names.append((item["id"], internal))
    return lines, names


def action_routes(seed):
    transitions = {
        item["event"]: item["route"]
        for item in seed["transitions"]
    }
    result = {}
    for control in seed["presentation"]["controls"]:
        event = f"control.{control['id']}.pressed"
        action = control["action"]
        route = checked_name(transitions[event])
        if action in result and result[action] != route:
            raise ValueError("action-route-conflict")
        result[action] = route
    return result, transitions


def expression_runtime(seed):
    laws = seed["semantics"]["numeric_laws"]
    operations = seed["semantics"]["operations"]
    functions = operations.get("functions", [])
    function_lines, function_names = function_source(functions)
    constants = ", ".join(
        f"{item['id']!r}: {checked_qualified(item['target'])}"
        for item in operations.get("constants", [])
    )
    variables = tuple(laws.get("variables", ()))
    lines = [
        *function_lines,
        f"BINARY = {{{operation_map(operations.get('binary', []))}}}",
        f"UNARY = {{{operation_map(operations.get('unary', []))}}}",
    ]
    if function_names:
        lines.append(
            "FUNCTIONS = {"
            + ", ".join(f"{name!r}: {internal}" for name, internal in function_names)
            + "}"
        )
    if constants:
        lines.append(f"CONSTANTS = {{{constants}}}")
    lines.extend(
        [
            "",
            "def evaluate_node(node, variables):",
            "    if isinstance(node, ast.Expression):",
            "        return evaluate_node(node.body, variables)",
            "    if isinstance(node, ast.Constant) and type(node.value) in (int, float):",
            "        return node.value",
        ]
    )
    if variables:
        lines.extend(
            [
                "    if isinstance(node, ast.Name) and node.id in variables:",
                "        return variables[node.id]",
            ]
        )
    if constants:
        lines.extend(
            [
                "    if isinstance(node, ast.Name) and node.id in CONSTANTS:",
                "        return CONSTANTS[node.id]",
            ]
        )
    lines.extend(
        [
            "    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:",
            "        return BINARY[type(node.op)](evaluate_node(node.left, variables), evaluate_node(node.right, variables))",
            "    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:",
            "        return UNARY[type(node.op)](evaluate_node(node.operand, variables))",
        ]
    )
    if function_names:
        lines.extend(
            [
                "    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:",
                "        return FUNCTIONS[node.func.id](*(evaluate_node(item, variables) for item in node.args))",
            ]
        )
    lines.extend(
        [
            "    raise ValueError('invalid-expression')",
            "",
            "def evaluate_expression(expression, variables=None):",
            f"    if not expression or len(expression) > {laws['maximum_characters']!r}:",
            "        raise ValueError('invalid-expression')",
            "    value = evaluate_node(ast.parse(expression, mode='eval'), variables or {})",
        ]
    )
    if laws["numeric_domain"] == "integer":
        lines.extend(
            [
                "    if type(value) is not int:",
                "        raise ValueError('integer-required')",
            ]
        )
    lines.extend(["    return value", ""])
    return lines


def stack_runtime(seed):
    operations = seed["semantics"]["operations"]["binary"]
    mapping = ", ".join(
        f"{item['token']!r}: {checked_qualified(item['target'])}"
        for item in operations
    )
    return [
        f"OPERATIONS = {{{mapping}}}",
        "",
        "def calculate_case(case):",
        "    stack = []",
        "    for token in case['tokens']:",
        "        if token in OPERATIONS:",
        "            right = stack.pop()",
        "            left = stack.pop()",
        "            stack.append(OPERATIONS[token](left, right))",
        "        else:",
        "            stack.append(float(token) if '.' in token else int(token))",
        "    if len(stack) != 1:",
        "        raise ValueError('invalid-stack')",
        "    return stack[0]",
        "",
    ]


def presenter(seed):
    laws = seed["semantics"]["numeric_laws"]
    if laws["numeric_domain"] == "integer" and "base" in seed["state"]["fields"]:
        return [
            "def present(value, base):",
            "    integer = int(value)",
            "    return {",
            "        2: ('-' if integer < 0 else '') + bin(abs(integer))[2:],",
            "        8: ('-' if integer < 0 else '') + oct(abs(integer))[2:],",
            "        10: str(integer),",
            "        16: ('-' if integer < 0 else '') + hex(abs(integer))[2:].upper(),",
            "    }[base]",
            "",
        ]
    return [
        "def present(value):",
        "    if isinstance(value, float):",
        f"        value = round(value, {laws.get('precision', 12)!r})",
        "        if value.is_integer():",
        "            value = int(value)",
        "    return str(value)",
        "",
    ]


def case_boundary(seed):
    laws = seed["semantics"]["numeric_laws"]
    errors = seed["semantics"]["validation"]["errors"]
    if laws["kind"] == "stack":
        calculate = []
    else:
        variables = laws.get("variables", ())
        mapping = "{" + ", ".join(f"{name!r}: case[{name!r}]" for name in variables) + "}"
        calculate = [
            "def calculate_case(case):",
            f"    return evaluate_expression(case['expression'], {mapping})",
            "",
        ]
    base = ", case.get('base', 10)" if "base" in seed["state"]["fields"] else ""
    return [
        *calculate,
        f"ERRORS = {{{', '.join(f'{item!r}: {item!r}' for item in errors)}}}",
        "",
        "def run_case(case):",
        "    try:",
        f"        return {{'result': present(calculate_case(case){base}), 'error': None}}",
        "    except ZeroDivisionError:",
        "        return {'result': None, 'error': 'division-by-zero'}",
        "    except IndexError:",
        "        return {'result': None, 'error': ERRORS.get('invalid-stack', 'invalid-expression')}",
        "    except ValueError as error:",
        "        return {'result': None, 'error': ERRORS.get(str(error), 'invalid-expression')}",
        "    except (ArithmeticError, KeyError, SyntaxError, TypeError):",
        "        return {'result': None, 'error': 'invalid-expression'}",
        "",
    ]


def route_source(seed, routes):
    fields = set(seed["state"]["fields"])
    laws = seed["semantics"]["numeric_laws"]
    lines = [
        "def visible_expression():",
        "    visible = display.get()",
        "    return visible if visible != displayed_value else state['expression']",
        "",
        "def present_display(value):",
        "    global displayed_value",
        "    displayed_value = str(value)",
        "    display.set(displayed_value)",
        "",
    ]
    if "append" in routes:
        lines.extend(
            [
                f"def {routes['append']}(value):",
                "    state['expression'] = visible_expression() + value",
                "    present_display(state['expression'])",
                "",
            ]
        )
    if "clear" in routes:
        lines.extend(
            [
                f"def {routes['clear']}():",
                "    state['expression'] = ''",
            ]
        )
        if "stack" in fields:
            lines.append("    state['stack'].clear()")
        lines.extend(["    present_display('')", ""])
    if "backspace" in routes:
        lines.extend(
            [
                f"def {routes['backspace']}():",
                "    state['expression'] = visible_expression()[:-1]",
                "    present_display(state['expression'])",
                "",
            ]
        )
    if "evaluate" in routes:
        variables = laws.get("variables", ())
        mapping = (
            "{" + ", ".join(f"{name!r}: 0" for name in variables) + "}"
        )
        base = ", state['base']" if "base" in fields else ""
        lines.extend(
            [
                f"def {routes['evaluate']}():",
                "    state['expression'] = visible_expression()",
                "    try:",
                f"        value = evaluate_expression(state['expression'], {mapping})",
            ]
        )
        if "last" in fields:
            lines.append("        state['last'] = value")
        lines.extend(
            [
                "        state['expression'] = str(value)",
                f"        present_display(present(value{base}))",
                "    except ZeroDivisionError:",
                "        present_display('division-by-zero')",
                "    except (ArithmeticError, SyntaxError, TypeError, ValueError):",
                "        present_display('invalid-expression')",
                "",
            ]
        )
    if "base" in routes:
        lines.extend(
            [
                f"def {routes['base']}(value):",
                "    state['base'] = int(value)",
                "    mode_text.set(f'base {value}')",
                "    present_display(present(state['last'], state['base']))",
                "",
            ]
        )
    if "push" in routes:
        lines.extend(
            [
                f"def {routes['push']}():",
                "    state['expression'] = visible_expression()",
                "    if state['expression']:",
                "        state['stack'].append(float(state['expression']) if '.' in state['expression'] else int(state['expression']))",
                "        state['expression'] = ''",
                "    present_display('  '.join(map(str, state['stack'])))",
                "",
            ]
        )
    if "apply" in routes:
        push = routes["push"]
        lines.extend(
            [
                f"def {routes['apply']}(symbol):",
                "    try:",
                f"        {push}()",
                "        right = state['stack'].pop()",
                "        left = state['stack'].pop()",
                "        state['stack'].append(OPERATIONS[symbol](left, right))",
                "        present_display('  '.join(map(str, state['stack'])))",
                "    except (ArithmeticError, IndexError, ValueError):",
                "        present_display('invalid-stack')",
                "",
            ]
        )
    if "plot" in routes:
        series = laws["series"]
        width = series["samples"]
        scale = series["scale"]
        variable = series["variable"]
        accent = seed["presentation"]["theme"]["accent"]
        rendering = seed["presentation"]["rendering"]
        lines.extend(
            [
                f"def {routes['plot']}():",
                "    state['expression'] = visible_expression()",
                "    canvas.delete('all')",
                f"    width, height = ({width!r}, {rendering['canvas_height']!r})",
                f"    canvas.create_line(0, height / 2, width, height / 2, fill={rendering['axis_color']!r})",
                f"    canvas.create_line(width / 2, 0, width / 2, height, fill={rendering['axis_color']!r})",
                "    points = []",
                "    for pixel in range(width):",
                f"        value = (pixel - width / 2) / {scale!r}",
                "        try:",
                f"            y = evaluate_expression(state['expression'], {{{variable!r}: value}})",
                f"            screen_y = height / 2 - float(y) * {scale!r}",
                "            if -height <= screen_y <= height * 2:",
                "                points.extend((pixel, screen_y))",
                "        except (ArithmeticError, SyntaxError, TypeError, ValueError):",
                "            pass",
                "    if len(points) >= 4:",
                f"        canvas.create_line(*points, fill={accent!r}, width={rendering['plot_line_width']!r})",
                f"    mode_text.set({rendering['plot_success']!r})",
                "",
            ]
        )
    return lines


def gui_source(seed, routes, transitions):
    presentation = seed["presentation"]
    columns = presentation["layout"]["columns"]
    theme = presentation["theme"]
    rendering = presentation["rendering"]
    series = "series" in seed["semantics"]["numeric_laws"]
    fields = set(seed["state"]["fields"])
    transition_by_event = {item["event"]: item for item in seed["transitions"]}
    self_test_controls = [
        {
            "identity": control["id"],
            "label": control["label"],
            "row": control["row"],
            "column": control["column"],
            "action": control["action"],
            **(
                {"value": transition_by_event[
                    f"control.{control['id']}.pressed"
                ]["argument"]}
                if "argument"
                in transition_by_event[
                    f"control.{control['id']}.pressed"
                ]
                else {}
            ),
        }
        for control in presentation["controls"]
    ]
    evaluation_control = next(
        (
            control
            for control in self_test_controls
            if control["action"] == "evaluate"
        ),
        None,
    )
    gui_acceptance = (
        seed["acceptance"][0]
        if evaluation_control
        and set(seed["acceptance"][0]["input"]) == {"expression"}
        else None
    )
    globals_ = "display, mode_text, canvas" if series else "display, mode_text"
    lines = [
        f"SELF_TEST_CONTROLS = {self_test_controls!r}",
        "",
        "def build_interface():",
        f"    global {globals_}",
        "    root = Tk()",
        f"    root.title({presentation['title']!r})",
        f"    root.geometry({presentation['geometry']!r})",
        f"    root.configure(bg={theme['background']!r})",
        "    display = StringVar()",
        f"    mode_text = StringVar(value={presentation['mode_label']!r})",
        f"    Entry(root, textvariable=display, font={tuple(rendering['entry_font'])!r}, justify={rendering['entry_justify']!r}).grid(row=0, column=0, columnspan={columns!r}, sticky={rendering['grid_sticky']!r})",
        f"    Label(root, textvariable=mode_text, bg={theme['background']!r}, fg={theme['foreground']!r}).grid(row=1, column=0, columnspan={columns!r}, sticky='w')",
    ]
    if series:
        row = presentation["layout"]["series_row"]
        width = seed["semantics"]["numeric_laws"]["series"]["samples"]
        lines.extend(
            [
                f"    canvas = Canvas(root, width={width!r}, height={rendering['canvas_height']!r}, bg={rendering['canvas_background']!r})",
                f"    canvas.grid(row={row!r}, column=0, columnspan={columns!r})",
            ]
        )
    for control in presentation["controls"]:
        transition = transition_by_event[f"control.{control['id']}.pressed"]
        route = checked_name(transition["route"])
        argument = transition.get("argument")
        command = (
            route
            if argument is None
            else f"lambda value={argument!r}: {route}(value)"
        )
        lines.append(
            "    Button("
            f"root, text={control['label']!r}, command={command}, "
            f"bg={theme['button_background']!r}, "
            f"fg={theme['button_foreground']!r}, width={rendering['button_width']!r}"
            f").grid(row={control['row']!r}, column={control['column']!r}, "
            f"sticky={rendering['grid_sticky']!r})"
        )
    lines.extend(
        f"    root.grid_columnconfigure({column}, weight=1)"
        for column in range(columns)
    )
    lines.extend(
        [
            "    return root",
            "",
            "def reset_interface():",
            "    state.clear()",
            f"    state.update({seed['state']['initial']!r})",
            "    state['expression'] = '1'",
            "    present_display('1')",
            f"    mode_text.set({presentation['mode_label']!r})",
            *(["    canvas.delete('all')"] if series else []),
            "",
            "def self_test_prepare(control):",
            "    reset_interface()",
            *(
                [
                    "    if control['action'] == 'apply':",
                    "        state['stack'] = [1]",
                ]
                if "apply" in routes
                else []
            ),
            *(
                [
                    "    if control['action'] == 'base':",
                    "        state['last'] = 1",
                ]
                if "base" in routes
                else []
            ),
            "",
            "def self_test_effect(control):",
            "    checks = {",
            *(
                [
                    "        'append': lambda: display.get() == '1' + control['value'],",
                ]
                if "append" in routes
                else []
            ),
            *(
                ["        'clear': lambda: display.get() == '',"]
                if "clear" in routes
                else []
            ),
            *(
                ["        'backspace': lambda: display.get() == '',"]
                if "backspace" in routes
                else []
            ),
            *(
                ["        'evaluate': lambda: display.get() == '1',"]
                if "evaluate" in routes
                else []
            ),
            *(
                [
                    "        'base': lambda: state['base'] == int(control['value']),",
                ]
                if "base" in routes
                else []
            ),
            *(
                ["        'push': lambda: state['stack'] == [1],"]
                if "push" in routes
                else []
            ),
            *(
                [
                    "        'apply': lambda: len(state['stack']) == 1 and display.get() != 'invalid-stack',",
                ]
                if "apply" in routes
                else []
            ),
            *(
                [
                    f"        'plot': lambda: len(canvas.find_all()) >= 3 and mode_text.get() == {rendering['plot_success']!r},",
                ]
                if "plot" in routes
                else []
            ),
            "    }",
            "    return checks[control['action']]()",
            "",
            "def self_test_interface(root):",
            "    results = []",
            "    for control in SELF_TEST_CONTROLS:",
            "        self_test_prepare(control)",
            "        widgets = [item for item in root.grid_slaves(row=control['row'], column=control['column']) if item.winfo_class() == 'Button']",
            "        try:",
            "            widget = widgets[0] if len(widgets) == 1 else None",
            "            widget.invoke()",
            "            results.append(widget.cget('text') == control['label'] and self_test_effect(control))",
            "        except Exception:",
            "            results.append(False)",
            *(
                [
                    "    reset_interface()",
                    f"    display.set({gui_acceptance['input']['expression']!r})",
                    "    state['expression'] = ''",
                    f"    widgets = [item for item in root.grid_slaves(row={evaluation_control['row']!r}, column={evaluation_control['column']!r}) if item.winfo_class() == 'Button']",
                    "    widgets[0].invoke()",
                    f"    results.append(display.get() == {(gui_acceptance['expected']['result'] or gui_acceptance['expected']['error'])!r})",
                ]
                if gui_acceptance
                else []
            ),
            "    reset_interface()",
            "    return {'passed': sum(results), 'total': len(results)}",
            "",
            "def self_test_application():",
            "    root = build_interface()",
            "    closed = False",
            "    try:",
            "        report = self_test_interface(root)",
            "    finally:",
            "        root.destroy()",
            "        closed = True",
            "    return {'self_test': report, 'closed': closed}",
            "",
            f"def {checked_name(seed['program']['launch_entrypoint'])}():",
            "    root = build_interface()",
            "    report = self_test_interface(root)",
            "    if report['passed'] != report['total']:",
            "        root.destroy()",
            "        raise RuntimeError('self-test-failed')",
            "    root.mainloop()",
            "",
        ]
    )
    return lines


def stamp_01_outer_to_inner(seed):
    laws = seed["semantics"]["numeric_laws"]
    imports = ["ast", "json", "operator", "sys", *required_imports(seed)]
    if laws["kind"] == "stack":
        imports.remove("ast")
    widgets = ["Button", "Entry", "Label", "StringVar", "Tk"]
    if "series" in laws:
        widgets.append("Canvas")
    return [
        "# stamp: 01_outer_to_inner",
        '"""Generated from concise declarations; no seed is loaded at runtime."""',
        *(f"import {name}" for name in dict.fromkeys(imports)),
        f"from tkinter import {', '.join(widgets)}",
        f"IDENTITY = {seed['identity']['variation']!r}",
        "",
    ]


def stamp_02_inner_to_core(seed):
    return ["# stamp: 02_inner_to_core", ""]


def stamp_03_core_prepare(seed):
    laws = seed["semantics"]["numeric_laws"]
    lines = ["# stamp: 03_core_prepare"]
    if laws["kind"] == "expression":
        lines.extend(expression_runtime(seed))
    elif laws["kind"] == "stack":
        lines.extend(stack_runtime(seed))
    else:
        raise ValueError("unknown-numeric-model")
    return lines


def stamp_04_core_collect(seed):
    return [
        "# stamp: 04_core_collect",
        *presenter(seed),
        *case_boundary(seed),
    ]


def stamp_05_core_to_inner(seed, routes):
    laws = seed["semantics"]["numeric_laws"]
    lines = ["# stamp: 05_core_to_inner"]
    lines.extend(
        [
            "display = None",
            "displayed_value = ''",
            "mode_text = None",
        ]
    )
    if "series" in laws:
        lines.append("canvas = None")
    lines.extend(
        [
            f"state = {seed['state']['initial']!r}",
            "",
            *route_source(seed, routes),
        ]
    )
    return lines


def stamp_06_inner_to_outer(seed, routes, transitions):
    return [
            "# stamp: 06_inner_to_outer",
            *gui_source(seed, routes, transitions),
            "def main(argv=None):",
            "    arguments = list(sys.argv if argv is None else argv)",
            "    if len(arguments) == 3 and arguments[1] == '--case':",
            f"        print(json.dumps({checked_name(seed['program']['case_entrypoint'])}(json.loads(arguments[2])), sort_keys=True))",
            "        return 0",
            "    if len(arguments) == 2 and arguments[1] == '--self-test':",
            "        report = self_test_application()",
            "        print(json.dumps(report, sort_keys=True))",
            "        return 0 if report['closed'] and report['self_test']['passed'] == report['self_test']['total'] else 1",
            f"    {checked_name(seed['program']['launch_entrypoint'])}()",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(main())",
    ]


STAMPS = (
    "01_outer_to_inner",
    "02_inner_to_core",
    "03_core_prepare",
    "04_core_collect",
    "05_core_to_inner",
    "06_inner_to_outer",
)


def render_calculator_source(seed):
    if seed["program"].get("language") != LANGUAGE:
        raise ValueError("declaration-language")
    declared = tuple(item["stage"] for item in seed["_assembly"]["stamps"])
    if declared != STAMPS:
        raise ValueError("stamper-order")
    routes, transitions = action_routes(seed)
    lines = [
        *stamp_01_outer_to_inner(seed),
        *stamp_02_inner_to_core(seed),
        *stamp_03_core_prepare(seed),
        *stamp_04_core_collect(seed),
        *stamp_05_core_to_inner(seed, routes),
        *stamp_06_inner_to_outer(seed, routes, transitions),
    ]
    return "\n".join(lines) + "\n"


def compile_calculator_declaration(seed):
    tree = ast.parse(render_calculator_source(seed))
    ast.fix_missing_locations(tree)
    return tree


def compile_declaration(seed):
    language = seed["program"].get("language")
    compilers = {
        LANGUAGE: compile_calculator_declaration,
        STATEFUL_LANGUAGE: compile_stateful_declaration,
    }
    compiler = compilers.get(language)
    if compiler is None:
        raise ValueError("declaration-language")
    return compiler(seed)


def render_declaration_source(seed):
    renderers = {
        LANGUAGE: render_calculator_source,
        STATEFUL_LANGUAGE: render_stateful_source,
    }
    renderer = renderers.get(seed["program"].get("language"))
    if renderer is None:
        raise ValueError("declaration-language")
    return renderer(seed)
