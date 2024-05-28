from __future__ import annotations

import logging
import sys
import typing
from enum import Enum

import pytest as pytest
from isa import OpcodeType, read_code

logger = logging.getLogger("machine_logger")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Selector(str, Enum):
    SP_INC = "sp_inc"
    SP_DEC = "sp_dec"
    I_INC = "i_inc"
    I_DEC = "i_dec"
    RET_STACK_PC = "ret_stack_pc"
    RET_STACK_OUT = "ret_stack_out"
    NEXT_MEM = "next_mem"
    NEXT_TOP = "next_top"
    NEXT_MEDIUM = "next_medium"
    MEDIUM_NEXT = "medium_next"
    MEDIUM_TOP = "medium_top"
    MEDIUM_RETURN = "medium_return"
    TOP_MEDIUM = "top_medium"
    TOP_NEXT = "top_next"
    TOP_ALU = "top_alu"
    TOP_MEM = "top_mem"
    TOP_IMMEDIATE = "top_immediate"
    TOP_INPUT = "top_input"
    PC_INC = "pc_int"
    PC_RET = "pc_ret"
    PC_IMMEDIATE = "pc_immediate"

    def __str__(self) -> str:
        return str(self.value)


class ALUOpcode(str, Enum):
    INC_A = "inc_a"
    DEC_A = "dec_a"
    INC_B = "inc_b"
    DEC_B = "dec_b"
    ADD = "add"
    SUB = "sub"
    DIV = "div"
    MOD = "mod"
    EQ = "eq"
    LS = "ls"
    OR = "or"

    def __str__(self) -> str:
        return str(self.value)


class ALU:
    alu_operations: typing.ClassVar[list[ALUOpcode]] = [
        ALUOpcode.INC_A,
        ALUOpcode.DEC_A,
        ALUOpcode.INC_B,
        ALUOpcode.DEC_B,
        ALUOpcode.ADD,
        ALUOpcode.SUB,
        ALUOpcode.DIV,
        ALUOpcode.MOD,
        ALUOpcode.EQ,
        ALUOpcode.LS,
        ALUOpcode.OR,
    ]
    result = None
    src_a = None
    src_b = None
    operation = None

    def __init__(self):
        self.result = 0
        self.src_a = None
        self.src_b = None
        self.operation = None

    def alu_op(self) -> None:  # noqa: C901 -- function is too complex
        if self.operation == ALUOpcode.INC_A:
            self.result = self.src_a + 1
        elif self.operation == ALUOpcode.INC_B:
            self.result = self.src_b + 1
        elif self.operation == ALUOpcode.DEC_A:
            self.result = self.src_a - 1
        elif self.operation == ALUOpcode.DEC_B:
            self.result = self.src_b - 1
        elif self.operation == ALUOpcode.ADD:
            self.result = self.src_a + self.src_b
        elif self.operation == ALUOpcode.DIV:
            self.result = self.src_b // self.src_a
        elif self.operation == ALUOpcode.SUB:
            self.result = self.src_b - self.src_a
        elif self.operation == ALUOpcode.MOD:
            self.result = self.src_b % self.src_a
        elif self.operation == ALUOpcode.EQ:
            self.result = int(self.src_a == self.src_b)
        elif self.operation == ALUOpcode.LS:
            self.result = int(self.src_a >= self.src_b)
        elif self.operation == ALUOpcode.OR:
            self.result = self.src_a | self.src_b
        else:
            pytest.fail(f"Unknown ALU operation: {self.operation}")

    def set_details(self, src_a, src_b, operation: ALUOpcode) -> None:
        self.src_a = src_a
        self.src_b = src_b
        self.operation = operation


