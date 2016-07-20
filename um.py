#!/usr/bin/env python
""" Universal Machine Simulator """
from __future__ import print_function

OP2NAME = [''] * 14
for op, name in enumerate(
      """MOVEIF INDEX ASTORE ADD MULT DIV NAND HALT ALLOC
      FREE OUTPUT INPUT JUMP LOAD""".split()):
   OP2NAME[op] = name
NAME2OP = {name: op for op, name in enumerate(OP2NAME) if name}

class Um():
   """ UM-32 "Universal Machine"""
   def __init__(self, code):
      """The machine shall consist of the following components:
      * An infinite supply of sandstone platters, with room on each
      for thirty-two small marks, which we call "bits."

      * Eight distinct general-purpose registers, capable of holding one
      platter each.

      * A collection of arrays of platters, each referenced by a distinct
      32-bit identifier. One distinguished array is referenced by 0
      and stores the "program." This array will be referred to as the
      '0' array.

      All registers shall be
      initialized with platters of value '0'. The execution finger shall
      point to the first platter of the '0' array, which has offset zero.
      """
      self.platter = {}
      self.platter[0] = []
      self.finger = 0
      self.gpr = [0,] * 8
      self.loadScroll(code)

   def loadScroll(self, code):
      """The machine shall be initialized with a '0' array whose contents
      shall be read from a "program" scroll.
      """
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
         return s + "r%u" % (a, b)
      elif operator < 7:
         return s + "r%u, r%u, r%u" % (a, b, c)
      elif opname in ('OUTPUT', 'INPUT'):
         return s + "r%u" % (c)
      elif opname == 'HALT':
         return s
      else:
         return s + "%u, %u, %u" % (a, b, c)

   @staticmethod
   def bits(w, start, l):
      """Return an int field of w that starts at w and goes for length l"""
      return w >> (31 - start - l + 1) & ((l << l) - 1)

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

   @staticmethod
   def int2b3(i):
      return list('{0:03b}'.format(i))

   @staticmethod
   def b2int(b):
      return reduce(lambda x, y: (int(x) << 1 | int(y)), b)

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
      register[7:] = list('{0:25b}'.format(operator))
      register[29:] = Um.int2b3(val)

if __name__ == '__main__':
   # import cProfile
   # cProfile.run("")
   pass
