"""Small exact arithmetic parser with explicit variable binders."""

from __future__ import annotations

import re

from ltm_inference_i3.schemas import FormalExpression


class ParseError(ValueError):
    pass


_TOKEN = re.compile(r"\s*(<=|>=|[()+*\-=<>]|\d+|[A-Za-z_]\w*)")


def _tokens(text: str) -> list[str]:
    result: list[str] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            if text[position:].strip():
                raise ParseError("PARSE_AMBIGUOUS")
            break
        result.append(match.group(1))
        position = match.end()
    return result


class _Parser:
    def __init__(self, text: str, variables: frozenset[str]) -> None:
        self.tokens = _tokens(text)
        self.variables = variables
        self.index = 0

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        value = self.peek()
        if value is None or expected is not None and value != expected:
            raise ParseError("PARSE_AMBIGUOUS")
        self.index += 1
        return value

    def expression(self) -> FormalExpression:
        value = self.term()
        while self.peek() in ("+", "-"):
            operator = self.take()
            right = self.term()
            value = FormalExpression("add", (value, right if operator == "+" else FormalExpression("neg", (right,))))
        return value

    def term(self) -> FormalExpression:
        value = self.factor()
        while self.peek() == "*":
            self.take("*")
            value = FormalExpression("mul", (value, self.factor()))
        return value

    def factor(self) -> FormalExpression:
        token = self.peek()
        if token == "-":
            self.take("-")
            return FormalExpression("neg", (self.factor(),))
        if token == "(":
            self.take("(")
            value = self.expression()
            self.take(")")
            return value
        if token is None:
            raise ParseError("PARSE_AMBIGUOUS")
        self.take()
        if token.isdigit():
            return FormalExpression("int", value=token)
        if token.isidentifier():
            return FormalExpression("var", value=f"?{token}") if token in self.variables else FormalExpression("atom", value=token)
        raise ParseError("PARSE_AMBIGUOUS")

    def proposition(self) -> tuple[FormalExpression, FormalExpression]:
        left = self.expression()
        if self.peek() != "=":
            raise ParseError("EXPLICIT_TARGET_REQUIRED")
        self.take("=")
        right = self.expression()
        if self.peek() is not None:
            raise ParseError("PARSE_AMBIGUOUS")
        return left, right


def parse_proposition(text: str) -> tuple[FormalExpression, FormalExpression]:
    value = text.strip().rstrip("?.")
    value = re.sub(r"^\s*(prove|show|verify|demonstrate)\s+(that\s+)?", "", value, flags=re.IGNORECASE)
    binder_match = re.match(r"^\s*(?:for\s+all|for\s+every|for)\s+([A-Za-z_]\w*)\s*[,;:]\s*(.+)$", value, re.IGNORECASE)
    variables = frozenset({binder_match.group(1)} if binder_match else ())
    value = binder_match.group(2) if binder_match else value
    return _Parser(value, variables).proposition()


def looks_open_ended(text: str) -> bool:
    return bool(re.search(r"\b(simplify|solve|what\s+is|find|calculate)\b", text, re.IGNORECASE)) and "=" not in text
