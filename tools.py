import logging

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