class DataPath:
    memory_size = None
    memory = None
    data_stack_size = None
    data_stack = None
    return_stack_size = None
    return_stack = None

    sp = None
    i = None
    pc = None
    top_of_stack = None
    next = None
    medium = None

    alu = None
    input_tokens: typing.ClassVar[list[tuple]] = []
    tokens_handled: typing.ClassVar[list[bool]] = []
    out_buffer = ""

    def __init__(self, memory_size: int, data_stack_size: int, return_stack_size: int, input_tokens: list[tuple]):
        assert memory_size > 0, "Размер памяти данных должен быть > 0"
        assert data_stack_size > 0, "Размер стека данных должен быть > 0"
        assert return_stack_size > 0, "Размер стека возврата должен быть > 0"

        self.input_tokens = input_tokens
        self.tokens_handled = [False for _ in input_tokens]
        self.memory_size = memory_size
        self.memory = [4747] * memory_size
        self.data_stack_size = data_stack_size
        self.data_stack = [8877] * data_stack_size
        self.return_stack_size = return_stack_size
        self.return_stack = [9988] * return_stack_size

        self.sp = 4
        self.i = 4
        self.pc = 0
        self.top_of_stack = 8877
        self.next = 8877
        self.medium = 8877

        self.alu = ALU()

    def signal_latch_sp(self, selector: Selector) -> None:
        if selector is Selector.SP_DEC:
            self.sp -= 1
        elif selector is Selector.SP_INC:
            self.sp += 1

    def signal_latch_i(self, selector: Selector) -> None:
        if selector is Selector.I_DEC:
            self.i -= 1
        elif selector is Selector.I_INC:
            self.i += 1

    def signal_latch_next(self, selector: Selector) -> None:
        if selector is Selector.NEXT_MEM:
            assert self.sp >= 0, "Адрес меньше 0"
            assert self.sp < self.data_stack_size, "Переполнение стека данных"
            self.next = self.data_stack[self.sp]
        elif selector is Selector.NEXT_TOP:
            self.next = self.top_of_stack
        elif selector is Selector.NEXT_MEDIUM:
            self.next = self.medium

    def signal_latch_medium(self, selector: Selector) -> None:
        if selector is Selector.MEDIUM_RETURN:
            assert self.i >= 0, "Адрес меньше 0"
            assert self.i < self.return_stack_size, "Переполнение стека возврата"
            self.medium = self.return_stack[self.i]
        elif selector is Selector.MEDIUM_TOP:
            self.medium = self.top_of_stack
        elif selector is Selector.MEDIUM_NEXT:
            self.medium = self.next

    def signal_latch_top(self, selector: Selector, immediate=0) -> None:
        if selector is Selector.TOP_NEXT:
            self.top_of_stack = self.next
        elif selector is Selector.TOP_MEDIUM:
            self.top_of_stack = self.medium
        elif selector is Selector.TOP_ALU:
            self.top_of_stack = self.alu.result
        elif selector is Selector.TOP_MEM:
            self.top_of_stack = self.memory[self.top_of_stack]
        elif selector is Selector.TOP_IMMEDIATE:
            self.top_of_stack = immediate

    def signal_data_wr(self) -> None:
        assert self.sp >= 0, "Адрес меньше 0"
        assert self.sp < self.data_stack_size, "Переполнение стека данных"
        self.data_stack[self.sp] = self.next

    def signal_ret_wr(self, selector: Selector) -> None:
        assert self.i >= 0, "Address below 0"
        assert self.i < self.return_stack_size, "Переполнение стека возврата"
        if selector is Selector.RET_STACK_PC:
            self.return_stack[self.i] = self.pc
        elif selector is Selector.RET_STACK_OUT:
            self.return_stack[self.i] = self.medium

    def signal_mem_write(self) -> None:
        assert self.top_of_stack >= 0, "Адрес меньше 0"
        assert self.top_of_stack < self.memory_size, "Переполнение памяти"
        self.memory[self.top_of_stack] = self.next

    def signal_alu_operation(self, operation: ALUOpcode) -> None:
        self.alu.set_details(self.top_of_stack, self.next, operation)
        self.alu.alu_op()


def opcode_to_alu_opcode(opcode_type: OpcodeType):
    return {
        OpcodeType.DIV: ALUOpcode.DIV,
        OpcodeType.SUB: ALUOpcode.SUB,
        OpcodeType.ADD: ALUOpcode.ADD,
        OpcodeType.MOD: ALUOpcode.MOD,
        OpcodeType.EQ: ALUOpcode.EQ,
        OpcodeType.LS: ALUOpcode.LS,
        OpcodeType.OR: ALUOpcode.OR,
    }.get(opcode_type)


