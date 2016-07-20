import unittest, inspect

from um import Um, OP2NAME, NAME2OP, OPCODE2FN

class TestUmspec(unittest.TestCase):

    def test_encode_decode(self):
        data = (3, 4, 5, 6)
        self.assertEqual(data, Um.decodeInstruction(Um.encodeInstruction(*data)))

    def test_registered(self):
        fns = set()
        for name, op in NAME2OP.items():
            fn = OPCODE2FN[op]
            self.assertTrue(inspect.isfunction(fn), "OPCODE2FN[%d] should be a fn" % (op,))
            fns.add(fn)
        self.assertEqual(len(fns), len(NAME2OP),
                         "NAME2OP should be fully populated %r" % NAME2OP)

    def test_assemble(self):
        instructions = [['LOAD', 0, 10],
                        ['ADD', 0, 0, 0],
                        ['HALT', 0, 0, 0]]
        code = Um.assemble(instructions)

        for i, c in enumerate(code):
            operator, a, b, c = Um.decodeInstruction(c)
            opname = OP2NAME[operator]
            if opname != 'LOAD':
                self.assertEqual([opname, a, b, c], instructions[i])
            else:
                self.assertEqual([opname, a, b], instructions[i])

    def test_bits(self):
        x = int('1011', 2)
        for start, l, expect in (
                (28, 1, 1),
                (28, 2, 2),
                (28, 3, 5),
                (27, 4, 5),
                (27, 5, 11)):
            got = Um.bits(x, start, l)
            self.assertEqual(got, expect,
                             ("bits(%x[%u:%u]) = %u, expect %u " %
                              (x, start, l, got, expect)))

    def test_nand(self):
        instructions = [['LOAD', 0, 0b1100],
                        ['LOAD', 1, 0b0101],
                        ['NAND', 2, 0, 1],
                        ['HALT', 0, 0, 0]]
        code = Um.assemble(instructions)
        m = Um(code)
        self.assertEqual(m.gpr[2], 0)
        m.simulate()
        self.assertEqual(m.gpr[2], 0xfffffffb, "nand %x vs %x" % (m.gpr[2], 0x1101))


if __name__ == '__main__':
    unittest.main()
