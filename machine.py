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
    NEXT_TEMP = "next_temp"
    TEMP_NEXT = "temp_next"
    TEMP_TOP = "temp_top"
    TEMP_RETURN = "temp_return"
    TOP_TEMP = "top_temp"
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
    MUL = "mul"
    DIV = "div"
    MOD = "mod"
    EQ = "eq"
    GR = "gr"
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
        ALUOpcode.MUL,
        ALUOpcode.DIV,
        ALUOpcode.MOD,
        ALUOpcode.EQ,
        ALUOpcode.GR,
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
        elif self.operation == ALUOpcode.MUL:
            self.result = self.src_a * self.src_b
        elif self.operation == ALUOpcode.DIV:
            self.result = self.src_b // self.src_a
        elif self.operation == ALUOpcode.SUB:
            self.result = self.src_b - self.src_a
        elif self.operation == ALUOpcode.MOD:
            self.result = self.src_b % self.src_a
        elif self.operation == ALUOpcode.EQ:
            self.result = int(self.src_a == self.src_b)
        elif self.operation == ALUOpcode.GR:
            self.result = int(self.src_a < self.src_b)
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
    temp = None

    alu = None

    def __init__(self, memory_size: int, data_stack_size: int, return_stack_size: int):
        assert memory_size > 0, "Размер памяти данных должен быть > 0"
        assert data_stack_size > 0, "Размер стека данных должен быть > 0"
        assert return_stack_size > 0, "Размер стека возврата должен быть > 0"

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
        self.temp = 8877

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
        elif selector is Selector.NEXT_TEMP:
            self.next = self.temp

    def signal_latch_temp(self, selector: Selector) -> None:
        if selector is Selector.TEMP_RETURN:
            assert self.i >= 0, "Адрес меньше 0"
            assert self.i < self.return_stack_size, "Переполнение стека возврата"
            self.temp = self.return_stack[self.i]
        elif selector is Selector.TEMP_TOP:
            self.temp = self.top_of_stack
        elif selector is Selector.TEMP_NEXT:
            self.temp = self.next

    def signal_latch_top(self, selector: Selector, immediate=0) -> None:
        if selector is Selector.TOP_NEXT:
            self.top_of_stack = self.next
        elif selector is Selector.TOP_TEMP:
            self.top_of_stack = self.temp
        elif selector is Selector.TOP_INPUT:
            self.top_of_stack = 47474747
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
            self.return_stack[self.i] = self.temp

    def signal_mem_write(self) -> None:
        assert self.top_of_stack >= 0, "Адрес меньше 0"
        assert self.top_of_stack < self.memory_size, "Переполнение памяти"
        self.memory[self.top_of_stack] = self.next

    def signal_alu_operation(self, operation: ALUOpcode) -> None:
        self.alu.set_details(self.top_of_stack, self.next, operation)
        self.alu.alu_op()


def opcode_to_alu_opcode(opcode_type: OpcodeType):
    return {
        OpcodeType.MUL: ALUOpcode.MUL,
        OpcodeType.DIV: ALUOpcode.DIV,
        OpcodeType.SUB: ALUOpcode.SUB,
        OpcodeType.ADD: ALUOpcode.ADD,
        OpcodeType.MOD: ALUOpcode.MOD,
        OpcodeType.EQ: ALUOpcode.EQ,
        OpcodeType.GR: ALUOpcode.GR,
        OpcodeType.LS: ALUOpcode.LS,
        OpcodeType.OR: ALUOpcode.OR,
    }.get(opcode_type)


