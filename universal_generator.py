"""Compile one seed profile into one exact standalone calculator program."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

FORMAT = "manual-calculator-profile-1"
ACTIONS = frozenset(
    {
        "append",
        "clear",
        "backspace",
        "evaluate",
        "base",
        "push",
        "apply",
        "plot",
    }
)


def canonical(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def expand_controls(profile):
    controls = []
    for row_index, row in enumerate(profile.pop("keypad"), start=2):
        for column, item in enumerate(row):
            controls.append({**item, "row": row_index, "column": column})
    profile["controls"] = controls
    return profile


def selected_authority(profile):
    backend = profile["backend"]
    language = profile["_language"]
    selected = {
        "binary": set(backend.get("operators", ())),
        "unary": set(backend.get("unary", ())),
        "functions": set(backend.get("functions", ())),
        "constants": set(backend.get("constants", ())),
    }
    declaration = {key: value for key, value in profile.items() if key != "_language"}
    declaration["language"] = {
        family: [
            item
            for item in language[family]
            if item["id"] in selected[family]
        ]
        for family in ("binary", "unary", "functions", "constants")
    }
    return declaration


def validate(profile):
    errors = []
    controls = profile.get("controls", ())
    positions = [(item.get("row"), item.get("column")) for item in controls]
    if profile.get("format") != FORMAT:
        errors.append("format")
    if profile.get("backend", {}).get("kind") not in ("expression", "stack"):
        errors.append("backend-kind")
    if not controls or len(positions) != len(set(positions)):
        errors.append("controls")
    if len({item.get("id") for item in controls}) != len(controls):
        errors.append("control-identity")
    if any(item.get("action") not in ACTIONS for item in controls):
        errors.append("control-action")
    if not profile.get("acceptance"):
        errors.append("acceptance")
    return errors


def selected_imports(profile):
    backend = profile["backend"]
    language = profile["_language"]
    selected_functions = {
        item["id"]: item
        for item in language["functions"]
        if item["id"] in backend.get("functions", ())
    }
    authority = json.dumps(
        {
            "functions": selected_functions,
            "constants": [
                item
                for item in language["constants"]
                if item["id"] in backend.get("constants", ())
            ],
        },
        sort_keys=True,
    )
    imports = ["import json", "import operator", "import sys"]
    if backend["kind"] != "stack":
        imports.insert(0, "import ast")
    if "math." in authority:
        imports.append("import math")
    if "statistics." in authority:
        imports.append("import statistics")
    widgets = ["Button", "Entry", "Label", "StringVar", "Tk"]
    if backend.get("series"):
        widgets.append("Canvas")
    imports.append("from tkinter import " + ", ".join(widgets))
    return imports


def render_expression(node, language):
    binary = {item["id"]: item for item in language["binary"]}
    if "literal" in node:
        return repr(node["literal"])
    if "parameter" in node:
        return node["parameter"]
    if "variadic" in node:
        return node["variadic"]
    if "spread" in node:
        return "*" + node["spread"]
    if "list" in node:
        return "list(" + render_expression(node["list"], language) + ")"
    if "call" in node:
        arguments = ", ".join(
            render_expression(item, language) for item in node.get("arguments", ())
        )
        return f"{node['call']}({arguments})"
    if "choose" in node:
        choice = node["choose"]
        return (
            f"({render_expression(choice['then'], language)} if "
            f"{render_expression(choice['when'], language)} else "
            f"{render_expression(choice['otherwise'], language)})"
        )
    if "equal" in node:
        left, right = node["equal"]
        return (
            f"({render_expression(left, language)} == "
            f"{render_expression(right, language)})"
        )
    if "negate" in node:
        return f"(-{render_expression(node['negate'], language)})"
    operation = next((name for name in binary if name in node), None)
    if operation is None:
        raise ValueError("unknown-semantic-node")
    left, right = node[operation]
    return (
        f"({render_expression(left, language)} "
        f"{binary[operation]['emit']} {render_expression(right, language)})"
    )


def render_capabilities(profile):
    backend = profile["backend"]
    language = profile["_language"]
    binary = {item["id"]: item for item in language["binary"]}
    unary = {item["id"]: item for item in language["unary"]}
    functions = {item["id"]: item for item in language["functions"]}
    constants = {item["id"]: item for item in language["constants"]}
    lines = []
    emitted_functions = {}
    for index, name in enumerate(backend.get("functions", ())):
        declaration = functions[name]
        emitted_name = f"_semantic_{index}"
        emitted_functions[name] = emitted_name
        parameters = ", ".join(declaration.get("parameters", ()))
        if declaration.get("variadic"):
            parameters = "*" + declaration["variadic"]
        lines.extend(
            (
                f"def {emitted_name}({parameters}):",
                f"    return {render_expression(declaration['body'], language)}",
                "",
            )
        )
    if backend["kind"] != "stack":
        lines.extend(("BINARY = {",))
        lines.extend(
            f"    {binary[name]['syntax']}: {binary[name]['target']},"
            for name in backend["operators"]
        )
        lines.extend(("}", "UNARY = {"))
        lines.extend(
            f"    {unary[name]['syntax']}: {unary[name]['target']},"
            for name in backend.get("unary", ())
        )
        lines.append("}")
        if backend.get("functions"):
            lines.extend(("FUNCTIONS = {",))
            lines.extend(
                f"    {name!r}: {emitted_functions[name]},"
                for name in backend["functions"]
            )
            lines.append("}")
        if backend.get("constants"):
            lines.extend(("CONSTANTS = {",))
            lines.extend(
                f"    {name!r}: {constants[name]['target']},"
                for name in backend["constants"]
            )
            lines.append("}")
    return lines


def render_expression_core(profile):
    backend = profile["backend"]
    lines = [
        "",
        "def evaluate_node(node, variables):",
        "    if isinstance(node, ast.Expression):",
        "        return evaluate_node(node.body, variables)",
        "    if isinstance(node, ast.Constant) and type(node.value) in (int, float):",
        "        return node.value",
    ]
    if backend.get("variables"):
        lines.extend(
            (
                "    if isinstance(node, ast.Name) and node.id in variables:",
                "        return variables[node.id]",
            )
        )
    if backend.get("constants"):
        lines.extend(
            (
                "    if isinstance(node, ast.Name) and node.id in CONSTANTS:",
                "        return CONSTANTS[node.id]",
            )
        )
    lines.extend(
        (
            "    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:",
            "        return BINARY[type(node.op)](",
            "            evaluate_node(node.left, variables),",
            "            evaluate_node(node.right, variables),",
            "        )",
            "    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:",
            "        return UNARY[type(node.op)](evaluate_node(node.operand, variables))",
        )
    )
    if backend.get("functions"):
        lines.extend(
            (
                "    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:",
                "        return FUNCTIONS[node.func.id](*(evaluate_node(item, variables) for item in node.args))",
            )
        )
    lines.extend(
        (
            '    raise ValueError("invalid-expression")',
            "",
            "def evaluate_expression(expression, variables=None):",
            f"    if not expression or len(expression) > {backend.get('maximum_characters', 512)}:",
            '        raise ValueError("invalid-expression")',
            "    value = evaluate_node(ast.parse(expression, mode='eval'), variables or {})",
        )
    )
    if backend.get("numeric_domain") == "integer":
        lines.extend(
            (
                "    if type(value) is not int:",
                '        raise ValueError("integer-required")',
            )
        )
    lines.extend(("    return value", ""))
    return lines


def render_present(profile):
    backend = profile["backend"]
    lines = [
        "def present(value, base):"
        if backend.get("numeric_domain") == "integer"
        else "def present(value):"
    ]
    if backend.get("numeric_domain") == "integer":
        lines.extend(
            (
                "    integer = int(value)",
                "    return {",
                '        2: ("-" if integer < 0 else "") + bin(abs(integer))[2:],',
                '        8: ("-" if integer < 0 else "") + oct(abs(integer))[2:],',
                "        10: str(integer),",
                '        16: ("-" if integer < 0 else "") + hex(abs(integer))[2:].upper(),',
                "    }[base]",
            )
        )
    else:
        lines.extend(
            (
                "    if isinstance(value, float):",
                f"        value = round(value, {backend.get('precision', 12)})",
                "        if value.is_integer():",
                "            value = int(value)",
                "    return str(value)",
            )
        )
    return [*lines, ""]


def render_run_case(profile):
    if profile["backend"]["kind"] == "stack":
        binary = {
            item["id"]: item for item in profile["_language"]["binary"]
        }
        return [
            "OPERATIONS = {",
            *(
                f"    {binary[name]['token']!r}: {binary[name]['target']},"
                for name in profile["backend"]["operators"]
            ),
            "}",
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
            '        raise ValueError("invalid-stack")',
            "    return stack[0]",
            "",
        ]
    variables = (
        "{"
        + ", ".join(
            f"{name!r}: case[{name!r}]"
            for name in profile["backend"].get("variables", ())
        )
        + "}"
    )
    return [
        "def calculate_case(case):",
        f"    return evaluate_expression(case['expression'], {variables})",
        "",
    ]


def render_controls(profile):
    action_names = {
        "append": "append",
        "clear": "clear",
        "backspace": "backspace",
        "evaluate": "evaluate",
        "base": "set_base",
        "push": "push",
        "apply": "apply",
        "plot": "plot",
    }
    lines = []
    for control in profile["controls"]:
        function = action_names[control["action"]]
        command = (
            f"lambda value={control.get('value', '')!r}: {function}(value)"
            if control["action"] in ("append", "base", "apply")
            else function
        )
        lines.extend(
            (
                "    Button(",
                f"        root, text={control['label']!r}, command={command},",
                f"        bg={profile['theme']['button_background']!r},",
                f"        fg={profile['theme']['button_foreground']!r}, width={control.get('width', 7)},",
                f"    ).grid(row={control['row']}, column={control['column']}, sticky='nsew')",
            )
        )
    return lines


def render_gui(profile):
    backend = profile["backend"]
    actions = {item["action"] for item in profile["controls"]}
    state = {"expression": ""}
    globals_ = ["display", "mode_text"]
    if "base" in actions:
        state.update({"last": 0, "base": 10})
    if "push" in actions or "apply" in actions:
        state["stack"] = []
    if backend.get("series"):
        globals_.append("canvas")
    lines = [*(f"{name} = None" for name in globals_), f"state = {state!r}", ""]
    if "append" in actions:
        lines.extend(
            (
                "def append(value):",
                "    state['expression'] += value",
                "    display.set(state['expression'])",
                "",
            )
        )
    if "clear" in actions:
        clear_lines = ["def clear():", "    state['expression'] = ''"]
        if "stack" in state:
            clear_lines.append("    state['stack'].clear()")
        clear_lines.extend(("    display.set('')", ""))
        lines.extend(clear_lines)
    if "backspace" in actions:
        lines.extend(
            (
                "def backspace():",
                "    state['expression'] = state['expression'][:-1]",
                "    display.set(state['expression'])",
                "",
            )
        )
    if "evaluate" in actions:
        variables = (
            repr({name: 0 for name in backend.get("variables", ())})
            if backend.get("variables")
            else "{}"
        )
        presentation = (
            "present(value, state['base'])"
            if "base" in actions
            else "present(value)"
        )
        lines.extend(
            (
                "def evaluate():",
                "    try:",
                f"        value = evaluate_expression(state['expression'], {variables})",
                *(("        state['last'] = value",) if "base" in actions else ()),
                "        state['expression'] = str(value)",
                f"        display.set({presentation})",
                "    except ZeroDivisionError:",
                "        display.set('division-by-zero')",
                "    except (ArithmeticError, SyntaxError, TypeError, ValueError):",
                "        display.set('invalid-expression')",
                "",
            )
        )
    if "base" in actions:
        lines.extend(
            (
                "def set_base(value):",
                "    state['base'] = int(value)",
                "    mode_text.set(f'base {value}')",
                "    display.set(present(state['last'], state['base']))",
                "",
            )
        )
    if "push" in actions:
        lines.extend(
            (
                "def push():",
                "    if state['expression']:",
                "        state['stack'].append(float(state['expression']) if '.' in state['expression'] else int(state['expression']))",
                "        state['expression'] = ''",
                "    display.set('  '.join(map(str, state['stack'])))",
                "",
            )
        )
    if "apply" in actions:
        lines.extend(
            (
                "def apply(symbol):",
                "    try:",
                "        push()",
                "        right = state['stack'].pop()",
                "        left = state['stack'].pop()",
                "        state['stack'].append(OPERATIONS[symbol](left, right))",
                "        display.set('  '.join(map(str, state['stack'])))",
                "    except (ArithmeticError, IndexError, ValueError):",
                "        display.set('invalid-stack')",
                "",
            )
        )
    if "plot" in actions:
        series = backend["series"]
        variable = series["variable"]
        samples = series["samples"]
        scale = series["scale"]
        lines.extend(
            (
                "def plot():",
                "    canvas.delete('all')",
                f"    width, height = {samples}, 180",
                "    canvas.create_line(0, height / 2, width, height / 2, fill='#888')",
                "    canvas.create_line(width / 2, 0, width / 2, height, fill='#888')",
                "    points = []",
                "    for pixel in range(width):",
                f"        value = (pixel - width / 2) / {scale}",
                "        try:",
                f"            y = evaluate_expression(state['expression'], {{{variable!r}: value}})",
                f"            screen_y = height / 2 - float(y) * {scale}",
                "            if -height <= screen_y <= height * 2:",
                "                points.extend((pixel, screen_y))",
                "        except (ArithmeticError, SyntaxError, TypeError, ValueError):",
                "            pass",
                "    if len(points) >= 4:",
                f"        canvas.create_line(*points, fill={profile['theme']['accent']!r}, width=2)",
                "    mode_text.set('series plotted')",
                "",
            )
        )
    lines.extend(
        (
            "def launch():",
            "    global " + ", ".join(globals_),
            "    root = Tk()",
            f"    root.title({profile['title']!r})",
            f"    root.geometry({profile.get('geometry', '420x360')!r})",
            f"    root.configure(bg={profile['theme']['background']!r})",
            "    display = StringVar()",
            f"    mode_text = StringVar(value={profile.get('mode_label', profile['identity'])!r})",
            f"    Entry(root, textvariable=display, font=('Menlo', 18), justify='right').grid(row=0, column=0, columnspan={profile['layout']['columns']}, sticky='nsew')",
            f"    Label(root, textvariable=mode_text, bg={profile['theme']['background']!r}, fg={profile['theme']['foreground']!r}).grid(row=1, column=0, columnspan={profile['layout']['columns']}, sticky='w')",
        )
    )
    if backend.get("series"):
        lines.extend(
            (
                "    canvas = Canvas(root, width=390, height=180, bg='white')",
                f"    canvas.grid(row={profile['layout']['series_row']}, column=0, columnspan={profile['layout']['columns']})",
            )
        )
    lines.extend(render_controls(profile))
    lines.extend(
        f"    root.grid_columnconfigure({column}, weight=1)"
        for column in range(profile["layout"]["columns"])
    )
    lines.extend(("    root.mainloop()", ""))
    return lines


def render_source(profile):
    lines = [
        '"""Build-time specialized calculator. No seed or profile is loaded at runtime."""',
        *selected_imports(profile),
        "",
        f"IDENTITY = {profile['identity']!r}",
        *render_capabilities(profile),
    ]
    if profile["backend"]["kind"] != "stack":
        lines.extend(render_expression_core(profile))
    lines.extend(render_present(profile))
    lines.extend(render_run_case(profile))
    presentation = (
        "present(calculate_case(case), case.get('base', 10))"
        if profile["backend"].get("numeric_domain") == "integer"
        else "present(calculate_case(case))"
    )
    lines.extend(
        (
            "def run_case(case):",
            "    try:",
            f"        return {{'result': {presentation}, 'error': None}}",
            "    except ZeroDivisionError:",
            "        return {'result': None, 'error': 'division-by-zero'}",
            "    except (ArithmeticError, IndexError, KeyError, SyntaxError, TypeError, ValueError):",
            "        return {'result': None, 'error': 'invalid-expression'}",
            "",
        )
    )
    lines.extend(render_gui(profile))
    lines.extend(
        (
            "def main(argv=None):",
            "    arguments = list(sys.argv if argv is None else argv)",
            "    if len(arguments) == 3 and arguments[1] == '--case':",
            "        print(json.dumps(run_case(json.loads(arguments[2])), sort_keys=True))",
            "        return 0",
            "    launch()",
            "    return 0",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(main())",
            "",
        )
    )
    return "\n".join(lines).encode()


def load_profile(path, profile_id):
    document = json.loads(path.read_text(encoding="utf-8"))
    profile = (
        next(item for item in document["profiles"] if item["identity"] == profile_id)
        if document.get("format") == "manual-calculator-program-suite-2"
        else document
    )
    loaded = json.loads(json.dumps(profile))
    loaded["_language"] = document["language"]
    return expand_controls(loaded)


def generate(profile_path, output, profile_id=None):
    profile_path = Path(profile_path).resolve(strict=True)
    output = Path(output).resolve(strict=False)
    profile = load_profile(profile_path, profile_id)
    errors = validate(profile)
    if errors:
        raise ValueError(",".join(errors))
    source = render_source(profile)
    compiled = compile(source, f"<generated:{profile['identity']}>", "exec")
    namespace = {"__name__": "generated.verification"}
    exec(compiled, namespace)
    stage = Path(tempfile.mkdtemp(prefix="." + output.name + "-", dir=output.parent))
    try:
        (stage / "main.py").write_bytes(source)
        results = [
            namespace["run_case"](case["input"]) == case["expected"]
            for case in profile["acceptance"]
        ]
        if not all(results):
            raise ValueError("acceptance-failed")
        selected = {
            "operators": profile["backend"].get("operators", ()),
            "unary": profile["backend"].get("unary", ()),
            "functions": profile["backend"].get("functions", ()),
            "constants": profile["backend"].get("constants", ()),
            "actions": sorted({item["action"] for item in profile["controls"]}),
        }
        manifest = {
            "format": "manual-compile-time-calculator-1",
            "profile": profile["identity"],
            "seed_sha256": digest(canonical(selected_authority(profile))),
            "files": {"main.py": digest(source)},
            "selected_capabilities": selected,
            "runtime_seed_files": 0,
            "runtime_common_engine_files": 0,
            "verification": {"passed": sum(results), "total": len(results)},
            "controls_verified": len(profile["controls"]),
        }
        (stage / "manifest.json").write_bytes(canonical(manifest))
        backup = output.with_name("." + output.name + ".previous")
        if backup.exists():
            shutil.rmtree(backup)
        if output.exists():
            output.rename(backup)
        stage.rename(output)
        if backup.exists():
            shutil.rmtree(backup)
        return manifest
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("profile")
    parser.add_argument("--profile-id")
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args(argv)
    sys.stdout.buffer.write(
        canonical(generate(arguments.profile, arguments.output, arguments.profile_id))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
