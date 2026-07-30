"""Compile calculator declarations into a specialized Python syntax tree."""

from __future__ import annotations

import ast
import re


LANGUAGE = "calculator-declaration-1"
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
    if not isinstance(value, dict) or len(value) != 1:
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
    if set(value) == {"call", "arguments"}:
        target = checked_qualified(value["call"])
        arguments = ", ".join(expression(item) for item in value["arguments"])
        return f"{target}({arguments})"
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
        "def run_case(case):",
        "    try:",
        f"        return {{'result': present(calculate_case(case){base}), 'error': None}}",
        "    except ZeroDivisionError:",
        "        return {'result': None, 'error': 'division-by-zero'}",
        "    except (ArithmeticError, IndexError, KeyError, SyntaxError, TypeError, ValueError):",
        "        return {'result': None, 'error': 'invalid-expression'}",
        "",
    ]


def route_source(seed, routes):
    fields = set(seed["state"]["fields"])
    laws = seed["semantics"]["numeric_laws"]
    lines = []
    if "append" in routes:
        lines.extend(
            [
                f"def {routes['append']}(value):",
                "    state['expression'] += value",
                "    display.set(state['expression'])",
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
        lines.extend(["    display.set('')", ""])
    if "backspace" in routes:
        lines.extend(
            [
                f"def {routes['backspace']}():",
                "    state['expression'] = state['expression'][:-1]",
                "    display.set(state['expression'])",
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
                "    try:",
                f"        value = evaluate_expression(state['expression'], {mapping})",
            ]
        )
        if "last" in fields:
            lines.append("        state['last'] = value")
        lines.extend(
            [
                "        state['expression'] = str(value)",
                f"        display.set(present(value{base}))",
                "    except ZeroDivisionError:",
                "        display.set('division-by-zero')",
                "    except (ArithmeticError, SyntaxError, TypeError, ValueError):",
                "        display.set('invalid-expression')",
                "",
            ]
        )
    if "base" in routes:
        lines.extend(
            [
                f"def {routes['base']}(value):",
                "    state['base'] = int(value)",
                "    mode_text.set(f'base {value}')",
                "    display.set(present(state['last'], state['base']))",
                "",
            ]
        )
    if "push" in routes:
        lines.extend(
            [
                f"def {routes['push']}():",
                "    if state['expression']:",
                "        state['stack'].append(float(state['expression']) if '.' in state['expression'] else int(state['expression']))",
                "        state['expression'] = ''",
                "    display.set('  '.join(map(str, state['stack'])))",
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
                "        display.set('  '.join(map(str, state['stack'])))",
                "    except (ArithmeticError, IndexError, ValueError):",
                "        display.set('invalid-stack')",
                "",
            ]
        )
    if "plot" in routes:
        series = laws["series"]
        width = series["samples"]
        scale = series["scale"]
        variable = series["variable"]
        accent = seed["presentation"]["theme"]["accent"]
        lines.extend(
            [
                f"def {routes['plot']}():",
                "    canvas.delete('all')",
                f"    width, height = ({width!r}, 180)",
                "    canvas.create_line(0, height / 2, width, height / 2, fill='#888')",
                "    canvas.create_line(width / 2, 0, width / 2, height, fill='#888')",
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
                f"        canvas.create_line(*points, fill={accent!r}, width=2)",
                "    mode_text.set('series plotted')",
                "",
            ]
        )
    return lines


def gui_source(seed, routes, transitions):
    presentation = seed["presentation"]
    columns = presentation["layout"]["columns"]
    theme = presentation["theme"]
    series = "series" in seed["semantics"]["numeric_laws"]
    globals_ = "display, mode_text, canvas" if series else "display, mode_text"
    lines = [
        f"def {checked_name(seed['program']['launch_entrypoint'])}():",
        f"    global {globals_}",
        "    root = Tk()",
        f"    root.title({presentation['title']!r})",
        f"    root.geometry({presentation['geometry']!r})",
        f"    root.configure(bg={theme['background']!r})",
        "    display = StringVar()",
        f"    mode_text = StringVar(value={presentation['mode_label']!r})",
        f"    Entry(root, textvariable=display, font=('Menlo', 18), justify='right').grid(row=0, column=0, columnspan={columns!r}, sticky='nsew')",
        f"    Label(root, textvariable=mode_text, bg={theme['background']!r}, fg={theme['foreground']!r}).grid(row=1, column=0, columnspan={columns!r}, sticky='w')",
    ]
    if series:
        row = presentation["layout"]["series_row"]
        width = seed["semantics"]["numeric_laws"]["series"]["samples"]
        lines.extend(
            [
                f"    canvas = Canvas(root, width={width!r}, height=180, bg='white')",
                f"    canvas.grid(row={row!r}, column=0, columnspan={columns!r})",
            ]
        )
    transition_by_event = {item["event"]: item for item in seed["transitions"]}
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
            f"fg={theme['button_foreground']!r}, width=7"
            f").grid(row={control['row']!r}, column={control['column']!r}, "
            "sticky='nsew')"
        )
    lines.extend(
        f"    root.grid_columnconfigure({column}, weight=1)"
        for column in range(columns)
    )
    lines.extend(["    root.mainloop()", ""])
    return lines


def compile_declaration(seed):
    if seed["program"].get("language") != LANGUAGE:
        raise ValueError("declaration-language")
    laws = seed["semantics"]["numeric_laws"]
    routes, transitions = action_routes(seed)
    imports = ["ast", "json", "operator", "sys", *required_imports(seed)]
    if laws["kind"] == "stack":
        imports.remove("ast")
    widgets = ["Button", "Entry", "Label", "StringVar", "Tk"]
    if "series" in laws:
        widgets.append("Canvas")
    lines = [
        '"""Generated from concise declarations; no seed is loaded at runtime."""',
        *(f"import {name}" for name in dict.fromkeys(imports)),
        f"from tkinter import {', '.join(widgets)}",
        f"IDENTITY = {seed['identity']['variation']!r}",
        "",
    ]
    if laws["kind"] == "expression":
        lines.extend(expression_runtime(seed))
    elif laws["kind"] == "stack":
        lines.extend(stack_runtime(seed))
    else:
        raise ValueError("unknown-numeric-model")
    lines.extend(presenter(seed))
    lines.extend(case_boundary(seed))
    lines.extend(
        [
            "display = None",
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
            *gui_source(seed, routes, transitions),
            "def main(argv=None):",
            "    arguments = list(sys.argv if argv is None else argv)",
            "    if len(arguments) == 3 and arguments[1] == '--case':",
            f"        print(json.dumps({checked_name(seed['program']['case_entrypoint'])}(json.loads(arguments[2])), sort_keys=True))",
            "        return 0",
            f"    {checked_name(seed['program']['launch_entrypoint'])}()",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(main())",
        ]
    )
    source = "\n".join(lines) + "\n"
    tree = ast.parse(source)
    ast.fix_missing_locations(tree)
    return tree
