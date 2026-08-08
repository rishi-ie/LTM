"""Conservative grammar for the frozen L2 arithmetic boundary."""

from __future__ import annotations

import re

from ltm_inference_i3.schemas import FormalExpression

_TOKEN = re.compile(r"\s*(<=|>=|[()+*\-=<>]|\d+|[A-Za-z_]\w*)")
_WORDS = {
    "plus": "+", "add": "+", "added": "+", "times": "*",
    "multiplied": "*", "multiply": "*", "equals": "=",
    "equal": "=", "is": "=",
}


class ParseError(ValueError):
    pass


def _normalise(text: str) -> str:
    value = text.lower().replace("×", "*").replace("⋅", "*").replace("−", "-")
    value = re.sub(r"\bmultiplied\s+by\b", "*", value)
    value = re.sub(r"\badded\s+to\b", "+", value)
    for word, symbol in _WORDS.items():
        value = re.sub(rf"\b{word}\b", symbol, value)
    return value


def _tokenise(text: str) -> list[str]:
    tokens: list[str] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            if text[position:].strip():
                raise ParseError("unsupported mathematical token")
            break
        tokens.append(match.group(1))
        position = match.end()
    return tokens


class _Parser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokenise(_normalise(text))
        self.index = 0

    def peek(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        value = self.peek()
        if value is None or expected is not None and value != expected:
            raise ParseError("unexpected mathematical token")
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
            raise ParseError("missing expression")
        self.take()
        if token.isdigit():
            return FormalExpression("int", value=token)
        if token.isidentifier():
            # Formal-kernel variables use the explicit ``?name`` pattern
            # convention so compiled bodies can instantiate onto numerals.
            return FormalExpression("var", value=f"?{token}")
        raise ParseError("invalid expression atom")

    def proposition(self) -> tuple[FormalExpression, FormalExpression]:
        left = self.expression()
        if self.peek() not in ("=", "<", "<=", ">"):
            raise ParseError("explicit target relation required")
        self.take()
        right = self.expression()
        if self.peek() is not None:
            raise ParseError("trailing mathematical input")
        return left, right


def parse_proposition(text: str) -> tuple[FormalExpression, FormalExpression]:
    value = re.sub(r"^\s*(prove|show|verify|demonstrate)\s+(that\s+)?", "", text, flags=re.IGNORECASE)
    value = re.sub(r"^\s*are\s+(.+?)\s+equivalent\s*\??\s*$", r"\1 = \1", value, flags=re.IGNORECASE)
    return _Parser(value.strip().rstrip("?.")).proposition()


def looks_open_ended(text: str) -> bool:
    return bool(re.search(r"\b(simplify|solve|what is|find|calculate)\b", text, re.IGNORECASE)) and "=" not in text
