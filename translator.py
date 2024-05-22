from __future__ import annotations

import shlex
import sys

from isa import Opcode, OpcodeParam, OpcodeParamType, OpcodeType, TermType, word_to_term, write_code


class Term:
    def __init__(self, word_number: int, term_type: TermType | None, word: str):
        self.converted = False
        self.operand = None
        self.word_number = word_number
        self.term_type = term_type
        self.word = word


variables = {}
variable_address = 512
string_address = 0
functions = {}


def split_to_terms(source_code: str) -> list[Term]:
    words = shlex.split(source_code.replace("\n", " "), posix=True)
    words = [word for word in words if len(word) > 0]
    terms = [Term(0, TermType.ENTRYPOINT, "")]
    for word_number, word in enumerate(words):
        term_type = word_to_term(word)
        if word.startswith(". "):
            word = f'."{word[2:]}"'
            term_type = TermType.STRING
        terms.append(Term(word_number + 1, term_type, word))
    return terms


def validate_indexes(terms: list[Term], begin: TermType, end: TermType, error: str) -> None:
    start_indexes = []
    for idx, term in enumerate(terms):
        if term.term_type == begin:
            start_indexes.append(idx)
        if term.term_type == end:
            assert start_indexes, f"{error} в слове #{term.word_number}"
            term.operand = start_indexes.pop()
    assert not start_indexes, error


def assign_functions(terms: list[Term]) -> None:
    global functions
    func_indices = []
    for idx, term in enumerate(terms):
        if term.term_type in {TermType.DEF, TermType.DEF_INTR}:
            assert idx + 1 < len(terms), f"Пропущено имя функции в слове #{term.word_number}"
            assert not func_indices, f"Незакрытая функция в слове #{term.word_number}"
            assert term.word not in functions, f"Повторяющаяся функция в слове #{term.word_number}"
            func_indices.append(term.word_number)
            func_name = terms[idx + 1].word
            functions[func_name] = term.word_number + 1
            terms[idx + 1].converted = True
        if term.term_type == TermType.RET:
            assert func_indices, f"RET не в функции в слове #{term.word_number}"
            function_term = terms[func_indices.pop()]
            function_term.operand = term.word_number + 1
    assert not func_indices, "Незакрытая функция"


def assign_variables(terms: list[Term]) -> None:
    global variable_address
    for term_index, term in enumerate(terms):
        # variable <name> [<size> allot]
        if term.term_type is TermType.VARIABLE:
            assert term_index + 1 < len(terms), "Неверное объявление переменной в слове #" + str(term.word_number)
            assert terms[term_index + 1].term_type is None, "Имя переменной такое же, как ключ в слове #" + str(
                term.word_number + 1
            )
            assert terms[term_index + 1].word[0].isalpha(), "Неверное имя переменной в слове #" + str(
                term.word_number + 1
            )
            assert terms[term_index + 1] not in variables, " Переменная уже существует в слове #" + str(
                term.word_number + 1
            )
            variables[terms[term_index + 1].word] = variable_address
            variable_address += 1
            terms[term_index + 1].converted = True
            if term_index + 3 < len(terms) and terms[term_index + 3].term_type is TermType.ALLOT:
                allot_variable_memory(terms, term_index + 3)


def allot_variable_memory(terms: list[Term], term_index: int) -> None:
    global variable_address
    assert term_index + 3 < len(terms), "Неверное объявление выделения"
    term = terms[term_index]
    if term.term_type is TermType.ALLOT:
        assert term_index - 3 >= 0, "Неверное объявление выделения в слове #" + str(term.word_number)
        terms[term_index - 1].converted = True
        try:
            allot_size = int(terms[term_index - 1].word)
            assert 1 <= allot_size <= 100, "Неверный размер выделения в слове #" + str(term.word_number - 1)
            variable_address += allot_size
        except ValueError:
            assert True, "Неверный размер выделения в слове #" + str(term.word_number - 1)


def check_if_else_then(terms: list[Term]) -> None:
    nested_ifs = []
    for term_index, term in enumerate(terms):
        if term.term_type is TermType.IF:
            nested_ifs.append(term)
        elif term.term_type is TermType.ELSE:
            nested_ifs.append(term)
        elif term.term_type is TermType.THEN:
            assert len(nested_ifs) > 0, "IF-ELSE-THEN несбалансированный в слове #" + str(term.word_number)
            last_if = nested_ifs.pop()
            if last_if.term_type is TermType.ELSE:
                last_else = last_if
                assert len(nested_ifs) > 0, "IF-ELSE-THEN несбалансированный в слове #" + str(term.word_number)
                last_if = nested_ifs.pop()
                last_else.operand = term.word_number + 1
                last_if.operand = last_else.word_number + 1
            else:
                last_if.operand = term.word_number + 1

    assert len(nested_ifs) == 0, "IF-ELSE-THEN несбалансированный в слове #" + str(nested_ifs[0].word_number)


