import unittest

from um import Um

class TestUmspec(unittest.TestCase):

    def test_bits(self):
        x = int('1101', 2)
        for start, l, expect in (
                (28, 1, 1),
                (28, 2, 3),
                (28, 3, 6),
                (27, 4, 6),
                (27, 5, 13)):
            got = Um.bits(x, start, l)
            self.assertEqual(got, expect,
                             "bits(%x[%u:%u]) = %u, expect %u " %
                             (x, start, l, got, expect))

    def test_encode_decode(self):
        data = (3, 4, 5, 6)
        self.assertEqual(data, Um.decodeInstruction(Um.encodeInstruction(*data)))

    pass

if __name__ == '__main__':
    unittest.main()
