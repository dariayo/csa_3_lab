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
    EMIT = "emit"
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
        EMIT,
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


def write_code(filename: str, code: list[dict]):
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")


def read_code(source_path: str) -> list:
    with open(source_path, encoding="utf-8") as file:
        return json.loads(file.read())