def replace_vars_funcs(terms: list[Term]) -> None:
    for term_index, term in enumerate(terms):
        if term.term_type is None and not term.converted:
            if term.word in variables:
                term.word = str(variables[term.word])
    for term_index, term in enumerate(terms):
        if term.term_type is None and not term.converted:
            if term.word in functions.keys():
                term.operand = functions[term.word]
                term.term_type = TermType.CALL
                term.word = "call"


def validate_and_correct_terms(terms: list[Term]) -> None:
    validate_indexes(terms, TermType.DO, TermType.LOOP, "Несбалансированный do ... loop")
    validate_indexes(terms, TermType.BEGIN, TermType.UNTIL, "Несбалансированный begin ... until")
    assign_functions(terms)
    assign_variables(terms)
    replace_vars_funcs(terms)
    check_if_else_then(terms)


def fix_literal(term: Term) -> list[Opcode]:
    global string_address
    if term.converted:
        return []
    if term.term_type != TermType.STRING:
        return [Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, term.word)])]

    opcodes = []
    content = term.word[2:-1]
    string_start = string_address

    opcodes.append(Opcode(OpcodeType.POP, []))
    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, len(content))]))
    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, string_address)]))
    opcodes.append(Opcode(OpcodeType.STORE, []))
    string_address += 1

    for char in content:
        opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, ord(char))]))
        opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, string_address)]))
        opcodes.append(Opcode(OpcodeType.STORE, []))
        string_address += 1

    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, string_start)]))
    opcodes.append(Opcode(OpcodeType.LOAD, []))
    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, string_start)]))
    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, 1)]))
    opcodes.append(Opcode(OpcodeType.ADD, []))
    opcodes.append(Opcode(OpcodeType.OVER, []))
    opcodes.append(Opcode(OpcodeType.ZJMP, [OpcodeParam(OpcodeParamType.ADDR_REL, 12)]))
    opcodes.append(Opcode(OpcodeType.DUP, []))
    opcodes.append(Opcode(OpcodeType.LOAD, []))
    opcodes.append(Opcode(OpcodeType.RPOP, []))
    opcodes.append(Opcode(OpcodeType.DUP, []))
    opcodes.append(Opcode(OpcodeType.POP, []))
    opcodes.append(Opcode(OpcodeType.OMIT, []))
    opcodes.append(Opcode(OpcodeType.SWAP, []))
    opcodes.append(Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, 1)]))
    opcodes.append(Opcode(OpcodeType.SUB, []))
    opcodes.append(Opcode(OpcodeType.SWAP, []))
    opcodes.append(Opcode(OpcodeType.JMP, [OpcodeParam(OpcodeParamType.ADDR_REL, -14)]))

    return opcodes


