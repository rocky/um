#!/usr/bin/env python
""" Universal Machine Simulator """
from __future__ import print_function

import os, sys, struct

TWO_32 = 1 << 32

OP2NAME = [''] * 14
for op, name in enumerate(
    """MOVEIF INDEX ASTORE ADD MULT DIV NAND HALT ALLOC
    FREE OUTPUT INPUT JUMP LOAD""".split()):
    OP2NAME[op] = name

NAME2OP = {name: op for op, name in enumerate(OP2NAME) if name}

OPCODE2FN = [None,] * 14

class Um():
    """ UM-32 "Universal Machine Object; call m.simulate() to run.
    """

    def __init__(self, code, debug=False):
        # Machine has a collection of arrays of platters, each
        # referenced by a distinct 32-bit identifier
        self.platter = {}
        # One distinguished array is referenced by 0
        # and stores the "program." This array will be referred to as the
        # '0' array.
        self.platter[0] = []
        self.finger = 0
        self.nextAlloc = 1 # zero taken above

        # Machine has general-purpose registers
        self.gpr = [0,] * 8
        self.loadScroll(code)
        self.debug = debug

    def loadScroll(self, code):
        """The machine shall be initialized with a '0' array whose contents
        shall be read from a "program" scroll."""
        self.platter[0] = []
        for c in code:
            self.platter[0].append(c)

    @staticmethod
    def disassemble(instructions, offset=0):
        for i, inst in enumerate(instructions[offset:]):
            print(Um.disasm1(inst, i))

    @staticmethod
    def disasm1(inst, i):
        operator, a, b, c = Um.decodeInstruction(inst)
        opname = OP2NAME[operator]
        assert opname in NAME2OP
        s = "%d: %s" % (i, opname)
        if opname == 'LOAD':
            return s + "r%u = %u" % (a, b)
        elif operator < 7:
            return s + "r%u, r%u, r%u" % (a, b, c)
        elif opname in ('OUTPUT', 'INPUT'):
            return s + "r%u" % (c)
        elif opname == 'HALT':
            return s
        elif opname == "JUMP":
            return s + "r%u[r%u]" % (b, c)
        else:
            return s + "%u, %u, %u" % (a, b, c)

    @staticmethod
    def bits(w, start, l):
        """Return an int field of w that starts at w and goes for length l"""
        return w >> (31 - start - l + 1) & ((1 << l) - 1)

    @staticmethod
    def b2int(b):
        return reduce(lambda x, y: (int(x) << 1 | int(y)), b)

    @staticmethod
    def decodeInstruction(i):
        operator = Um.bits(i, 0, 4)
        if operator == NAME2OP['LOAD']:
            a = Um.bits(i, 4, 3)
            b = Um.bits(i, 7, 25)
            return operator, a, b, None
        else:
            a = Um.bits(i, 23, 3)
            b = Um.bits(i, 26, 3)
            c = Um.bits(i, 29, 3)
            return operator, a, b, c

    def simulate(self):
        # tot = 0
        while self.spinCycle() != 'HALT':
            # if (tot % 1200000) == 0:
            #     print(tot, ' ', end='')
            #     self.debug = True
            # else:
            #     self.debug = False
            # tot += 1
            # if tot > 30: break
            pass

    def spinCycle(self):
        assert self.finger < len(self.platter[0]), "Spun off end of program"
        i = self.platter[0][self.finger]
        operator, a, b, c = Um.decodeInstruction(i)
        if self.debug:
            print("%s\t%s" % (Um.disasm1(i, self.finger+1), self.dumpRegs()))

        self.finger += 1
        OPCODE2FN[operator](self, a, b, c)
        return OP2NAME[operator]

    def register(op, fn):
        """Add fn to OPCODE2FN indexed by its opcode"""
        OPCODE2FN[op] = fn

    def conditionalMove(self, a, b, c):
        if self.gpr[c] != 0: self.gpr[a] = self.gpr[b]
    register(0, conditionalMove)

    def arrayIndex(self, a, b, c):
        """The register A receives the value stored at offset
        in register C in the array identified by B."""
        self.gpr[a] = self.platter[self.gpr[b]][self.gpr[c]]
    register(1, arrayIndex)

    def arrayAmendment(self, a, b, c):
        """The array identified by A is amended at the offset
        in register B to store the value in register C."""
        self.platter[self.gpr[a]][self.gpr[b]] = self.gpr[c]

    register(2, arrayAmendment)

    def addition(self, a, b, c):
        """The register A receives the value in register B plus
        the value in register C, modulo 2^32."""
        self.gpr[a] = (self.gpr[b] + self.gpr[c]) % TWO_32
    register(3, addition)

    def multiplication(self, a, b, c):
        """The register A receives the value in register B times
        the value in register C, modulo 2^32."""
        self.gpr[a] = (self.gpr[b] * self.gpr[c]) % TWO_32
    register(4, multiplication)

    def division(self, a, b, c):
        """The register A receives the value in register B
        divided by the value in register C, if any, where
        each quantity is treated treated as an unsigned 32
        bit number."""
        # Note vaguess around rounding.
        # We'll let Python's ZeroDevice exception propagate here.
        self.gpr[a] = (self.gpr[b] // self.gpr[c]) % TWO_32
    register(5, division)

    def notAnd(self, a, b, c):
        """Each bit in the register A receives the 1 bit if
        either register B or register C has a 0 bit in that
        position.  Otherwise the bit in register A receives
        the 0 bit.
        """
        self.gpr[a] = (~(self.gpr[b] & self.gpr[c])) % TWO_32
    register(6, notAnd)

    def halt(self, _dummy1, _dumm2, _dummy3):
        """universal machine stops computation."""
        print("universal machine stops computation.")
    register(7, halt)

    def allocation(self, a, b, c):
        """
         A new array is created with a capacity of platters
        commensurate to the value in the register C. This
        new array is initialized entirely with platters
        holding the value 0. A bit pattern not consisting of
         exclusively the 0 bit, and that identifies no other
         active allocated array, is placed in the B register.
        """
        self.platter[self.nextAlloc] = [0,] * self.gpr[c]
        self.gpr[b] = self.nextAlloc
        self.nextAlloc += 1

    register(8, allocation)

    def abandonment(self, a, b, c):
        """
        The array identified by the register C is abandoned.
        Future allocations may then reuse that identifier.
        """
        del self.platter[self.gpr[c]]
    register(9, abandonment)

    def output(self, a, b, c):
        """
        The value in the register C is displayed on the console
        immediately. Only values between and including 0 and 255
        are allowed.
        """
        print(chr(self.gpr[c]), end='')

    register(10, output)

    def input(self, a, b, c):
        """
        The universal machine waits for input on the console.
        When input arrives, the register C is loaded with the
        input, which must be between and including 0 and 255.
        If the end of input has been signaled, then the
        register C is endowed with a uniform value pattern
        where every place is pregnant with the 1 bit.
        """
        while True:
            try:
                ch = getch()
                if ch == '\r':
                    ch = '\n'
                elif ord(ch) == 04:  # Ctrl-D
                    raise EOFError
            except EOFError:
                self.gpr[c] = TWO_32 - 1
                break
            print(ch, end="")
            self.gpr[c] = ord(ch)
            break

    register(11, input)

    def loadProgram(self, a, b, c):
        """
        The array identified by the B register is duplicated
        and the duplicate shall replace the '0' array,
        regardless of size. The execution finger is placed
        to indicate the platter of this array that is
        described by the offset given in C, where the value
        0 denotes the first platter, 1 the second, et
        cetera.

        The '0' array shall be the most sublime choice for
        loading, and shall be handled with the utmost
        velocity.
        """

        # Optimization: don't need to dup onto yourself
        if self.gpr[b] != 0:
            assert self.gpr[b] in self.platter
            self.platter[0] = list(self.platter[self.gpr[b]])
        self.finger = self.gpr[c]

    register(12, loadProgram)

    def orthography(self, a, val, _dummy):
        """The value indicated is loaded into the register A
           forthwith."""
        self.gpr[a] = val
    register(13, orthography)

    @staticmethod
    def assemble(instructions):
        bin_instructions = []
        for i in instructions:
            opname = i[0]
            assert opname in NAME2OP
            if opname == 'LOAD':
                a, b = i[1:]
                i = Um.encodeValue(NAME2OP['LOAD'], a, b)
            else:
                a, b, c = i[1:]
                i = Um.encodeInstruction(NAME2OP[opname], a, b, c)
            bin_instructions.append(i)
        return bin_instructions

    # FIXME: combine these two
    @staticmethod
    def int2b32(i):
        return list('{0:032b}'.format(i))

    @staticmethod
    def int2b3(i):
        return list('{0:03b}'.format(i))

    @staticmethod
    def encodeInstruction(operator, a, b, c):
        register = [0,] * 32
        register[0:4] = list('{0:04b}'.format(operator))
        register[23:26] = Um.int2b3(a)
        register[26:29] = Um.int2b3(b)
        register[29:] = Um.int2b3(c)
        return Um.b2int(register)

    @staticmethod
    def encodeValue(operator, reg, val):
        register = [0,] * 32
        register[0:4] = list('{0:04b}'.format(operator))
        register[4:7] = Um.int2b3(reg)
        register[7:] = list('{0:025b}'.format(val))
        return Um.b2int(register)

    def dumpRegs(self):
        """Display non-zero registers"""
        return "regs = (%s)" % ", ".join([str(r) for r in self.gpr])

class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

class _GetchWindows:
    def __init__(self):
        import msvcrt
    def __call__(self):
        import msvcrt
        return msvcrt.getch()


getch = _Getch()

def getcode(path):
    size = os.path.getsize(path)
    if size % 4 != 0:
        print("Warning: expecting size of %s a multiple of 4; dropping bytes" %
              size)
    intSize = size // 4
    fmt = "!%uI" % intSize
    with open(path, 'r') as fp:
        ints = fp.read(intSize * 4)
        code = struct.unpack(fmt, ints)
    print("code %s loaded" % path)
    return code

def main(argv):
    if len(argv) != 2:
        print("""usage:
um program-image

Runs simulator for UM with program program-image
""")
        sys.exit(1)
    path = sys.argv[1]
    code = getcode(path)
    m = Um(code, debug=False)
    # import cProfile
    # cProfile.run("m.simulate()")
    m.simulate()

if __name__ == '__main__':
    main(sys.argv)
