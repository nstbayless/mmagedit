import re
from parsimonious.grammar import Grammar
from parsimonious.nodes import Node, NodeVisitor
from parsimonious.exceptions import IncompleteParseError, ParseError
from functools import reduce

mnemonics = {
# machine instructions
'adc': {'imm': 0x69, 'z': 0x65, 'zx': 0x75, 'abs': 0x6d, 'abx': 0x7d, 'aby': 0x79, 'zix': 0x61, 'ziy': 0x71},
'and': ['adc', 0x20-0x60],
'asl': {'a': 0x0a, 'z': 0x06, 'zx': 0x16, 'abs': 0x0e, 'abx': 0x1e},
'bit': {'z': 0x24, 'abs': 0x2c},
'bpl': {'rel': 0x10},
'bmi': {'rel': 0x30},
'bvc': {'rel': 0x50},
'bvs': {'rel': 0x70},
'bcc': {'rel': 0x90},
'blt': {'rel': 0x90},
'bcs': {'rel': 0xb0},
'bge': {'rel': 0xb0},
'bne': {'rel': 0xd0},
'beq': {'rel': 0xf0},
'brk': {'a': 0x00},
'cmp': ['adc', 0xc0-0x60],
'cpx': {'imm': 0xe0, 'z': 0xe4, 'abs': 0xec},
'cpy': ['cpx', 0xc0-0xe0],
'dec': {'z': 0xc6, 'zx': 0xd6, 'abs': 0xce, 'abx': 0xde},
'eor': ['adc', 0x40-0x60],
'clc': {'a': 0x18},
'sec': {'a': 0x38},
'cli': {'a': 0x58},
'sei': {'a': 0x78},
'clv': {'a': 0xb8},
'cld': {'a': 0xd8},
'sed': {'a': 0xf8},
'inc': ['dec', 0xe0-0xc0],
'jmp': {'abs': 0x4c, 'ind': 0x6c},
'jsr': {'abs': 0x20},
'lda': ['adc', 0xa0-0x60],
'ldx': {'imm': 0xa2, 'z': 0xa6, 'zy': 0xb6, 'abs': 0xae, 'aby': 0xbe},
'ldy': {'imm': 0xa0, 'z': 0xa4, 'zx': 0xb4, 'abs': 0xac, 'abx': 0xbc},
'lsr': ['asl', 0x40],
'nop': {'a': 0xea},
'ora': ['adc', -0x60],
'tax': {'a': 0xaa},
'txa': {'a': 0x8a},
'dex': {'a': 0xca},
'inx': {'a': 0xe8},
'tay': {'a': 0xa8},
'tya': {'a': 0x98},
'dey': {'a': 0x88},
'iny': {'a': 0xc8},
'rol': ['asl', 0x20],
'ror': ['asl', 0x60],
'rti': {'a': 0x40},
'rts': {'a': 0x60},
'sbc': ['adc', 0xe0-0x60],
'sta': ['adc', 0x80-0x60, ['a']],
'txs': {'a': 0x9a},
'tsx': {'a': 0xba},
'pha': {'a': 0x48},
'pla': {'a': 0x68},
'php': {'a': 0x08},
'plp': {'a': 0x28},
'stx': {'z': 0x86, 'zy': 0x96, 'abs': 0x8e},
'sty': {'z': 0x84, 'zx': 0x94, 'abs': 0x8c},

# illegal instructions
'las': {'aby': 0xbb},
'lax': {'z': 0xa7, 'ay': 0xb7, 'abs': 0xaf, 'aby': 0xbf, 'zix': 0xa3, 'ziy': 0xb3},
'sax': {'z': 0x87, 'zy': 0x97, 'abs': 0x8f, 'zix': 0x83},
#...add some more!

# commands
'db': {'imm': None, 'z': None},
'dw': {'imm2': None, 'abs': None},
'org': {'abs': None},
'end': {'abs': None},
}

class AsmException(Exception):
    pass