class ControlUnit:
    out_buffer = ""
    program_memory_size = None
    program_memory = None
    data_path = None
    ps = None
    IO = "h"
    input_tokens: typing.ClassVar[list[tuple]] = []
    tokens_handled: typing.ClassVar[list[bool]] = []

    tick_number = 0
    instruction_number = 0

    def __init__(self, data_path: DataPath, program_memory_size: int, input_tokens: list[tuple]):
        self.data_path = data_path
        self.input_tokens = input_tokens
        self.tokens_handled = [False for _ in input_tokens]
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
        self.ps["Intr_Req"] = self.check_for_interrupts()

    def check_for_interrupts(self) -> bool:
        if self.ps["Intr_On"]:
            for index, interrupt in enumerate(self.input_tokens):
                if not self.tokens_handled[index] and interrupt[0] <= self.tick_number:
                    self.IO = interrupt[1]
                    self.ps["Intr_Req"] = True
                    self.ps["Intr_On"] = False
                    self.tokens_handled[index] = True
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
        self.check_for_interrupts()
        self.signal_latch_pc(Selector.PC_INC)

    def decode_execute(self) -> None:  # noqa: C901 -- function is too complex
        memory_cell = self.program_memory[self.data_path.pc]
        command = memory_cell["command"]
        arithmetic_operation = opcode_to_alu_opcode(command)
        if arithmetic_operation:
            self.tick([lambda: self.data_path.signal_alu_operation(arithmetic_operation)])
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_ALU)])
            self.tick([lambda: self.data_path.signal_latch_sp(Selector.SP_DEC)])
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        elif command == OpcodeType.PUSH:
            self.tick([lambda: self.data_path.signal_data_wr()])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                    lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_IMMEDIATE, memory_cell["arg"])])
        elif command == OpcodeType.DROP:
            self.tick(
                [
                    lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        elif command == OpcodeType.OMIT:
            if chr(self.data_path.next) == "⊭":
                self.out_buffer += str(self.data_path.top_of_stack)
            else:
                self.out_buffer += chr(self.data_path.next)
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
        elif command == OpcodeType.READ:
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
        elif command == OpcodeType.SWAP:
            self.tick([lambda: self.data_path.signal_latch_temp(Selector.TEMP_TOP)])
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT)])
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_TEMP)])
        elif command == OpcodeType.OVER:
            self.tick([lambda: self.data_path.signal_data_wr()])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_temp(Selector.TEMP_TOP),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT)])
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_TEMP)])
        elif command == OpcodeType.DUP:
            self.tick([lambda: self.data_path.signal_data_wr()])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                ]
            )
        elif command == OpcodeType.LOAD:
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_MEM)])
        elif command == OpcodeType.STORE:
            self.tick(
                [lambda: self.data_path.signal_mem_write(), lambda: self.data_path.signal_latch_sp(Selector.SP_DEC)]
            )
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_top(Selector.TOP_NEXT),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_DEC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_next(Selector.NEXT_MEM)])
        elif command == OpcodeType.POP:
            self.tick([lambda: self.data_path.signal_latch_temp(Selector.TEMP_TOP)])
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
        elif command == OpcodeType.RPOP:
            self.tick([lambda: self.data_path.signal_latch_i(Selector.I_DEC)])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_temp(Selector.TEMP_RETURN),
                    lambda: self.data_path.signal_data_wr(),
                ]
            )
            self.tick(
                [
                    lambda: self.data_path.signal_latch_next(Selector.NEXT_TOP),
                    lambda: self.data_path.signal_latch_sp(Selector.SP_INC),
                ]
            )
            self.tick([lambda: self.data_path.signal_latch_top(Selector.TOP_TEMP)])
        elif command == OpcodeType.ZJMP:
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
        elif command == OpcodeType.JMP:
            self.tick([lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, memory_cell["arg"])])
        elif command == OpcodeType.CALL:
            self.tick([lambda: self.data_path.signal_ret_wr(Selector.RET_STACK_PC)])
            self.tick(
                [
                    lambda: self.data_path.signal_latch_i(Selector.I_INC),
                    lambda: self.signal_latch_pc(Selector.PC_IMMEDIATE, memory_cell["arg"]),
                ]
            )
        elif command == OpcodeType.DI:
            self.tick([lambda: self.signal_latch_ps(False)])
        elif command == OpcodeType.EI:
            self.tick([lambda: self.signal_latch_ps(True)])
        elif command == OpcodeType.RET:
            self.tick([lambda: self.data_path.signal_latch_i(Selector.I_DEC)])
            self.tick([lambda: self.signal_latch_pc(Selector.PC_RET)])
        elif command == OpcodeType.HALT:
            raise StopIteration

    def __print__(self, comment: str) -> None:
        tos_memory = self.data_path.data_stack[self.data_path.sp - 1 : self.data_path.sp - 4 : -1]
        tos = [self.data_path.top_of_stack, self.data_path.next, *tos_memory]
        ret_tos = self.data_path.return_stack[self.data_path.i - 1 : self.data_path.i - 4 : -1]
        state_repr = (
            "TICK: {:4} | PC: {:3} | PS_REQ {:1} | PS_STATE: {:1} | SP: {:3} | I: {:3} | "
            "TEMP: {:7} | DATA_MEMORY[TOP] {:7} | TOS : {} | RETURN_TOS : {}"
        ).format(
            self.tick_number,
            self.data_path.pc,
            self.ps["Intr_Req"],
            self.ps["Intr_On"],
            self.data_path.sp,
            self.data_path.i,
            self.data_path.temp,
            self.data_path.memory[self.data_path.top_of_stack]
            if self.data_path.top_of_stack < self.data_path.memory_size
            else "?",
            str(tos),
            str(ret_tos),
        )
        logger.info(state_repr + " " + comment)


def simulation(code: list, limit: int, input_tokens: list[tuple]):
    data_path = DataPath(15000, 15000, 15000)
    control_unit = ControlUnit(data_path, 15000, input_tokens)
    control_unit.fill_memory(code)
    while control_unit.instruction_number < limit:
        try:
            control_unit.command_cycle()
        except StopIteration:
            break
    return [control_unit.out_buffer, control_unit.instruction_number, control_unit.tick_number]


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