def term2opcodes(term: Term) -> list[Opcode]:
    opcodes = {
        TermType.DI: [Opcode(OpcodeType.DI, [])],
        TermType.EI: [Opcode(OpcodeType.EI, [])],
        TermType.DUP: [Opcode(OpcodeType.DUP, [])],
        TermType.ADD: [Opcode(OpcodeType.ADD, [])],
        TermType.OR: [Opcode(OpcodeType.OR, [])],
        TermType.SUB: [Opcode(OpcodeType.SUB, [])],
        TermType.DIV: [Opcode(OpcodeType.DIV, [])],
        TermType.MOD: [Opcode(OpcodeType.MOD, [])],
        TermType.OMIT: [Opcode(OpcodeType.OMIT, [])],
        TermType.SWAP: [Opcode(OpcodeType.SWAP, [])],
        TermType.DROP: [Opcode(OpcodeType.DROP, [])],
        TermType.OVER: [Opcode(OpcodeType.OVER, [])],
        TermType.EQ: [Opcode(OpcodeType.EQ, [])],
        TermType.LS: [Opcode(OpcodeType.LS, [])],
        TermType.READ: [Opcode(OpcodeType.READ, [])],
        TermType.VARIABLE: [],
        TermType.ALLOT: [],
        TermType.STORE: [Opcode(OpcodeType.STORE, [])],
        TermType.LOAD: [Opcode(OpcodeType.LOAD, [])],
        TermType.IF: [Opcode(OpcodeType.ZJMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
        TermType.ELSE: [Opcode(OpcodeType.JMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
        TermType.THEN: [],
        TermType.DEF: [Opcode(OpcodeType.JMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
        TermType.RET: [Opcode(OpcodeType.RET, [])],
        TermType.DEF_INTR: [],
        TermType.DO: [
            Opcode(OpcodeType.DI, []),
            Opcode(OpcodeType.POP, []),
            Opcode(OpcodeType.POP, []),
            Opcode(OpcodeType.EI, []),
        ],
        TermType.LOOP: [
            Opcode(OpcodeType.DI, []),
            Opcode(OpcodeType.RPOP, []),
            Opcode(OpcodeType.RPOP, []),
            Opcode(OpcodeType.PUSH, [OpcodeParam(OpcodeParamType.CONST, 1)]),
            Opcode(OpcodeType.ADD, []),
            Opcode(OpcodeType.OVER, []),
            Opcode(OpcodeType.OVER, []),
            Opcode(OpcodeType.LS, []),
            Opcode(OpcodeType.ZJMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)]),
            Opcode(OpcodeType.DROP, []),
            Opcode(OpcodeType.DROP, []),
            Opcode(OpcodeType.EI, []),
        ],
        TermType.BEGIN: [],
        TermType.UNTIL: [Opcode(OpcodeType.ZJMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
        TermType.LOOP_CNT: [
            Opcode(OpcodeType.DI, []),
            Opcode(OpcodeType.RPOP, []),
            Opcode(OpcodeType.RPOP, []),
            Opcode(OpcodeType.OVER, []),
            Opcode(OpcodeType.OVER, []),
            Opcode(OpcodeType.POP, []),
            Opcode(OpcodeType.POP, []),
            Opcode(OpcodeType.SWAP, []),
            Opcode(OpcodeType.DROP, []),
            Opcode(OpcodeType.EI, []),
        ],
        TermType.CALL: [Opcode(OpcodeType.CALL, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
        TermType.ENTRYPOINT: [Opcode(OpcodeType.JMP, [OpcodeParam(OpcodeParamType.UNDEFINED, None)])],
    }.get(term.term_type)

    if term.operand and opcodes is not None:
        for opcode in opcodes:
            for param_num, param in enumerate(opcode.params):
                if param.param_type is OpcodeParamType.UNDEFINED:
                    opcode.params[param_num].param_type = OpcodeParamType.ADDR
                    opcode.params[param_num].value = term.operand

    if opcodes is None:
        return fix_literal(term)

    return opcodes


def fix_addresses(term_opcodes: list[list[Opcode]]) -> list[Opcode]:
    result_opcodes = []
    pref_sum = [0]
    for term_num, opcodes in enumerate(term_opcodes):
        term_opcode_cnt = len(opcodes)
        pref_sum.append(pref_sum[term_num] + term_opcode_cnt)
    for term_opcode in list(filter(lambda x: x is not None, term_opcodes)):
        for opcode in term_opcode:
            for param_num, param in enumerate(opcode.params):
                if param.param_type is OpcodeParamType.ADDR:
                    opcode.params[param_num].value = pref_sum[param.value]
                    opcode.params[param_num].param_type = OpcodeParamType.CONST
                if param.param_type is OpcodeParamType.ADDR_REL:
                    opcode.params[param_num].value = len(result_opcodes) + opcode.params[param_num].value
                    opcode.params[param_num].param_type = OpcodeParamType.CONST
            result_opcodes.append(opcode)
    return result_opcodes


def fix_interrupt(terms: list[Term]) -> list[Term]:
    is_interrupt = False
    interrupt_ret = 1
    terms_interrupt_proc = []
    terms_not_interrupt_proc = []
    for term in terms[1:]:
        if term.term_type is TermType.DEF_INTR:
            is_interrupt = True
        if term.term_type is TermType.RET:
            if is_interrupt:
                terms_interrupt_proc.append(term)
                interrupt_ret = len(terms_interrupt_proc) + 1
            else:
                terms_not_interrupt_proc.append(term)
            is_interrupt = False

        if is_interrupt:
            terms_interrupt_proc.append(term)
        elif not is_interrupt and term.term_type is not TermType.RET:
            terms_not_interrupt_proc.append(term)

    terms[0].operand = interrupt_ret
    return [*[terms[0]], *terms_interrupt_proc, *terms_not_interrupt_proc]


def terms_to_opcodes(terms: list[Term]) -> list[Opcode]:
    terms = fix_interrupt(terms)
    opcodes = list(map(term2opcodes, terms))
    opcodes = fix_addresses(opcodes)
    return [*opcodes, Opcode(OpcodeType.HALT, [])]


def translate(source_code: str) -> list[dict]:
    terms = split_to_terms(source_code)
    validate_and_correct_terms(terms)
    opcodes = terms_to_opcodes(terms)
    commands = []
    for index, opcode in enumerate(opcodes):
        command = {
            "index": index,
            "command": opcode.opcode_type,
        }
        if len(opcode.params):
            command["arg"] = int(opcode.params[0].value)
        commands.append(command)
    return commands


def main(source_file: str, target_file: str) -> None:
    global variables, variable_address, string_address, functions

    variables = {}
    variable_address = 512
    string_address = 0
    functions = {}

    with open(source_file, encoding="utf-8") as f:
        source_code = f.read()
    code = translate(source_code)
    write_code(target_file, code)
    print("source LoC:", len(source_code.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Неверные аргументы: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