# implement the shorthand opcodes
for key in mnemonics:
    mk = mnemonics[key]
    if type(mk) == list:
        src = mk[0]
        off = mk[1]
        exclude = mk[2] if len(mk) > 2 else []
        mnemonics[key] = dict()
        for mode, srcmc in mnemonics[src].items():
            if mode not in exclude:
                mnemonics[key][mode] = srcmc + off

def linere(s):
    return re.compile('^' + s + '$')

IDENT = "[a-zA-Z_][a-zA-Z_0-9]*"
EXPRESSION = r"[a-zA-Z_0-9\-\+ \(\)&\>\<\^\$/\*]+"
OPZW = "(|(?P<z>.z)|(?P<w>.w))"
RE_LABEL = linere(f"(?P<label>{IDENT}):\s*(\\$(?P<addr>[0-9a-fA-F]+))?")
OPERANDS = "(" + "|".join([
    "",
    r"(?P<a>[aA]?)",
    r"\$(?P<hex2>[0-9a-fA-F]{1,2})",
    r"\$(?P<hex4>[0-9a-fA-F]{3,4})",
    r"#\$(?P<hexl>[0-9a-fA-F]+)",
    r"#(?P<decl>\d+)",
    f"(?P<ident>{IDENT})",
    f"#(?P<identl>{IDENT})",
    f"(?P<expression>{EXPRESSION})",
    f"#(?P<expressionl>{EXPRESSION})",
]) + ")"
RE_CMD = linere(f"(?P<op>{IDENT}){OPZW}\s*{OPERANDS}")
RE_CMD_ABXY = linere(f"(?P<op>{IDENT}){OPZW}\s*{OPERANDS}((?P<abx>,\s?[xX])|(?P<aby>,\s?[yY]))")
RE_CMD_INDIRECT = linere(f"(?P<op>{IDENT}){OPZW}\s*[\\[]{OPERANDS}(?P<inx>,\s?[xX])?(?P<ind>[\\]])(?P<iny>,\s?[yY])?")

expressionGrammar = Grammar(
    """
    expr        = _ bitwise_or _
    bitwise_or  = (bitwise_xor _ "|" _ bitwise_or) / bitwise_xor
    bitwise_xor = (bitwise_and _ "^" _ bitwise_xor) / bitwise_and
    bitwise_and = (lshift _ "&" _ bitwise_and) / lshift
    lshift      = (rshift _ "<<" _ lshift) / rshift
    rshift      = (sum _ ">>" _ rshift) / sum
    sum         = (sub _ "+" _ sum) / sub
    sub         = (term _ "-" _)* term
    term        = (div _ "*" _)* div
    div         = (unary _ "/" _)* unary
    unary       = swap / lo / hi / innermost
    swap        = "><" innermost
    lo          = "<" innermost
    hi          = ">" innermost
    innermost   = number / label / ("(" _ expr _ ")")
    
    label       = ~r"[a-zA-Z_][a-zA-Z_0-9]*"
    number      = dec / ("$" hex)
    dec         = ~r"[0-9]+"
    hex         = ~r"[0-9a-fA-F]+"
    _           = ~"\s*"
    """
)

class Expression():
    def __init__(self, *values, **kwargs):
        self.reducefn = kwargs.get("reduce", lambda x, y: x)
        self.mapfn = kwargs.get("map", lambda x: x)
        self.values = values
        assert len(values) > 0
        
    def evaluable(self, labels):
        return all(map(lambda x : self.evaluable_value(x, labels), self.values))
        
    def evaluable_value(self, value, labels):
        if type(value) == Expression:
            return value.evaluable(labels)
        if type(value) == str:
            return value in labels
        return True
        
    def evaluate(self, labels):
        return reduce(self.reducefn, map(lambda x: self.mapfn(self.evaluate_value(x, labels)), self.values))
        
    def evaluate_value(self, value, labels):
        if type(value) == Expression:
            return value.evaluate(labels)
        if type(value) == str:
            if value not in labels:
                raise AsmException(f"label \"{value}\" referenced in expression, but not defined.")
            return labels[value]
        return value

