from __future__ import annotations

import json
from enum import Enum


class OpcodeParamType(str, Enum):
    CONST = "const"
    ADDR = "addr"
    UNDEFINED = "undefined"
    ADDR_REL = "addr_rel"


class OpcodeParam:
    def __init__(self, param_type: OpcodeParamType, value: any):
        self.param_type = param_type
        self.value = value

    def __str__(self):
        return f"({self.param_type}, {self.value})"


class OpcodeType(str, Enum):
    DROP = "drop"
    DIV = "div"
    SUB = "sub"
    ADD = "add"
    MOD = "mod"
    SWAP = "swap"
    OVER = "over"
    DUP = "dup"
    EQ = "eq"
    LS = "ls"
    OR = "or"
    DI = "di"
    EI = "ei"
    OMIT = "omit"
    READ = "read"
    STORE = "store"
    LOAD = "load"
    PUSH = "push"
    RPOP = "rpop"
    POP = "pop"
    JMP = "jmp"
    ZJMP = "zjmp"
    CALL = "call"
    RET = "ret"
    HALT = "halt"

    def __str__(self):
        return str(self.value)


class Opcode:
    def __init__(self, opcode_type: OpcodeType, params: list[OpcodeParam]):
        self.opcode_type = opcode_type
        self.params = params


class TermType(Enum):
    (
        DI,
        EI,
        DUP,
        ADD,
        SUB,
        DIV,
        MOD,
        OMIT,
        SWAP,
        DROP,
        OVER,
        EQ,
        LS,
        OR,
        READ,
        VARIABLE,
        ALLOT,
        STORE,
        LOAD,
        IF,
        ELSE,
        THEN,
        PRINT,
        DEF,
        RET,
        DEF_INTR,
        DO,
        LOOP,
        BEGIN,
        UNTIL,
        LOOP_CNT,
        CALL,
        STRING,
        ENTRYPOINT,
    ) = range(34)

def word_to_term(word: str) -> Term | None:
    return {
        "di": TermType.DI,
        "ei": TermType.EI,
        "dup": TermType.DUP,
        "+": TermType.ADD,
        "-": TermType.SUB,
        "/": TermType.DIV,
        "mod": TermType.MOD,
        "omit": TermType.OMIT,
        "read": TermType.READ,
        "swap": TermType.SWAP,
        "drop": TermType.DROP,
        "over": TermType.OVER,
        "=": TermType.EQ,
        "<": TermType.LS,
        "variable": TermType.VARIABLE,
        "allot": TermType.ALLOT,
        "!": TermType.STORE,
        "@": TermType.LOAD,
        "if": TermType.IF,
        "else": TermType.ELSE,
        "then": TermType.THEN,
        ".": TermType.OMIT,
        ":": TermType.DEF,
        ";": TermType.RET,
        ":intr": TermType.DEF_INTR,
        "do": TermType.DO,
        "loop": TermType.LOOP,
        "begin": TermType.BEGIN,
        "until": TermType.UNTIL,
        "i": TermType.LOOP_CNT,
        "or": TermType.OR,
    }.get(word)

def write_code(filename: str, code: list[dict]):
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")


def read_code(source_path: str) -> list:
    with open(source_path, encoding="utf-8") as file:
        return json.loads(file.read())
