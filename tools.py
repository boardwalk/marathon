import logging
import struct

BYTES_PER_LINE = 32

def dump(data):
  lines = []
  hex_part = ""
  ascii_part = ""
  for i in range(len(data)):
    by = data[i]
    hex_part += "%02X " % by
    ascii_part += chr(by) if by > 31 and by < 127 else "."
    if i % BYTES_PER_LINE + 1 == BYTES_PER_LINE:
      lines.append("%s  %s" % (hex_part, ascii_part))
      hex_part = ""
      ascii_part = ""
  if len(data) % BYTES_PER_LINE != 0:
    padding = BYTES_PER_LINE - len(data) % BYTES_PER_LINE
    hex_part += "   " * padding
    lines.append("%s  %s" % (hex_part, ascii_part))
  return "\n".join(lines)

class RC4:
  def __init__(self, x, y, S):
    self.x = x
    self.y = y
    self.S = bytearray(S)

  @classmethod
  def from_file(cls, path):
    with open(path) as f:
      x, y, S = struct.unpack("II256s", f.read())
      return cls(x, y, S)

  @classmethod
  def from_key(cls, key):
    key = bytearray(key)
    S = bytearray(256)
    for i in range(len(S)):
      S[i] = i
    j = 0
    for i in range(len(S)):
      j = (j + S[i] + key[i % len(key)]) % 256
      S[i], S[j] = S[j], S[i]
    return cls(0, 0, S)

  @classmethod
  def test_one(cls, key, plaintext, ciphertext):
    rc4 = cls.from_key(key)
    data = bytearray(plaintext)
    rc4.crypt(data)
    if data != ciphertext.decode("hex"):
      raise RuntimeError

  @classmethod
  def test(cls):
    cls.test_one("Key", "Plaintext", "BBF316E8D940AF0AD3")
    cls.test_one("Wiki", "pedia", "1021BF0420")
    cls.test_one("Secret", "Attack at dawn", "45A01F645FC35B383552544B9BF5")

  def crypt(self, data, begin = 0, end = -1):
    if end < 0:
      end += len(data) + 1
    for i in range(begin, end):
      data[i] ^= self.get()

  def get(self):
    self.x = (self.x + 1) % 256
    self.y = (self.y + self.S[self.x]) % 256
    self.S[self.x], self.S[self.y] = self.S[self.y], self.S[self.x]
    return self.S[(self.S[self.x] + self.S[self.y]) % 256]