def flatten(l):
    result = []
    for v in l:
        if type(v) == list:
            result.extend(flatten(v))
        else:
            result.append(v)
    return result

def _(l):
    return list(filter(lambda x: x is not None, flatten(l)))

class ExprVisitor(NodeVisitor):
    def visit_expr(self, node, visited_children):
        visited_children = _(visited_children)
        assert len(visited_children) == 1
        if type(visited_children[0]) != Expression:
            return Expression(visited_children[0])
        return visited_children[0]
        
    def visit_bitwise_or(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x | y)
    
    def visit_bitwise_xor(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x ^ y)
    
    def visit_bitwise_and(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x & y)

    def visit_lshift(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x << y)

    def visit_rshift(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x >> y)
    
    def visit_sum(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x + y)

    def visit_sub(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x - y)
    
    def visit_term(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x * y)
    
    def visit_div(self, node, visited_children):
        return Expression(*_(visited_children), reduce=lambda x, y: x // y)
    
    def visit_lo(self, node, visited_children):
        return Expression(*_(visited_children), map=lambda x: x & 0xff)
    
    def visit_hi(self, node, visited_children):
        return Expression(*_(visited_children), map=lambda x: (x >> 8) & 0xff)
    
    def visit_swap(self, node, visited_children):
        return Expression(*_(visited_children), map=lambda x: ((x & 0xff) << 8) | ((x >> 8) & 0xff))
    
    def visit_label(self, node, vc):
        return node.text
    
    def visit_number(self, node, vc):
        return _(vc)[0]
    
    def visit_dec(self, node, vc):
        return int(node.text)
    
    def visit_hex(self, node, vc):
        return int(node.text, 16)
    
    def generic_visit(self, node, visited_children):
        return _(visited_children)

def parseExpression(src):
    try:
        e = ExprVisitor().visit(expressionGrammar.parse(src))
        
        assert type(e) == Expression
        return e
    except IncompleteParseError as e:
        raise AsmException(f"Unable to parse expression: \"{src}\"")
    except ParseError as e:
        raise AsmException(f"Unable to parse expression: \"{src}\"")

def parseline(line):
    if ';' in line:
        line = line[:line.index(';')]
    line = line.strip()
    if line == "":
        return None, line
    matches = RE_LABEL.match(line)
    if matches:
        if matches.groupdict()["addr"]:
            return ("LABEL", matches.group("label"), int(matches.group("addr"), 16)), line
        return ("LABEL", matches.group("label")), line
    matches = RE_CMD.match(line) or RE_CMD_ABXY.match(line)
    brackets = False
    if not matches:
        matches = RE_CMD_INDIRECT.match(line)
        brackets = True
    if matches:
        op = matches.group("op").lower()
        if op in mnemonics:
            gd = matches.groupdict()
            addrmode = []
            if gd.get("inx", None) and not gd.get("iny", None):
                addrmode = ["INX"]
            elif gd.get("iny", None) and not gd.get("inx", None):
                addrmode = ["INY"]
            elif gd.get("abx", None):
                addrmode = ["ABX"]
            elif gd.get("aby", None):
                addrmode = ["ABY"]
            elif brackets and "ind" in mnemonics[op]:
                addrmode = ["IND"]
            if gd["w"]:
                addrmode += ["W"]
            elif gd["z"]:
                addrmode += ["Z"]
            if gd["a"]:
                return ("OP", op, "A", *addrmode), line
            if gd["hex2"]:
                return ("OP", op, "ADDRZ", int(gd["hex2"], 16), *addrmode), line
            if gd["hex4"]:
                return ("OP", op, "ADDR", int(gd["hex4"], 16), *addrmode), line
            if gd["hexl"]:
                return ("OP", op, "LIT", int(gd["hexl"], 16), *addrmode), line
            if gd["decl"]:
                return ("OP", op, "LIT", int(gd["decl"]), *addrmode), line
            if gd["identl"]:
                return ("OP", op, "IDL", gd["identl"], *addrmode), line
            if gd["ident"]:
                return ("OP", op, "ID", gd["ident"], *addrmode), line
            if gd["expression"]:
                return ("OP", op, "EX", parseExpression(gd["expression"]), *addrmode), line
            if gd["expressionl"]:
                return ("OP", op, "EXL", parseExpression(gd["expressionl"]), *addrmode), line
            return ("OP", op, "A", *addrmode), line
    return ("UNK", line), line

def adjustvariant(variant, xy):
    if variant == "abs" and len(xy) > 0:
        return "ab" + xy
    else:
        return variant + xy

# returns a list of (romaddress, bytes)
def assemble(source):
    outbuffs = []
    outbuff = []
    addr = None
    startaddr = None
    labels = dict()
    for line in source.splitlines():
        parse, line = parseline(line)
        if not parse:
            continue
        elif parse[0] == "LABEL":
            if parse[1] in labels:
                raise AsmException(f"Redefined label \"{parse[1]}\"")
            if len(parse) > 2:
                labels[parse[1]] = parse[2]
            else:
                if addr is None:
                    raise AsmException(f"Label definition for \"{parse[1]},\" but no address defined -- did you forget 'org'?")
                labels[parse[1]] = addr
        elif parse[0] == "OP":
            pmode = parse[2]
            op = parse[1]
            opvmap = mnemonics[op]
            
            if op != "org" and addr is None:
                raise AsmException(f"No address defined here -- did you forget 'org'? Line: {line}")
            
            # get address mode (or None)
            addrmode = None
            for _ac in ["INX", "INY", "IND", "ABX", "ABY"]:
                if _ac in parse:
                    addrmode = _ac
            
            # get address width (or None)
            addrw = None
            for _aw in ["W", "Z"]:
                if _aw in parse:
                    addrw = _aw
            
            # determine instruction variant
            variant = None
            if pmode == "A":
                variant = "a"
                if addrmode or addrw:
                    raise AsmException(f"incompatible addressing mode: {line}")
            elif (pmode == "ADDRZ" and addrw != "W") or (pmode in ["ADDR", "ID", "EX"] and addrw == "Z"):
                variant = "z"
                if addrmode is None:
                    pass
                elif addrmode == "ABX":
                    variant = "zx"
                elif addrmode == "ABY":
                    variant = "zy"
                elif addrmode == "INX":
                    variant = "zix"
                elif addrmode == "INY":
                    variant = "ziy"
                else:
                    raise AsmException(f"incompatible addressing mode: {line}")
            elif pmode in ["ADDR", "ID", "EX"] or (pmode == "ADDRZ" and addrw == "W"):
                variant = "abs"
                if addrw == "z":
                    variant = "z"
                if addrw != "w" and pmode == "ID":
                    ident = parse[3]
                    if ident in labels and labels[ident] < 0x100 and labels[ident] >= 0:
                        variant = "z"
                if addrw != "w" and pmode == "EXPR":
                    expression = parse[3]
                    if expression.evaluable(labels):
                        ev = expression.evaluate(labels)
                        while ev < 0:
                            ev += 0x100
                        if ev < 0x100:
                            variant = "z"
                if addrmode is None:
                    pass
                elif addrmode == "ABX":
                    variant = adjustvariant(variant, "x")
                elif addrmode == "ABY":
                    variant = adjustvariant(variant, "y")
                elif addrmode == "INX":
                    variant = "zix"
                elif addrmode == "INY":
                    variant = "ziy"
                else:
                    raise AsmException(f"incompatible addressing mode: {line}")
            elif pmode in ["LIT", "IDL", "EXL"]:
                variant = "imm2" if "imm2" in opvmap else "imm"
                if addrmode or addrw:
                    raise AsmException(f"incompatible addressing mode: {line}")
            
            if "rel" in opvmap:
                variant = "rel"
                if addrmode or addrw:
                    raise AsmException(f"incompatible addressing mode: {line}")
            
            # replace z with abs and vice versa if missing address mode.
            if variant not in opvmap and variant in ["z", "zx", "zy"]:
                adv = adjustvariant("abs", variant[1:])
                if adv in opvmap:
                    variant = adv
            if variant not in opvmap and variant in ["abs", "abx", "aby"]:
                adv = "z"
                if variant in ["abx", "aby"]:
                    adv += variant[2]
                if adv in opvmap:
                    variant = adv
            
            if variant not in opvmap:
                raise AsmException(f"mnemonic \"{op}\" does not support operand ({variant}): {line}")
            
            # write opcode
            if opvmap[variant] is not None:
                outbuff.append(opvmap[variant])
                addr += 1
            
            # determine operand width
            vwidth = 0
            if variant in ["z", "zx", "zy", "zix", "ziy", "rel", "imm"]:
                vwidth = 1
            elif variant in ["abs", "abx", "aby", "ind", "imm2"]:
                vwidth = 2
                
            # determine operand value:
            value = None
            if pmode in ["LIT", "ADDRZ", "ADDR", "EX", "EXL"]:
                value = parse[3]
            elif pmode == "A":
                value = None
            elif pmode in ["ID", "IDL"]:
                ident = parse[3]
                if ident in labels:
                    value = labels[ident]
                else:
                    value = ident
                
            # write operand
            if op == "org":
                # TODO: banks
                if len(outbuff) > 0:
                    outbuffs.append({"addr": startaddr, "data": outbuff})
                addr = value
                startaddr = addr
                outbuff = []
            elif op == "end":
                if addr > value:
                    raise AsmException(f"exceeded max address: ${addr:04X} > ${value:04X}")
            elif value is None:
                pass
            elif type(value) == Expression:
                addr += vwidth
                outbuff.append({
                    "width": vwidth,
                    "expression": value,
                })
            elif type(value) == str:
                addr += vwidth
                outbuff.append({
                    "width": vwidth,
                    "label": value,
                    "rel": addr if variant == "rel" else 0,
                })
            else:
                assert type(value) == type(0)
                addr += vwidth
                if variant == "rel":
                    value -= addr
                if vwidth == 1:
                    while value < 0:
                        value += 0x100
                    if value >= 0x100:
                        raise AsmException(f"value exceeds 1 byte: {line}")
                    outbuff.append(value)
                else:
                    assert vwidth == 2
                    while value < 0:
                        value += 0x10000
                    if value >= 0x10000:
                        raise AsmException(f"value exceeds 2 bytes: {line}")
                    outbuff.append(value & 0xff)
                    outbuff.append(value >> 8)
            pass
        else:
            raise AsmException("unrecognized: " + parse[1])
    if len(outbuff) > 0:
        outbuffs.append({"addr": startaddr, "data": outbuff})
    
    for outbuff in outbuffs:
        i = -1
        data = outbuff["data"]
        while True:
            i += 1
            if i >= len(data):
                break
            if type(data[i]) == dict:
                # swap out dict for value
                vwidth = data[i]["width"]
                if "expression" in data[i]:
                    value = data[i]["expression"].evaluate(labels)
                    orgvalue = value
                    label = "(expression)"
                else:
                    label = data[i]["label"]
                    rel = data[i]["rel"]
                    if label not in labels:
                        raise AsmException(f"label \"{label}\" referenced but not defined")
                    value = labels[label] - rel
                    orgvalue = labels[label]
                if vwidth == 1:
                    if value < -0x80 and "rel" in data[i] and data[i]["rel"] > 0:
                        raise AsmException(f"relative jump is too negative ({label})")
                    while value < 0:
                        value += 0x100
                    if value >= 0x100:
                        raise AsmException(f"label \"{label}\" at ${orgvalue:02X} is referenced as a zero-page address, but exceeds $FF")
                    data[i:i+1] = [value & 0xff]
                else:
                    while value < 0:
                        value += 0x10000
                    if value >= 0x10000:
                        raise AsmException(f"label \"{label}\" at ${orgvalue:04X} is not addressable")
                    assert vwidth == 2
                    data[i:i+1] = [value & 0xff, value >> 8]
                    i += 1
            else:
                assert data[i] >= 0 and data[i] < 0x100
    return outbuffs