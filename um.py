#!/usr/bin/env python
""" Universal Machine Simulator. See um-spec.txt """
# Note: running with pypy gives something like over a 15 times speedup.
from __future__ import print_function

import os, sys, struct

PYTHON3 = (sys.version_info >= (3, 0))

WORDSIZE = 32
TWO_32 = 1 << WORDSIZE

OP2NAME = [''] * 14
for op, name in enumerate(
    """MOVEIF INDEX STORE ADD MULT DIV NAND HALT ALLOC
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

        # Eight distinct general-purpose registers, capable of holding one
        # platter each.
        # All registers shall be initialized with platters of value '0'.
        self.gpr = [0,] * 8
        self.loadScroll(code)
        self.debug = debug

    def loadScroll(self, code):
        """The machine shall be initialized with a '0' array whose contents
        shall be read from a "program" scroll."""
        self.platter[0] = []
        for c in code:
            self.platter[0].append(c)

    # Not needed for problem but useful in developing and debugging
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
        """Return an int field of w that starts at 'start' and goes for length 'l'"""
        return w >> (WORDSIZE - start - l) & ((1 << l) - 1)

    @staticmethod
    def decodeInstruction(i):
        """Each Standard Operator performs an errand using three registers,
        called A, B, and C. Each register is described by a three bit
        segment of the instruction platter. The register C is described by
        the three least meaningful bits, the register B by the three next
        more meaningful than those, and the register A by the three next
        more meaningful than those.

                                      A     C
                                      |     |
                                      vvv   vvv
              .--------------------------------.
              |VUTSRQPONMLKJIHGFEDCBA9876543210|
              `--------------------------------'
               ^^^^                      ^^^
               |                         |
               operator number           B

              Figure 2. Standard Operators

        One special operator does not describe registers in the same way.
        Instead the three bits immediately less significant than the four
        instruction indicator bits describe a single register A. The
        remainder twenty five bits indicate a value, which is loaded
        forthwith into the register A.

                   A
                   |
                   vvv
              .--------------------------------.
              |VUTSRQPONMLKJIHGFEDCBA9876543210|
              `--------------------------------'
               ^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^
               |      |
               |      value
               |
               operator number

               Figure 3. Special Operators
        """
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
        """In each cycle of the Universal Machine, an Operator shall be
        retrieved from the platter that is indicated by the execution
        finger. ... Before this operator is discharged, the execution
        finger shall be advanced to the next platter, if any.
        """
        assert self.finger < len(self.platter[0]), "Spun off end of program"
        i = self.platter[0][self.finger]
        operator, a, b, c = Um.decodeInstruction(i)
        if self.debug:
            print("%s\t%s" % (Um.disasm1(i, self.finger+1), self.dumpRegs()))

        self.finger += 1
        OPCODE2FN[operator](self, a, b, c)
        return OP2NAME[operator]

    def register(op):
        """Add fn to OPCODE2FN indexed by its opcode"""
        def _decorator(fn):
            OPCODE2FN[op] = fn
            return fn
        return _decorator

    @register(0)
    def conditionalMove(self, a, b, c):
        if self.gpr[c] != 0: self.gpr[a] = self.gpr[b]

    @register(1)
    def arrayIndex(self, a, b, c):
        """The register A receives the value stored at offset
        in register C in the array identified by B."""
        self.gpr[a] = self.platter[self.gpr[b]][self.gpr[c]]

    @register(2)
    def arrayAmendment(self, a, b, c):
        """The array identified by A is amended at the offset
        in register B to store the value in register C."""
        self.platter[self.gpr[a]][self.gpr[b]] = self.gpr[c]

    @register(3)
    def addition(self, a, b, c):
        """The register A receives the value in register B plus
        the value in register C, modulo 2^32."""
        self.gpr[a] = (self.gpr[b] + self.gpr[c]) % TWO_32

    @register(4)
    def multiplication(self, a, b, c):
        """The register A receives the value in register B times
        the value in register C, modulo 2^32."""
        self.gpr[a] = (self.gpr[b] * self.gpr[c]) % TWO_32

    @register(5)
    def division(self, a, b, c):
        """The register A receives the value in register B
        divided by the value in register C, if any, where
        each quantity is treated treated as an unsigned 32
        bit number."""
        # Note vagueness around rounding.
        # We'll let Python's ZeroDivide exception propagate here.
        self.gpr[a] = (self.gpr[b] // self.gpr[c]) % TWO_32

    @register(6)
    def notAnd(self, a, b, c):
        """Each bit in the register A receives the 1 bit if
        either register B or register C has a 0 bit in that
        position.  Otherwise the bit in register A receives
        the 0 bit.
        """
        self.gpr[a] = (~(self.gpr[b] & self.gpr[c])) % TWO_32

    @register(7)
    def halt(self, _dummy1, _dumm2, _dummy3):
        """universal machine stops computation."""
        print("universal machine stops computation.")

    @register(8)
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

    @register(9)
    def abandonment(self, a, b, c):
        """
        The array identified by the register C is abandoned.
        Future allocations may then reuse that identifier.
        """
        del self.platter[self.gpr[c]]

    @register(10)
    def output(self, a, b, c):
        """
        The value in the register C is displayed on the console
        immediately. Only values between and including 0 and 255
        are allowed.
        """
        print(chr(self.gpr[c]), end='')

    @register(11)
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
                elif ord(ch) == 4:  # Ctrl-D
                    raise EOFError
            except EOFError:
                self.gpr[c] = TWO_32 - 1
                break
            print(ch, end="")
            self.gpr[c] = ord(ch)
            break

    @register(12)
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

    @register(13)
    def orthography(self, a, val, _dummy):
        """The value indicated is loaded into the register A
           forthwith."""
        self.gpr[a] = val

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

    @staticmethod
    def encodeInstruction(operator, a, b, c):
        register = (
           '{0:04b}'.format(operator) +
           '0'*19 +
           '{0:03b}'.format(a) +
           '{0:03b}'.format(b) +
           '{0:03b}'.format(c))
        return int(register, 2)

    @staticmethod
    def encodeValue(operator, reg, val):
        register = (
           '{0:04b}'.format(operator) +
           '{0:03b}'.format(reg) +
           '{0:025b}'.format(val))
        return int(register, 2)

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
    with open(path, 'rb') as fp:
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