class ControlUnit:
    program_memory_size = None
    program_memory = None
    data_path = None
    ps = None
    IO = ""

    tick_number = 0
    instruction_number = 0

    def __init__(self, data_path: DataPath, program_memory_size: int):
        self.data_path = data_path
        self.program_memory_size = program_memory_size
        self.program_memory = [{"index": x, "command": 0, "arg": 0} for x in range(self.program_memory_size)]
        self.ps = {"Intr_Req": False, "Intr_On": True}

    def fill_memory(self, opcodes: list) -> None:
        for opcode in opcodes:
            mem_cell = int(opcode["index"])
            assert 0 <= mem_cell < self.program_memory_size, "Индекс программы выходит за размер памяти"
            self.program_memory[mem_cell] = opcode

    def signal_latch_pc(self, selector: Selector, immediate=0) -> None:
        if selector is Selector.PC_INC:
            self.data_path.pc += 1
        elif selector is Selector.PC_RET:
            self.data_path.pc = self.data_path.return_stack[self.data_path.i]
        elif selector is Selector.PC_IMMEDIATE:
            self.data_path.pc = immediate - 1

    def signal_latch_ps(self, intr_on: bool) -> None:
        self.ps["Intr_On"] = intr_on
        self.ps["Intr_Req"] = self.find_interrupt()

    def find_interrupt(self) -> bool:
        if self.ps["Intr_On"]:
            for index, interrupt in enumerate(self.data_path.input_tokens):
                if not self.data_path.tokens_handled[index] and interrupt[0] <= self.tick_number:
                    self.IO = interrupt[1]
                    self.ps["Intr_Req"] = True
                    self.ps["Intr_On"] = False
                    self.data_path.tokens_handled[index] = True
                    self.tick([lambda: self.data_path.signal_ret_wr(Selector.RET_STACK_PC)])
                    self.tick(
                        [
                            lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, 1),
                            lambda: self.data_path.signal_latch_i(Selector.I_INC),
                        ]
                    )
                    break
        return False

    def tick(self, operations: list[typing.Callable], comment="", limit_tick=200) -> None:
        self.tick_number += 1
        for operation in operations:
            operation()
        if self.tick_number < limit_tick:
            self.__print__(comment)

    def command_cycle(self):
        self.instruction_number += 1
        self.decode_execute()
        self.find_interrupt()
        self.signal_latch_pc(Selector.PC_INC)

    def arithmetic(self, arithmetic_operation):
        self.tick([lambda: self.data_path.signal_alu_operation(arithmetic_operation)])
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_ALU)])
        self.tick([lambda: self.data_path.signal_latch_sp(Selector.SP_DEC)])
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])

    def push(self, memory_cell: dict):
        self.tick([lambda: self.data_path.signal_data_wr()])
        self.tick(
            [
                lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_IMMEDIATE, memory_cell["arg"])])

    def drop(self):
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])

    def omit(self):
        if chr(self.data_path.next) == "⊭":
            self.data_path.out_buffer += str(self.data_path.top_of_stack)
        else:
            self.data_path.out_buffer += chr(self.data_path.next)
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])

    def read(self):
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick([lambda: self.data_path.signal_data_wr()])
        self.tick(
            [
                lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_IMMEDIATE, ord(self.IO))])

    def swap(self):
        self.tick([lambda: self.data_path.signal_latch_medium(Selector.MEDIUM_TOP)])
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT)])
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEDIUM)])

    def over(self):
        self.tick([lambda: self.data_path.signal_data_wr()])
        self.tick(
            [
                lambda: self.data_path.signal_latch_medium(Selector.MEDIUM_TOP),
                lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT)])
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEDIUM)])

    def dup(self):
        self.tick([lambda: self.data_path.signal_data_wr()])
        self.tick(
            [
                lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
                lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
            ]
        )

    def load(self):
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_MEM)])

    def store(self):
        self.tick([lambda: self.data_path.signal_mem_write(), lambda: self.data_path.signal_latch_sp(Selector.SP_DEC)])
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])

    def pop(self):
        self.tick([lambda: self.data_path.signal_latch_medium(Selector.MEDIUM_TOP)])
        self.tick(
            [
                lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
            ]
        )
        self.tick(
            [
                lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM),
                lambda: self.data_path.signal_ret_wr(Selector.RET_STACK_OUT),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_i(Selector.I_INC)])

    def rpop(self):
        self.tick([lambda: self.data_path.signal_latch_i(Selector.I_DEC)])
        self.tick(
            [
                lambda: self.data_path.signal_latch_medium(Selector.MEDIUM_RETURN),
                lambda: self.data_path.signal_data_wr(),
            ]
        )
        self.tick(
            [
                lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
                lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
            ]
        )
        self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_MEDIUM)])

    def zjmp(self, memory_cell: dict):
        if self.data_path.top_of_stack == 0:
            self.tick(
                [
                    lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, memory_cell["arg"]),
                    lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        else:
            self.tick(
                [
                    lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])

    def jmp(self, memory_cell: dict):
        self.tick([lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, memory_cell["arg"])])

    def call(self, memory_cell: dict):
        self.tick([lambda: self.data_path.signal_ret_wr(Selector.RET_STACK_PC)])
        self.tick(
            [
                lambda: self.data_path.signal_latch_i(Selector.I_INC),
                lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, memory_cell["arg"]),
            ]
        )

    def ret(self):
        self.tick([lambda: self.data_path.signal_latch_i(Selector.I_DEC)])
        self.tick([lambda: self.signal_latch_pc(Selector.PC_RET)])

    def di(self):
        self.tick([lambda: self.signal_latch_ps(False)])

    def ei(self):
        self.tick([lambda: self.signal_latch_ps(True)])

    def decode_execute(self) -> None:  # noqa: C901 -- function is too complex
        memory_cell = self.program_memory[self.data_path.pc]
        command = memory_cell["command"]
        arithmetic_operation = opcode_to_alu_opcode(command)
        if arithmetic_operation:
            self.arithmetic(arithmetic_operation)
        elif command == OpcodeType.PUSH:
            self.push(memory_cell)
        elif command == OpcodeType.DROP:
            self.drop()
        elif command == OpcodeType.OMIT:
            self.omit()
        elif command == OpcodeType.READ:
            self.read()
        elif command == OpcodeType.SWAP:
            self.swap()
        elif command == OpcodeType.OVER:
            self.over()
        elif command == OpcodeType.DUP:
            self.dup()
        elif command == OpcodeType.LOAD:
            self.load()
        elif command == OpcodeType.STORE:
            self.store()
        elif command == OpcodeType.POP:
            self.pop()
        elif command == OpcodeType.RPOP:
            self.rpop()
        elif command == OpcodeType.ZJMP:
            self.zjmp(memory_cell)
        elif command == OpcodeType.JMP:
            self.jmp(memory_cell)
        elif command == OpcodeType.CALL:
            self.call(memory_cell)
        elif command == OpcodeType.DI:
            self.di()
        elif command == OpcodeType.EI:
            self.ei()
        elif command == OpcodeType.RET:
            self.ret()
        elif command == OpcodeType.HALT:
            raise StopIteration

    def __print__(self, comment: str) -> None:
        tos_memory = self.data_path.data_stack[self.data_path.sp - 1 : self.data_path.sp - 4 : -1]
        tos = [self.data_path.top_of_stack, self.data_path.next, *tos_memory]
        ret_tos = self.data_path.return_stack[self.data_path.i - 1 : self.data_path.i - 4 : -1]

        state_repr = (
            "TICK: {:4} | COMMAND: {:5} | PC: {:3} | PS_REQ: {:1} | PS_STATE: {:1} | "
            "SP: {:3} | I: {:3} | MEDIUM: {:7} | DATA_MEMORY[TOP]: {:7} | "
            "TOS: {} | RETURN_TOS: {}"
        ).format(
            self.tick_number,
            self.program_memory[self.data_path.pc]["command"],
            self.data_path.pc,
            self.ps["Intr_Req"],
            self.ps["Intr_On"],
            self.data_path.sp,
            self.data_path.i,
            self.data_path.medium,
            self.data_path.memory[self.data_path.top_of_stack]
            if self.data_path.top_of_stack < self.data_path.memory_size
            else "?",
            tos,
            ret_tos,
        )

        logger.info(f"{state_repr} {comment}")


def simulation(code: list, limit: int, input_tokens: list[tuple]):
    data_path = DataPath(10000, 10000, 10000, input_tokens)
    control_unit = ControlUnit(data_path, 10000)
    control_unit.fill_memory(code)
    while control_unit.instruction_number < limit:
        try:
            control_unit.command_cycle()
        except StopIteration:
            break
    return [data_path.out_buffer, control_unit.instruction_number, control_unit.tick_number]


def main(code_file: str, token_path: str | None) -> None:
    input_tokens = []
    if token_path:
        with open(token_path, encoding="utf-8") as file:
            input_tokens = eval(file.read())
    code = read_code(code_file)
    output, instr_num, ticks = simulation(code, limit=55000, input_tokens=input_tokens)
    print(f"Output: {output}\nInstructions: {instr_num}\nTicks: {ticks - 1}")


if __name__ == "__main__":
    assert 2 <= len(sys.argv) <= 3, "Неверные аргументы: machine.py <code_file> <input_file>"
    if len(sys.argv) == 3:
        _, code_file, input_file = sys.argv
    else:
        _, code_file = sys.argv
        input_file = None
    main(code_file, input_file)
