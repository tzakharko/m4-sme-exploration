import sys
assert sys.version_info >= (3, 10), "Requires Python 3.10 or later"

import collections, yaml
from types import SimpleNamespace
from dataclasses import dataclass
from typing import assert_never, Literal
from contextlib import contextmanager

# SME data types
@dataclass(kw_only=True)
class SMEType:
  label: str
  suffix: str
  kind: str
  size: int
  max_za_tiles: int

def sme_type_from_label(label: str):
  return Types.__dict__[label]

class Types:
  f8 = SMEType(label = "f8",   suffix = "b", kind = "float" , size = 8 ,  max_za_tiles = 1)
  f16 = SMEType(label = "f16", suffix = "h", kind = "float" , size = 16 , max_za_tiles = 2)
  b16 = SMEType(label = "b16", suffix = "h", kind = "bfloat", size = 16 , max_za_tiles = 2)
  f32 = SMEType(label = "f32", suffix = "s", kind = "float" , size = 32 , max_za_tiles = 4)
  f64 = SMEType(label = "f64", suffix = "d", kind = "float" , size = 64 , max_za_tiles = 8)
  i8  = SMEType(label = "i8" , suffix = "b", kind = "int"   , size = 8  , max_za_tiles = 1)
  i16 = SMEType(label = "i16", suffix = "h", kind = "int"   , size = 16 , max_za_tiles = 2)
  i32 = SMEType(label = "i32", suffix = "s", kind = "int"   , size = 32 , max_za_tiles = 4)
  i64 = SMEType(label = "i64", suffix = "d", kind = "int"   , size = 64 , max_za_tiles = 8)
  u8  = SMEType(label = "u8" , suffix = "b", kind = "uint"  , size = 8  , max_za_tiles = 1)
  u16 = SMEType(label = "u16", suffix = "h", kind = "uint"  , size = 16 , max_za_tiles = 2)
  u32 = SMEType(label = "u32", suffix = "s", kind = "uint"  , size = 32 , max_za_tiles = 4)
  u64 = SMEType(label = "u64", suffix = "d", kind = "uint"  , size = 64 , max_za_tiles = 8)

  @staticmethod
  def with_label(label: str) -> SMEType:
    return Types.__dict__[label]

  @classmethod
  def __new__(cls):
    raise Exception("this class cannot be instantiated")

class AsmBlock:
  """ Simple gcc assembly block emitter """
  def __init__(self, width: int = 60):
    self.width = width
    self.lines = []
    self.indent = ""

  def emit(self, opcode: str, *args):
    line = f"{self.indent}{opcode} {", ".join(str(arg) for arg in args if arg is not None)}"
    self.width = max(self.width, len(line))
    self.lines.append(line)

  @contextmanager
  def labeled_block(self, label: int):
    self.emit(f"{label}:")
    indent = self.indent
    self.indent = self.indent + "  "
    yield
    self.indent = indent

  def join(self, first_ident = 0, second_ident = 8):
    lines = ['"' + line.ljust(self.width) + '\\n"' for line in self.lines]

    first = "".ljust(first_ident)
    second = "".ljust(second_ident)

    if len(lines) == 0:
      return first

    out = first + lines[0]
    for line in lines[1:]:
      out = f"{out}\n{second}{line}"

    return out
