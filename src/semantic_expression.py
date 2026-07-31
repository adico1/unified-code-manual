"""Render seed-declared semantic expressions into specialized Python."""

from __future__ import annotations

import re


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
        return checked_qualified(payload)
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
    raise ValueError("unknown-semantic-expression")


def function_source(items, *, prefix="_semantic"):
    lines = []
    names = []
    for index, item in enumerate(items):
        internal = f"{prefix}_{index}"
        parameters = item.get("parameters")
        if parameters is None:
            parameters = ["*" + checked_name(item["variadic"])]
        else:
            parameters = [checked_name(value) for value in parameters]
        lines.extend(
            [
                f"def {internal}({', '.join(parameters)}):",
                f"    return {expression(item['body'])}",
                "",
            ]
        )
        names.append((item["id"], internal))
    return lines, names
