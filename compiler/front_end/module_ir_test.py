# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for module_ir."""

from __future__ import print_function

import collections
import pkgutil
import unittest

from compiler.front_end import module_ir
from compiler.front_end import parser
from compiler.front_end import tokenizer
from compiler.util import ir_data
from compiler.util import ir_data_fields
from compiler.util import ir_data_utils
from compiler.util import test_util

_TESTDATA_PATH = "testdata.golden"
_MINIMAL_SOURCE = pkgutil.get_data(
    _TESTDATA_PATH, "span_se_log_file_status.emb"
).decode(encoding="UTF-8")
_MINIMAL_SAMPLE = parser.parse_module(
    tokenizer.tokenize(_MINIMAL_SOURCE, "")[0]
).parse_tree
_MINIMAL_SAMPLE_IR = ir_data_utils.IrDataSerializer.from_json(
    ir_data.Module,
    pkgutil.get_data(_TESTDATA_PATH, "span_se_log_file_status.ir.txt").decode(
        encoding="UTF-8"
    ),
)

# _TEST_CASES contains test cases, separated by '===', that ensure that specific
# results show up in the IR for .embs.
#
# Each test case is of the form:
#
#     name
#     ---
#     .emb text
#     ---
#     (incomplete) IR text format
#
# For each test case, the .emb is parsed into a parse tree, which is fed into
# module_ir.build_ir(), which should successfully return an IR.  The generated
# IR is then compared against the incomplete IR in the test case to ensure that
# the generated IR is a strict superset of the test case IR -- that is, it is OK
# if the generated IR contains fields that are not in the test case, but not if
# the test case contains fields that are not in the generated IR, and not if the
# test case contains fields whose values differ from the generated IR.
#
# Additionally, for each test case, a pass is executed to ensure that the source
# code location for each node in the IR is strictly contained within the source
# location for its parent node.
_TEST_CASES = r"""
prelude
---
external UInt:
  [fixed_size: false]
  [byte_order_dependent: true]

external Byte:
  [size: 1]
  [byte_order_dependent: false]
---
{
  "type": [
    {
      "external": {},
      "name": { "name": { "text": "UInt" } },
      "attribute": [
        {
          "name": { "text": "fixed_size" },
          "value": { "expression": { "boolean_constant": { "value": false } } }
        },
        {
          "name": { "text": "byte_order_dependent" },
          "value": { "expression": { "boolean_constant": { "value": true } } }
        }
      ]
    },
    {
      "external": {},
      "name": { "name": { "text": "Byte" } },
      "attribute": [
        {
          "name": { "text": "size" },
          "value": { "expression": { "constant": { "value": "1" } } }
        },
        {
          "name": { "text": "byte_order_dependent" },
          "value": { "expression": { "boolean_constant": { "value": false } } }
        }
      ]
    }
  ]
}

===
numbers
---
bits Foo:
  0000000000          [+0_000_000_003]   UInt  decimal
  0b00000100          [+0b0000_0111]     UInt  binary
  0b00000000_00001000 [+0b0_00001011]    UInt  binary2
  0b_0_00001100       [+0b_00001111]     UInt  binary3
  0x00000010          [+0x0000_0013]     UInt  hex
  0x00000000_00000014 [+0x0_00000017]    UInt  hex2
  0x_0_00000018       [+0x_0000001b]     UInt  hex3
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "decimal" } },
            "location": {
              "start": { "constant": { "value": "0" } },
              "size": { "constant": { "value": "3" } }
            }
          },
          {
            "name": { "name": { "text": "binary" } },
            "location": {
              "start": { "constant": { "value": "4" } },
              "size": { "constant": { "value": "7" }
              }
            }
          },
          {
            "name": { "name": { "text": "binary2" } },
            "location": {
              "start": { "constant": { "value": "8" } },
              "size": { "constant": { "value": "11" } }
            }
          },
          {
            "name": { "name": { "text": "binary3" } },
            "location": {
              "start": { "constant": { "value": "12" } },
              "size": { "constant": { "value": "15" } }
            }
          },
          {
            "name": { "name": { "text": "hex" } },
            "location": {
              "start": { "constant": { "value": "16" } },
              "size": { "constant": { "value": "19" } }
            }
          },
          {
            "name": { "name": { "text": "hex2" } },
            "location": {
              "start": { "constant": { "value": "20" } },
              "size": { "constant": { "value": "23" } }
            }
          },
          {
            "name": { "name": { "text": "hex3" } },
            "location": {
              "start": { "constant": { "value": "24" } },
              "size": { "constant": { "value": "27" } }
            }
          }
        ]
      }
    }
  ]
}

===
enum
---
enum Kind:
  WIDGET = 0
  SPROCKET = 1
  GEEGAW = 2  # Comment.
  MAX32 = 4294967295
  MAX64 = 9223372036854775807
---
{
  "type": [
    {
      "enumeration": {
        "value": [
          {
            "name": { "name": { "text": "WIDGET" } },
            "value": { "constant": { "value": "0" } }
          },
          {
            "name": { "name": { "text": "SPROCKET" } },
            "value": { "constant": { "value": "1" } }
          },
          {
            "name": { "name": { "text": "GEEGAW" } },
            "value": { "constant": { "value": "2" } }
          },
          {
            "name": { "name": { "text": "MAX32" } },
            "value": { "constant": { "value": "4294967295" } }
          },
          {
            "name": { "name": { "text": "MAX64" } },
            "value": { "constant": { "value": "9223372036854775807" } }
          }
        ]
      },
      "name": { "name": { "text": "Kind" } }
    }
  ]
}

===
struct attribute
---
struct Foo:
  [size: 10]
  0 [+0]  UInt  field
---
{
  "type": [
    {
      "structure": {
        "field": [ { "name": { "name": { "text": "field" } } } ]
      },
      "name": { "name": { "text": "Foo" } },
      "attribute": [
        {
          "name": { "text": "size" },
          "value": { "expression": { "constant": { "value": "10" } } },
          "is_default": false
        }
      ]
    }
  ]
}

===
$default attribute
---
[$default byte_order: "LittleEndian"]
---
{
  "attribute": [
    {
      "name": { "text": "byte_order" },
      "value": { "string_constant": { "text": "LittleEndian" } },
      "is_default": true
    }
  ]
}

===
abbreviations
---
struct Foo:
  0 [+1]  UInt  size (s)
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "size" } },
            "abbreviation": { "text": "s" }
          }
        ]
      }
    }
  ]
}

===
expressions
---
struct Foo:
  0+1 [+2*3]             UInt  plus_times
  4-5 [+(6)]             UInt  minus_paren
  nn [+7*(8+9)]          UInt  name_complex
  10+11+12 [+13*14*15]   UInt  associativity
  16+17*18 [+19*20-21]   UInt  precedence
  -(+1) [+0-(-10)]       UInt  unary_plus_minus
  1 + + 2 [+3 - -4 - 5]  UInt  unary_plus_minus_2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "plus_times" } },
            "location": {
              "start": {
                "function": {
                  "function": "ADDITION",
                  "function_name": { "text": "+" },
                  "args": [
                    { "constant": { "value": "0" } },
                    { "constant": { "value": "1" } }
                  ]
                }
              },
              "size": {
                "function": {
                  "function": "MULTIPLICATION",
                  "function_name": { "text": "*" },
                  "args": [
                    { "constant": { "value": "2" } },
                    { "constant": { "value": "3" } }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "minus_paren" } },
            "location": {
              "start": {
                "function": {
                  "function": "SUBTRACTION",
                  "args": [
                    { "constant": { "value": "4" } },
                    { "constant": { "value": "5" } }
                  ]
                }
              },
              "size": { "constant": { "value": "6" } }
            }
          },
          {
            "name": { "name": { "text": "name_complex" } },
            "location": {
              "start": {
                "field_reference": {
                  "path": [ { "source_name": [ { "text": "nn" } ] } ]
                }
              },
              "size": {
                "function": {
                  "function": "MULTIPLICATION",
                  "args": [
                    { "constant": { "value": "7" } },
                    {
                      "function": {
                        "function": "ADDITION",
                        "args": [
                          { "constant": { "value": "8" } },
                          { "constant": { "value": "9" } }
                        ]
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "associativity" } },
            "location": {
              "start": {
                "function": {
                  "function": "ADDITION",
                  "args": [
                    {
                      "function": {
                        "function": "ADDITION",
                        "args": [
                          { "constant": { "value": "10" } },
                          { "constant": { "value": "11" } }
                        ]
                      }
                    },
                    { "constant": { "value": "12" } }
                  ]
                }
              },
              "size": {
                "function": {
                  "function": "MULTIPLICATION",
                  "args": [
                    {
                      "function": {
                        "function": "MULTIPLICATION",
                        "args": [
                          { "constant": { "value": "13" } },
                          { "constant": { "value": "14" } }
                        ]
                      }
                    },
                    { "constant": { "value": "15" } }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "precedence" } },
            "location": {
              "start": {
                "function": {
                  "function": "ADDITION",
                  "args": [
                    { "constant": { "value": "16" } },
                    {
                      "function": {
                        "function": "MULTIPLICATION",
                        "args": [
                          { "constant": { "value": "17" } },
                          { "constant": { "value": "18" } }
                        ]
                      }
                    }
                  ]
                }
              },
              "size": {
                "function": {
                  "function": "SUBTRACTION",
                  "args": [
                    {
                      "function": {
                        "function": "MULTIPLICATION",
                        "args": [
                          { "constant": { "value": "19" } },
                          { "constant": { "value": "20" } }
                        ]
                      }
                    },
                    { "constant": { "value": "21" } }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "unary_plus_minus" } },
            "location": {
              "start": {
                "function": {
                  "function": "SUBTRACTION",
                  "function_name": {
                    "text": "-",
                    "source_location": {
                      "start": { "line": 8, "column": 3 },
                      "end": { "line": 8, "column": 4 }
                    }
                  },
                  "args": [
                    {
                      "constant": {
                        "value": "0",
                        "source_location": {
                          "start": { "line": 8, "column": 3 },
                          "end": { "line": 8, "column": 3 }
                        }
                      },
                      "source_location": {
                        "start": { "line": 8, "column": 3 },
                        "end": { "line": 8, "column": 3 }
                      }
                    },
                    {
                      "function": {
                        "function": "ADDITION",
                        "function_name": {
                          "text": "+",
                          "source_location": {
                            "start": { "line": 8, "column": 5 },
                            "end": { "line": 8, "column": 6 }
                          }
                        },
                        "args": [
                          {
                            "constant": { "value": "0" },
                            "source_location": {
                              "start": { "line": 8, "column": 5 },
                              "end": { "line": 8, "column": 5 }
                            }
                          },
                          {
                            "constant": { "value": "1" },
                            "source_location": {
                              "start": { "line": 8, "column": 6 },
                              "end": { "line": 8, "column": 7 }
                            }
                          }
                        ]
                      },
                      "source_location": {
                        "start": { "line": 8, "column": 4 },
                        "end": { "line": 8, "column": 8 }
                      }
                    }
                  ]
                }
              },
              "size": {
                "function": {
                  "function": "SUBTRACTION",
                  "function_name": {
                    "text": "-",
                    "source_location": {
                      "start": { "line": 8, "column": 12 },
                      "end": { "line": 8, "column": 13 }
                    }
                  },
                  "args": [
                    {
                      "constant": {
                        "value": "0",
                        "source_location": {
                          "start": { "line": 8, "column": 11 },
                          "end": { "line": 8, "column": 12 }
                        }
                      },
                      "source_location": {
                        "start": { "line": 8, "column": 11 },
                        "end": { "line": 8, "column": 12 }
                      }
                    },
                    {
                      "function": {
                        "function": "SUBTRACTION",
                        "function_name": {
                          "text": "-",
                          "source_location": {
                            "start": { "line": 8, "column": 14 },
                            "end": { "line": 8, "column": 15 }
                          }
                        },
                        "args": [
                          {
                            "constant": { "value": "0" },
                            "source_location": {
                              "start": { "line": 8, "column": 14 },
                              "end": { "line": 8, "column": 14 }
                            }
                          },
                          {
                            "constant": { "value": "10" },
                            "source_location": {
                              "start": { "line": 8, "column": 15 },
                              "end": { "line": 8, "column": 17 }
                            }
                          }
                        ]
                      },
                      "source_location": {
                        "start": { "line": 8, "column": 13 },
                        "end": { "line": 8, "column": 18 }
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "unary_plus_minus_2" } },
            "location": {
              "start": {
                "function": {
                  "function": "ADDITION",
                  "args": [
                    { "constant": { "value": "1" } },
                    {
                      "function": {
                        "function": "ADDITION",
                        "args": [
                          { "constant": { "value": "0" } },
                          { "constant": { "value": "2" } }
                        ]
                      }
                    }
                  ]
                }
              },
              "size": {
                "function": {
                  "function": "SUBTRACTION",
                  "args": [
                    {
                      "function": {
                        "function": "SUBTRACTION",
                        "args": [
                          { "constant": { "value": "3" } },
                          {
                            "function": {
                              "function": "SUBTRACTION",
                              "args": [
                                { "constant": { "value": "0" } },
                                { "constant": { "value": "4" } }
                              ]
                            }
                          }
                        ]
                      }
                    },
                    { "constant": { "value": "5" } }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
auto array size
---
struct TenElementArray:
  0 [+10]  Byte[]  bytes
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "array_type": {
                "base_type": {
                  "atomic_type": {
                    "reference": { "source_name": [ { "text": "Byte" } ] }
                  }
                },
                "automatic": {
                  "source_location": {
                    "start": { "line": 3, "column": 16 },
                    "end": { "line": 3, "column": 18 }
                  }
                }
              }
            },
            "name": { "name": { "text": "bytes" } }
          }
        ]
      }
    }
  ]
}

===
start [+size] ranges
---
struct Foo:
  0 [ + 1 ]  UInt     zero_plus_one
  s [+2]     UInt     s_plus_two
  s [+t]     Byte[t]  s_plus_t
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "zero_plus_one" } },
            "location": {
              "start": {
                "constant": { "value": "0" },
                "source_location": {
                  "start": { "line": 3, "column": 3 },
                  "end": { "line": 3, "column": 4 }
                }
              },
              "size": {
                "constant": { "value": "1" },
                "source_location": {
                  "start": { "line": 3, "column": 9 },
                  "end": { "line": 3, "column": 10 }
                }
              }
            }
          },
          {
            "name": { "name": { "text": "s_plus_two" } },
            "location": {
              "start": {
                "field_reference": {
                  "path": [ { "source_name": [ { "text": "s" } ] } ]
                }
              },
              "size": { "constant": { "value": "2" } }
            }
          },
          {
            "name": { "name": { "text": "s_plus_t" } },
            "location": {
              "start": {
                "field_reference": {
                  "path": [ { "source_name": [ { "text": "s" } ] } ]
                }
              },
              "size": {
                "field_reference": {
                  "path": [ { "source_name": [ { "text": "t" } ] } ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
Using Enum.VALUEs in expressions
---
struct Foo:
  0 [+0+Number.FOUR]  UInt               length_four
  Number.FOUR [+8]    UInt               start_four
  8 [+3*Number.FOUR]  UInt               end_four
  12 [+16]            Byte[Number.FOUR]  array_size_four

enum Number:
  FOUR = 4
  EIGHT = FOUR + Number.FOUR
  SIXTEEN = Number.FOUR * FOUR
  INVALID = Number.NaN.FOUR
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "length_four" } },
            "location": {
              "size": {
                "function": {
                  "function": "ADDITION",
                  "args": [
                    { "constant": { "value": "0" } },
                    {
                      "constant_reference": {
                        "source_name": [
                          { "text": "Number" },
                          { "text": "FOUR" }
                        ]
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "start_four" } },
            "location": {
              "start": {
                "constant_reference": {
                  "source_name": [
                    { "text": "Number" },
                    { "text": "FOUR" }
                  ]
                }
              }
            }
          },
          {
            "name": { "name": { "text": "end_four" } },
            "location": {
              "size": {
                "function": {
                  "function": "MULTIPLICATION",
                  "args": [
                    { "constant": { "value": "3" } },
                    {
                      "constant_reference": {
                        "source_name": [
                          { "text": "Number" },
                          { "text": "FOUR" }
                        ]
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "type": {
              "array_type": {
                "element_count": {
                  "constant_reference": {
                    "source_name": [
                      { "text": "Number" },
                      { "text": "FOUR" }
                    ]
                  }
                }
              }
            },
            "name": { "name": { "text": "array_size_four" } }
          }
        ]
      }
    },
    {
      "enumeration": {
        "value": [
          {
            "name": { "name": { "text": "FOUR" } },
            "value": { "constant": { "value": "4" } }
          },
          {
            "name": { "name": { "text": "EIGHT" } },
            "value": {
              "function": {
                "function": "ADDITION",
                "args": [
                  {
                    "constant_reference": {
                      "source_name": [ { "text": "FOUR" } ]
                    }
                  },
                  {
                    "constant_reference": {
                      "source_name": [
                        { "text": "Number" },
                        { "text": "FOUR" }
                      ]
                    }
                  }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "SIXTEEN" } },
            "value": {
              "function": {
                "function": "MULTIPLICATION",
                "args": [
                  {
                    "constant_reference": {
                      "source_name": [
                        { "text": "Number" },
                        { "text": "FOUR" }
                      ]
                    }
                  },
                  {
                    "constant_reference": {
                      "source_name": [ { "text": "FOUR" } ]
                    }
                  }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "INVALID" } },
            "value": {
              "constant_reference": {
                "source_name": [
                  { "text": "Number" },
                  { "text": "NaN" },
                  { "text": "FOUR" }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
Using Type.constants in expressions
---
struct Foo:
  0 [+Bar.four]  UInt  length_four
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "length_four" } },
            "location": {
              "size": {
                "constant_reference": {
                  "source_name": [ { "text": "Bar" }, { "text": "four" } ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
using Type.Subtype
---
struct Foo:
  0 [+0]  Bar.Baz  bar_baz
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [ { "text": "Bar" }, { "text": "Baz" } ]
                }
              }
            },
            "name": { "name": { "text": "bar_baz" } }
          }
        ]
      }
    }
  ]
}

===
module.Type
---
struct Foo:
  0 [+0]  bar.Baz  bar_baz
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [ { "text": "bar" }, { "text": "Baz" } ]
                }
              }
            },
            "name": { "name": { "text": "bar_baz" } }
          }
        ]
      }
    }
  ]
}

===
module.Type.ENUM_VALUE
---
struct Foo:
  bar.Baz.QUX [+0]  UInt  i
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "i" } },
            "location": {
              "start": {
                "constant_reference": {
                  "source_name": [
                    { "text": "bar" },
                    { "text": "Baz" },
                    { "text": "QUX" }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
field attributes
---
struct Foo:
  0 [+1]  UInt  field  [fixed_size: true]
    [size: 1]
  1 [+2]  UInt  field2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "field"
              }
            },
            "attribute": [
              {
                "name": {
                  "text": "fixed_size"
                },
                "value": {
                  "expression": {
                    "boolean_constant": {
                      "value": true
                    }
                  }
                }
              },
              {
                "name": {
                  "text": "size"
                },
                "value": {
                  "expression": {
                    "constant": {
                      "value": "1"
                    }
                  }
                }
              }
            ]
          },
          {
            "name": {
              "name": {
                "text": "field2"
              }
            }
          }
        ]
      },
      "name": {
        "name": {
          "text": "Foo"
        }
      }
    }
  ]
}

===
enum attribute
---
enum Foo:
  [fixed_size: false]
  NAME = 1
---
{
  "type": [
    {
      "enumeration": {
        "value": [ { "name": { "name": { "text": "NAME" } } } ]
      },
      "name": { "name": { "text": "Foo" } },
      "attribute": [
        {
          "name": { "text": "fixed_size" },
          "value": {
            "expression": { "boolean_constant": { "value": false } }
          }
        }
      ]
    }
  ]
}

===
string attribute
---
[abc: "abc"]
[bs: "abc\\"]
[bsbs: "abc\\\\"]
[nl: "abc\nd"]
[q: "abc\"d"]
[qq: "abc\"\""]
---
{
  "attribute": [
    {
      "name": { "text": "abc" },
      "value": { "string_constant": { "text": "abc" } }
    },
    {
      "name": { "text": "bs" },
      "value": { "string_constant": { "text": "abc\\" } }
    },
    {
      "name": { "text": "bsbs" },
      "value": { "string_constant": { "text": "abc\\\\" } }
    },
    {
      "name": { "text": "nl" },
      "value": { "string_constant": { "text": "abc\nd" } }
    },
    {
      "name": { "text": "q" },
      "value": { "string_constant": { "text": "abc\"d" } }
    },
    {
      "name": { "text": "qq" },
      "value": { "string_constant": { "text": "abc\"\"" } }
    }
  ]
}

===
back-end-specific attribute
---
[(cpp) namespace: "a::b::c"]
---
{
  "attribute": [
    {
      "name": { "text": "namespace" },
      "value": { "string_constant": { "text": "a::b::c" } },
      "back_end": { "text": "cpp" }
    }
  ]
}

===
documentation
---
-- module doc
--
-- module doc 2
struct Foo:
  -- foo doc
  -- foo doc 2
  0 [+1]  UInt  bar  -- bar inline doc
    -- bar continued doc
    -- bar continued doc 2
enum Baz:
  -- baz doc
  -- baz doc 2
  QUX = 1  -- qux inline doc
    -- qux continued doc
    -- qux continued doc 2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "documentation": [
              {
                "text": "bar inline doc"
              },
              {
                "text": "bar continued doc"
              },
              {
                "text": "bar continued doc 2"
              }
            ]
          }
        ]
      },
      "name": {
        "name": {
          "text": "Foo"
        }
      },
      "documentation": [
        {
          "text": "foo doc"
        },
        {
          "text": "foo doc 2"
        }
      ]
    },
    {
      "enumeration": {
        "value": [
          {
            "name": {
              "name": {
                "text": "QUX"
              }
            },
            "documentation": [
              {
                "text": "qux inline doc"
              },
              {
                "text": "qux continued doc"
              },
              {
                "text": "qux continued doc 2"
              }
            ]
          }
        ]
      },
      "name": {
        "name": {
          "text": "Baz"
        }
      },
      "documentation": [
        {
          "text": "baz doc"
        },
        {
          "text": "baz doc 2"
        }
      ]
    }
  ],
  "documentation": [
    {
      "text": "module doc"
    },
    {
      "text": ""
    },
    {
      "text": "module doc 2"
    }
  ]
}

===
inline enum
---
struct Foo:
  0 [+1]  enum  baz_qux_gibble (bqg):
    [q: 5]
    BAR = 1
    FOO = 2
bits Bar:
  0 [+1]  enum  baz_qux_gibble (bqg):
    [q: 5]
    BAR = 1
    FOO = 2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [ { "text": "BazQuxGibble" } ],
                  "is_local_name": true
                }
              }
            },
            "name": { "name": { "text": "baz_qux_gibble" } },
            "abbreviation": { "text": "bqg" },
            "attribute": [
              {
                "name": { "text": "q" },
                "value": { "expression": { "constant": { "value": "5" } } }
              }
            ]
          }
        ]
      },
      "name": { "name": { "text": "Foo" } },
      "subtype": [
        {
          "enumeration": {
            "value": [
              {
                "name": { "name": { "text": "BAR" } },
                "value": { "constant": { "value": "1" } }
              },
              {
                "name": { "name": { "text": "FOO" } },
                "value": { "constant": { "value": "2" } }
              }
            ]
          },
          "name": { "name": { "text": "BazQuxGibble" } }
        }
      ]
    },
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [ { "text": "BazQuxGibble" } ],
                  "is_local_name": true
                }
              }
            },
            "name": { "name": { "text": "baz_qux_gibble" } },
            "abbreviation": { "text": "bqg" },
            "attribute": [
              {
                "name": { "text": "q" },
                "value": { "expression": { "constant": { "value": "5" } } }
              }
            ]
          }
        ]
      },
      "name": { "name": { "text": "Bar" } },
      "subtype": [
        {
          "enumeration": {
            "value": [
              {
                "name": { "name": { "text": "BAR" } },
                "value": { "constant": { "value": "1" } }
              },
              {
                "name": { "name": { "text": "FOO" } },
                "value": { "constant": { "value": "2" } }
              }
            ]
          },
          "name": { "name": { "text": "BazQuxGibble" } }
        }
      ]
    }
  ]
}

===
inline struct
---
struct Foo:
  0 [+1]  struct  baz_qux_gibble (bqg):
    [q: 5]
    0 [+1]  UInt  bar
    1 [+1]  UInt  foo
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [ { "text": "BazQuxGibble" } ],
                  "is_local_name": true
                }
              }
            },
            "name": { "name": { "text": "baz_qux_gibble" } },
            "abbreviation": { "text": "bqg" },
            "attribute": [
              {
                "name": { "text": "q" },
                "value": { "expression": { "constant": { "value": "5" } } }
              }
            ]
          }
        ]
      },
      "name": { "name": { "text": "Foo" } },
      "subtype": [
        {
          "structure": {
            "field": [
              {
                "type": {
                  "atomic_type": {
                    "reference": { "source_name": [ { "text": "UInt" } ] }
                  }
                },
                "name": { "name": { "text": "bar" } }
              },
              {
                "type": {
                  "atomic_type": {
                    "reference": { "source_name": [ { "text": "UInt" } ] }
                  }
                },
                "name": { "name": { "text": "foo" } }
              }
            ]
          },
          "name": { "name": { "text": "BazQuxGibble" } }
        }
      ]
    }
  ]
}

===
inline bits
---
struct Foo:
  0 [+1]  bits  baz_qux_gibble (bqg):
    [q: 5]
    0 [+1]  UInt  bar
    1 [+1]  UInt  foo
bits Bar:
  0 [+8]  bits  baz_qux_gibble (bqg):
    [q: 5]
    0 [+1]  UInt  bar
    1 [+1]  UInt  foo
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [
                    {
                      "text": "BazQuxGibble"
                    }
                  ]
                }
              }
            },
            "name": {
              "name": {
                "text": "baz_qux_gibble"
              }
            },
            "abbreviation": {
              "text": "bqg"
            },
            "attribute": [
              {
                "name": {
                  "text": "q"
                },
                "value": {
                  "expression": {
                    "constant": {
                      "value": "5"
                    }
                  }
                }
              }
            ]
          }
        ]
      },
      "name": {
        "name": {
          "text": "Foo"
        }
      },
      "subtype": [
        {
          "structure": {
            "field": [
              {
                "type": {
                  "atomic_type": {
                    "reference": {
                      "source_name": [
                        {
                          "text": "UInt"
                        }
                      ]
                    }
                  }
                },
                "name": {
                  "name": {
                    "text": "bar"
                  }
                }
              },
              {
                "type": {
                  "atomic_type": {
                    "reference": {
                      "source_name": [
                        {
                          "text": "UInt"
                        }
                      ]
                    }
                  }
                },
                "name": {
                  "name": {
                    "text": "foo"
                  }
                }
              }
            ]
          },
          "name": {
            "name": {
              "text": "BazQuxGibble"
            }
          }
        }
      ]
    },
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": {
                  "source_name": [
                    {
                      "text": "BazQuxGibble"
                    }
                  ]
                }
              }
            },
            "name": {
              "name": {
                "text": "baz_qux_gibble"
              }
            },
            "abbreviation": {
              "text": "bqg"
            },
            "attribute": [
              {
                "name": {
                  "text": "q"
                },
                "value": {
                  "expression": {
                    "constant": {
                      "value": "5"
                    }
                  }
                }
              }
            ]
          }
        ]
      },
      "name": {
        "name": {
          "text": "Bar"
        }
      },
      "subtype": [
        {
          "structure": {
            "field": [
              {
                "type": {
                  "atomic_type": {
                    "reference": {
                      "source_name": [
                        {
                          "text": "UInt"
                        }
                      ]
                    }
                  }
                },
                "name": {
                  "name": {
                    "text": "bar"
                  }
                }
              },
              {
                "type": {
                  "atomic_type": {
                    "reference": {
                      "source_name": [
                        {
                          "text": "UInt"
                        }
                      ]
                    }
                  }
                },
                "name": {
                  "name": {
                    "text": "foo"
                  }
                }
              }
            ]
          },
          "name": {
            "name": {
              "text": "BazQuxGibble"
            }
          }
        }
      ]
    }
  ]
}

===
subfield
---
struct Foo:
  foo.bar [+1]  UInt  x
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "x"
              }
            },
            "location": {
              "start": {
                "field_reference": {
                  "path": [
                    {
                      "source_name": [
                        {
                          "text": "foo"
                        }
                      ]
                    },
                    {
                      "source_name": [
                        {
                          "text": "bar"
                        }
                      ]
                    }
                  ]
                }
              }
            }
          }
        ]
      },
      "name": {
        "name": {
          "text": "Foo"
        }
      }
    }
  ]
}

===
anonymous bits
---
struct Foo:
  0 [+1]  bits:
    31 [+1]    enum  high_bit:
      OFF = 0
      ON  = 1
    0 [+1]     Flag  low_bit
    if false:
      16 [+1]  UInt  mid_high
      15 [+1]  UInt  mid_low
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "is_anonymous": true
            },
            "location": {
              "start": {
                "constant": {
                  "value": "0"
                }
              },
              "size": {
                "constant": {
                  "value": "1"
                }
              }
            }
          }
        ]
      },
      "name": {
        "name": {
          "text": "Foo"
        }
      },
      "subtype": [
        {
          "structure": {
            "field": [
              {
                "name": {
                  "name": {
                    "text": "high_bit"
                  }
                }
              },
              {
                "name": {
                  "name": {
                    "text": "low_bit"
                  }
                }
              },
              {
                "name": {
                  "name": {
                    "text": "mid_high"
                  }
                },
                "existence_condition": {
                  "boolean_constant": {
                    "value": false
                  }
                }
              },
              {
                "name": {
                  "name": {
                    "text": "mid_low"
                  }
                },
                "existence_condition": {
                  "boolean_constant": {
                    "value": false
                  }
                }
              }
            ]
          },
          "name": { "is_anonymous": true }
        },
        {
          "enumeration": {
            "value": [
              {
                "name": { "name": { "text": "OFF" } },
                "value": { "constant": { "value": "0" } }
              },
              {
                "name": { "name": { "text": "ON" } },
                "value": { "constant": { "value": "1" } }
              }
            ]
          },
          "name": { "name": { "text": "HighBit" } }
        }
      ]
    }
  ]
}

===
explicit type size
---
struct Foo:
  0 [+1]  Bar:8  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          { "type": { "size_in_bits": { "constant": { "value": "8" } } } }
        ]
      },
      "name": { "name": { "text": "Foo" } }
    }
  ]
}

===
import
---
import "xyz.emb" as yqf
---
{
  "foreign_import": [
    { "file_name": { "text": "" }, "local_name": { "text": "" } },
    { "file_name": { "text": "xyz.emb" }, "local_name": { "text": "yqf" } }
  ]
}

===
empty file
---
---
{
  "foreign_import": [
    {
      "file_name": {
        "text": "",
        "source_location": {
          "start": { "line": 1, "column": 1 },
          "end": { "line": 1, "column": 1 }
        }
      },
      "local_name": {
        "text": "",
        "source_location": {
          "start": { "line": 1, "column": 1 },
          "end": { "line": 1, "column": 1 }
        }
      },
      "source_location": {
        "start": { "line": 1, "column": 1 },
        "end": { "line": 1, "column": 1 }
      }
    }
  ],
  "source_location": {
    "start": { "line": 1, "column": 1 },
    "end": { "line": 1, "column": 1 }
  }
}

===
existence_condition on unconditional field
---
struct Foo:
  0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "bar" } },
            "existence_condition": { "boolean_constant": { "value": true } }
          }
        ]
      }
    }
  ]
}

===
conditional struct fields
---
struct Foo:
  if true == false:
    0 [+1]  UInt  bar
    1 [+1]  bits:
      0 [+1]  UInt  xx
      1 [+1]  UInt  yy
    2 [+1]  enum  baz:
      XX = 1
      YY = 2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "bar" } },
            "existence_condition": {
              "function": {
                "function": "EQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          },
          {
            "existence_condition": {
              "function": {
                "function": "EQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "baz" } },
            "existence_condition": {
              "function": {
                "function": "EQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          }
        ]
      },
      "subtype": [
        {
          "structure": {
            "field": [
              {
                "name": { "name": { "text": "xx" } },
                "existence_condition": { "boolean_constant": { "value": true } }
              }
            ]
          }
        }
      ]
    }
  ]
}

===
negative condition
---
struct Foo:
  if true != false:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "bar" } },
            "existence_condition": {
              "function": {
                "function": "INEQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional bits fields
---
bits Foo:
  if true == false:
    0 [+1]  UInt  bar
    1 [+1]  enum  baz:
      XX = 1
      YY = 2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "bar" } },
            "existence_condition": {
              "function": {
                "function": "EQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "baz" } },
            "existence_condition": {
              "function": {
                "function": "EQUALITY",
                "args": [
                  { "boolean_constant": { "value": true } },
                  { "boolean_constant": { "value": false } }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with logical and
---
struct Foo:
  if true && false:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "boolean_constant": {
                      "value": true
                    }
                  },
                  {
                    "boolean_constant": {
                      "value": false
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with logical or
---
struct Foo:
  if true || false:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "OR",
                "args": [
                  {
                    "boolean_constant": {
                      "value": true
                    }
                  },
                  {
                    "boolean_constant": {
                      "value": false
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with multiple logical ands
---
struct Foo:
  if true && false && true:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "AND",
                      "args": [
                        {
                          "boolean_constant": {
                            "value": true
                          }
                        },
                        {
                          "boolean_constant": {
                            "value": false
                          }
                        }
                      ]
                    }
                  },
                  {
                    "boolean_constant": {
                      "value": true
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with multiple logical ors
---
struct Foo:
  if true || false || true:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "OR",
                "args": [
                  {
                    "function": {
                      "function": "OR",
                      "args": [
                        {
                          "boolean_constant": {
                            "value": true
                          }
                        },
                        {
                          "boolean_constant": {
                            "value": false
                          }
                        }
                      ]
                    }
                  },
                  {
                    "boolean_constant": {
                      "value": true
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with comparisons and logical or
---
struct Foo:
  if 5 == 6 || 6 == 6:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "OR",
                "args": [
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "5"
                          }
                        },
                        {
                          "constant": {
                            "value": "6"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "6"
                          }
                        },
                        {
                          "constant": {
                            "value": "6"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
conditional with or-of-ands
---
struct Foo:
  if true || (false && true):
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "OR",
                "args": [
                  {
                    "boolean_constant": {
                      "value": true
                    }
                  },
                  {
                    "function": {
                      "function": "AND",
                      "args": [
                        {
                          "boolean_constant": {
                            "value": false
                          }
                        },
                        {
                          "boolean_constant": {
                            "value": true
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
less-than comparison
---
struct Foo:
  if 1 < 2:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "LESS",
                "args": [
                  {
                    "constant": {
                      "value": "1"
                    }
                  },
                  {
                    "constant": {
                      "value": "2"
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
less-than-or-equal comparison
---
struct Foo:
  if 1 <= 2:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "LESS_OR_EQUAL",
                "args": [
                  {
                    "constant": {
                      "value": "1"
                    }
                  },
                  {
                    "constant": {
                      "value": "2"
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
greater-than comparison
---
struct Foo:
  if 1 > 2:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "GREATER",
                "args": [
                  {
                    "constant": {
                      "value": "1"
                    }
                  },
                  {
                    "constant": {
                      "value": "2"
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
greater-than-or-equal comparison
---
struct Foo:
  if 1 >= 2:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "GREATER_OR_EQUAL",
                "args": [
                  {
                    "constant": {
                      "value": "1"
                    }
                  },
                  {
                    "constant": {
                      "value": "2"
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained less-than comparison
---
struct Foo:
  if 1 < 2 < 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "LESS",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "LESS",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained greater-than comparison
---
struct Foo:
  if 1 > 2 > 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "GREATER",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "GREATER",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
longer chained less-than comparison
---
struct Foo:
  if 1 < 2 < 3 <= 4:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "AND",
                      "args": [
                        {
                          "function": {
                            "function": "LESS",
                            "args": [
                              {
                                "constant": {
                                  "value": "1"
                                }
                              },
                              {
                                "constant": {
                                  "value": "2"
                                }
                              }
                            ]
                          }
                        },
                        {
                          "function": {
                            "function": "LESS",
                            "args": [
                              {
                                "constant": {
                                  "value": "2"
                                }
                              },
                              {
                                "constant": {
                                  "value": "3"
                                }
                              }
                            ]
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "LESS_OR_EQUAL",
                      "args": [
                        {
                          "constant": {
                            "value": "3"
                          }
                        },
                        {
                          "constant": {
                            "value": "4"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
longer chained greater-than comparison
---
struct Foo:
  if 1 > 2 > 3 >= 4:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "AND",
                      "args": [
                        {
                          "function": {
                            "function": "GREATER",
                            "args": [
                              {
                                "constant": {
                                  "value": "1"
                                }
                              },
                              {
                                "constant": {
                                  "value": "2"
                                }
                              }
                            ]
                          }
                        },
                        {
                          "function": {
                            "function": "GREATER",
                            "args": [
                              {
                                "constant": {
                                  "value": "2"
                                }
                              },
                              {
                                "constant": {
                                  "value": "3"
                                }
                              }
                            ]
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "GREATER_OR_EQUAL",
                      "args": [
                        {
                          "constant": {
                            "value": "3"
                          }
                        },
                        {
                          "constant": {
                            "value": "4"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained less-than and equal comparison
---
struct Foo:
  if 1 < 2 == 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "LESS",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained greater-than and equal comparison
---
struct Foo:
  if 1 > 2 == 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "GREATER",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained equal and less-than comparison
---
struct Foo:
  if 1 == 2 < 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "LESS",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained equal and greater-than comparison
---
struct Foo:
  if 1 == 2 > 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "GREATER",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
chained equality comparison
---
struct Foo:
  if 1 == 2 == 3:
    0 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "existence_condition": {
              "function": {
                "function": "AND",
                "args": [
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "1"
                          }
                        },
                        {
                          "constant": {
                            "value": "2"
                          }
                        }
                      ]
                    }
                  },
                  {
                    "function": {
                      "function": "EQUALITY",
                      "args": [
                        {
                          "constant": {
                            "value": "2"
                          }
                        },
                        {
                          "constant": {
                            "value": "3"
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
choice operator
---
struct Foo:
  true ? 0 : 1 [+1]  UInt  bar
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "bar"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "CHOICE",
                  "args": [
                    {
                      "boolean_constant": {
                        "value": true
                      }
                    },
                    {
                      "constant": {
                        "value": "0"
                      }
                    },
                    {
                      "constant": {
                        "value": "1"
                      }
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
max function
---
struct Foo:
  $max()               [+1]  UInt  no_arg
  $max(0)              [+1]  UInt  one_arg
  $max(2 * 3)          [+1]  UInt  mul_arg
  $max(2, 3)           [+1]  UInt  two_arg
  $max(2, 3, 4, 5, 6)  [+1]  UInt  five_arg
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "no_arg"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "MAXIMUM"
                }
              }
            }
          },
          {
            "name": {
              "name": {
                "text": "one_arg"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "MAXIMUM",
                  "args": [
                    {
                      "constant": {
                        "value": "0"
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": {
              "name": {
                "text": "mul_arg"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "MAXIMUM",
                  "args": [
                    {
                      "function": {
                        "function": "MULTIPLICATION",
                        "args": [
                          {
                            "constant": {
                              "value": "2"
                            }
                          },
                          {
                            "constant": {
                              "value": "3"
                            }
                          }
                        ]
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": {
              "name": {
                "text": "two_arg"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "MAXIMUM",
                  "args": [
                    {
                      "constant": {
                        "value": "2"
                      }
                    },
                    {
                      "constant": {
                        "value": "3"
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "name": {
              "name": {
                "text": "five_arg"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "MAXIMUM",
                  "args": [
                    {
                      "constant": {
                        "value": "2"
                      }
                    },
                    {
                      "constant": {
                        "value": "3"
                      }
                    },
                    {
                      "constant": {
                        "value": "4"
                      }
                    },
                    {
                      "constant": {
                        "value": "5"
                      }
                    },
                    {
                      "constant": {
                        "value": "6"
                      }
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
has function
---
struct Foo:
  if $present(x):
    0 [+1]  UInt  field
  if $present(x.y.z):
    0 [+1]  UInt  field2
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "field"
              }
            },
            "existence_condition": {
              "function": {
                "function": "PRESENCE",
                "args": [
                  {
                    "field_reference": {
                      "path": [
                        {
                          "source_name": [
                            {
                              "text": "x"
                            }
                          ]
                        }
                      ]
                    }
                  }
                ]
              }
            }
          },
          {
            "name": {
              "name": {
                "text": "field2"
              }
            },
            "existence_condition": {
              "function": {
                "function": "PRESENCE",
                "args": [
                  {
                    "field_reference": {
                      "path": [
                        {
                          "source_name": [
                            {
                              "text": "x"
                            }
                          ]
                        },
                        {
                          "source_name": [
                            {
                              "text": "y"
                            }
                          ]
                        },
                        {
                          "source_name": [
                            {
                              "text": "z"
                            }
                          ]
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
upper_bound function
---
struct Foo:
  $upper_bound(0)    [+1]  UInt  one
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "one"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "UPPER_BOUND",
                  "args": [
                    {
                      "constant": {
                        "value": "0"
                      }
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
lower_bound function
---
struct Foo:
  $lower_bound(0)    [+1]  UInt  one
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": {
              "name": {
                "text": "one"
              }
            },
            "location": {
              "start": {
                "function": {
                  "function": "LOWER_BOUND",
                  "args": [
                    {
                      "constant": {
                        "value": "0"
                      }
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    }
  ]
}

===
struct addressable_unit
---
struct Foo:
  0 [+1]  UInt  size
---
{ "type": [ { "structure": {}, "addressable_unit": "BYTE" } ] }

===
bits addressable_unit
---
bits Foo:
  0 [+1]  UInt  size
---
{ "type": [ { "structure": {}, "addressable_unit": "BIT" } ] }

===
enum addressable_unit
---
enum Foo:
  BAR = 0
---
{ "type": [ { "enumeration": {}, "addressable_unit": "BIT" } ] }

===
type size source_location
---
struct Foo:
  0 [+4]  UInt:32  field
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": { "source_name": [ { "text": "UInt" } ] }
              },
              "size_in_bits": {
                "source_location": {
                  "start": { "line": 3, "column": 15 },
                  "end": { "line": 3, "column": 18 }
                }
              },
              "source_location": {
                "start": { "line": 3, "column": 11 },
                "end": { "line": 3, "column": 18 }
              }
            },
            "name": { "name": { "text": "field" } }
          }
        ]
      }
    }
  ]
}

===
builtin references
---
external Foo:
  [requires: $is_statically_sized && $static_size_in_bits == 64]
---
{
  "type": [
    {
      "external": {},
      "attribute": [
        {
          "name": { "text": "requires" },
          "value": {
            "expression": {
              "function": {
                "args": [
                  {
                    "builtin_reference": {
                      "canonical_name": {
                        "module_file": "",
                        "object_path": [ "$is_statically_sized" ]
                      },
                      "source_name": [ { "text": "$is_statically_sized" } ]
                    }
                  },
                  {
                    "function": {
                      "args": [
                        {
                          "builtin_reference": {
                            "canonical_name": {
                              "module_file": "",
                              "object_path": [ "$static_size_in_bits" ]
                            },
                            "source_name": [
                              { "text": "$static_size_in_bits" }
                            ]
                          }
                        }
                      ]
                    }
                  }
                ]
              }
            }
          }
        }
      ]
    }
  ]
}

===
$next
---
struct Foo:
  $next [+0]  UInt  x
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "location": {
              "start": {
                "builtin_reference": { "source_name": [ { "text": "$next" } ] }
              }
            },
            "name": { "name": { "text": "x" } }
          }
        ]
      }
    }
  ]
}

===
virtual fields
---
struct Foo:
  let x = 10
bits Bar:
  let y = 100
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "x" } },
            "read_transform": { "constant": { "value": "10" } }
          }
        ]
      }
    },
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "y" } },
            "read_transform": { "constant": { "value": "100" } }
          }
        ]
      }
    }
  ]
}

===
builtin fields
---
struct Foo:
  let x = $size_in_bytes
  let y = $max_size_in_bytes
  let z = $min_size_in_bytes
bits Bar:
  let x = $size_in_bits
  let y = $max_size_in_bits
  let z = $min_size_in_bits
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "x" } },
            "read_transform": {
              "field_reference": {
                "path": [ { "source_name": [ { "text": "$size_in_bytes" } ] } ]
              }
            }
          },
          {
            "name": { "name": { "text": "y" } },
            "read_transform": {
              "field_reference": {
                "path": [
                  { "source_name": [ { "text": "$max_size_in_bytes" } ] }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "z" } },
            "read_transform": {
              "field_reference": {
                "path": [
                  { "source_name": [ { "text": "$min_size_in_bytes" } ] }
                ]
              }
            }
          }
        ]
      }
    },
    {
      "structure": {
        "field": [
          {
            "name": { "name": { "text": "x" } },
            "read_transform": {
              "field_reference": {
                "path": [ { "source_name": [ { "text": "$size_in_bits" } ] } ]
              }
            }
          },
          {
            "name": { "name": { "text": "y" } },
            "read_transform": {
              "field_reference": {
                "path": [
                  { "source_name": [ { "text": "$max_size_in_bits" } ] }
                ]
              }
            }
          },
          {
            "name": { "name": { "text": "z" } },
            "read_transform": {
              "field_reference": {
                "path": [
                  { "source_name": [ { "text": "$min_size_in_bits" } ] }
                ]
              }
            }
          }
        ]
      }
    }
  ]
}

===
parameterized type definitions
---
struct Foo(a: Flag, b: UInt:32):
  let x = 10
bits Bar(c: UInt:16):
  let y = 100
struct Baz():
  let x = 10
---
{
  "type": [
    {
      "runtime_parameter": [
        {
          "name": { "name": { "text": "a" } },
          "physical_type_alias": {
            "atomic_type": {
              "reference": { "source_name": [ { "text": "Flag" } ] }
            }
          }
        },
        {
          "name": { "name": { "text": "b" } },
          "physical_type_alias": {
            "atomic_type": {
              "reference": { "source_name": [ { "text": "UInt" } ] }
            },
            "size_in_bits": { "constant": { "value": "32" } }
          }
        }
      ]
    },
    {
      "runtime_parameter": [
        {
          "name": { "name": { "text": "c" } },
          "physical_type_alias": {
            "atomic_type": {
              "reference": { "source_name": [ { "text": "UInt" } ] }
            },
            "size_in_bits": { "constant": { "value": "16" } }
          }
        }
      ]
    },
    {}
  ]
}

===
parameterized type usages
---
struct Foo:
  0 [+1]  Two(1, 2)  two
  1 [+1]  One(3)     one
  2 [+1]  Zero()     zero
---
{
  "type": [
    {
      "structure": {
        "field": [
          {
            "type": {
              "atomic_type": {
                "reference": { "source_name": [ { "text": "Two" } ] },
                "runtime_parameter": [
                  { "constant": { "value": "1" } },
                  { "constant": { "value": "2" } }
                ]
              }
            },
            "name": { "name": { "text": "two" } }
          },
          {
            "type": {
              "atomic_type": {
                "reference": { "source_name": [ { "text": "One" } ] },
                "runtime_parameter": [ { "constant": { "value": "3" } } ]
              }
            },
            "name": { "name": { "text": "one" } }
          },
          {
            "type": {
              "atomic_type": {
                "reference": { "source_name": [ { "text": "Zero" } ] }
              }
            },
            "name": { "name": { "text": "zero" } }
          }
        ]
      }
    }
  ]
}

===
enum value attribute
---
enum Foo:
  BAR     = 1 [test: 0]
  BAZ     = 2
    [test: 1]
    [different: "test"]
  FOO_BAR = 4
    -- foo bar doc
    [test: 2]
  FOO_BAZ = 8 [test: 3] -- foo baz doc
  BAR_FOO = 16 [test: 4]
    -- bar foo doc
  BAZ_FOO = 32 -- baz foo doc
    [test: 5]
---
{
  "type": [
    {
      "enumeration": {
        "value": [
          {
            "name": { "name": { "text": "BAR" } },
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "0" } } }
              }
            ]
          },
          {
            "name": { "name": { "text": "BAZ" } },
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "1" } } }
              },
              {
                "name": { "text": "different" },
                "value": { "string_constant": { "text": "test" } }
              }
            ]
          },
          {
            "name": { "name": { "text": "FOO_BAR" } },
            "documentation": [ { "text": "foo bar doc" } ],
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "2" } } }
              }
            ]
          },
          {
            "name": { "name": { "text": "FOO_BAZ" } },
            "documentation": [ { "text": "foo baz doc" } ],
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "3" } } }
              }
            ]
          },
          {
            "name": { "name": { "text": "BAR_FOO" } },
            "documentation": [ { "text": "bar foo doc" } ],
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "4" } } }
              }
            ]
          },
          {
            "name": { "name": { "text": "BAZ_FOO" } },
            "documentation": [ { "text": "baz foo doc" } ],
            "attribute": [
              {
                "name": { "text": "test" },
                "value": { "expression": { "constant": { "value": "5" } } }
              }
            ]
          }
        ]
      },
      "name": { "name": { "text": "Foo" } }
    }
  ]
}

"""


# For each test in _NEGATIVE_TEST_CASES, parsing should fail, and the failure
# should indicate the specified token.
_NEGATIVE_TEST_CASES = """
anonymous bits does not allow documentation
---
-- doc
---
struct Foo:
  0 [+1]  bits:
    -- doc
    0 [+2]  UInt  bar
===
anonymous bits does not allow subtypes
---
enum
---
struct Foo:
  0 [+1]  bits:
    enum Bar:
      X = 1
    0 [+2]  Bar  bar
"""


def _get_test_cases():
    test_case = collections.namedtuple("test_case", ["name", "parse_tree", "ir"])
    result = []
    for case in _TEST_CASES.split("==="):
        name, emb, ir_text = case.split("---")
        name = name.strip()
        try:
            ir = ir_data_utils.IrDataSerializer.from_json(ir_data.Module, ir_text)
        except Exception:
            print(name)
            raise
        parse_result = parser.parse_module(tokenizer.tokenize(emb, "")[0])
        assert not parse_result.error, "{}:\n{}".format(name, parse_result.error)
        result.append(test_case(name, parse_result.parse_tree, ir))
    return result


def _get_negative_test_cases():
    test_case = collections.namedtuple("test_case", ["name", "text", "error_token"])
    result = []
    for case in _NEGATIVE_TEST_CASES.split("==="):
        name, error_token, text = case.split("---")
        name = name.strip()
        error_token = error_token.strip()
        result.append(test_case(name, text, error_token))
    return result


def _check_source_location(source_location, path, min_start, max_end):
    """Performs sanity checks on a source_location field.

    Arguments:
      source_location: The source_location to check.
      path: The path, to use in error messages.
      min_start: A minimum value for source_location.start, or None.
      max_end: A maximum value for source_location.end, or None.

    Returns:
      A list of error messages, or an empty list if no errors.
    """
    if source_location.is_disjoint_from_parent:
        # If source_location.is_disjoint_from_parent, then this source_location is
        # allowed to be outside of the parent's source_location.
        return []

    result = []
    start = None
    end = None
    if not source_location.HasField("start"):
        result.append("{}.start missing".format(path))
    else:
        start = source_location.start
    if not source_location.HasField("end"):
        result.append("{}.end missing".format(path))
    else:
        end = source_location.end

    if start and end:
        if start.HasField("line") and end.HasField("line"):
            if start.line > end.line:
                result.append(
                    "{}.start.line > {}.end.line ({} vs {})".format(
                        path, path, start.line, end.line
                    )
                )
            elif start.line == end.line:
                if (
                    start.HasField("column")
                    and end.HasField("column")
                    and start.column > end.column
                ):
                    result.append(
                        "{}.start.column > {}.end.column ({} vs {})".format(
                            path, path, start.column, end.column
                        )
                    )

    for name, field in (("start", start), ("end", end)):
        if not field:
            continue
        if field.HasField("line"):
            if field.line <= 0:
                result.append("{}.{}.line <= 0 ({})".format(path, name, field.line))
        else:
            result.append("{}.{}.line missing".format(path, name))
        if field.HasField("column"):
            if field.column <= 0:
                result.append("{}.{}.column <= 0 ({})".format(path, name, field.column))
        else:
            result.append("{}.{}.column missing".format(path, name))

    if min_start and start:
        if min_start.line > start.line or (
            min_start.line == start.line and min_start.column > start.column
        ):
            result.append("{}.start before parent start".format(path))

    if max_end and end:
        if max_end.line < end.line or (
            max_end.line == end.line and max_end.column < end.column
        ):
            result.append("{}.end after parent end".format(path))

    return result


def _check_all_source_locations(proto, path="", min_start=None, max_end=None):
    """Performs sanity checks on all source_locations in proto.

    Arguments:
      proto: The proto to recursively check.
      path: The path, to use in error messages.
      min_start: A minimum value for source_location.start, or None.
      max_end: A maximum value for source_location.end, or None.

    Returns:
      A list of error messages, or an empty list if no errors.
    """
    if path:
        path += "."

    errors = []

    child_start = None
    child_end = None
    # Only check the source_location value if this proto message actually has a
    # source_location field.
    if proto.HasField("source_location"):
        errors.extend(
            _check_source_location(
                proto.source_location, path + "source_location", min_start, max_end
            )
        )
        child_start = proto.source_location.start
        child_end = proto.source_location.end

    for name, spec in ir_data_fields.field_specs(proto).items():
        if name == "source_location":
            continue
        if not proto.HasField(name):
            continue
        field_path = "{}{}".format(path, name)
        if spec.is_dataclass:
            if spec.is_sequence:
                index = 0
                for i in getattr(proto, name):
                    item_path = "{}[{}]".format(field_path, index)
                    index += 1
                    errors.extend(
                        _check_all_source_locations(
                            i, item_path, child_start, child_end
                        )
                    )
            else:
                errors.extend(
                    _check_all_source_locations(
                        getattr(proto, name), field_path, child_start, child_end
                    )
                )

    return errors


class ModuleIrTest(unittest.TestCase):
    """Tests the module_ir.build_ir() function."""

    def test_build_ir(self):
        ir = module_ir.build_ir(_MINIMAL_SAMPLE)
        ir.source_text = _MINIMAL_SOURCE
        self.assertEqual(ir, _MINIMAL_SAMPLE_IR)

    def test_production_coverage(self):
        """Checks that all grammar productions are used somewhere in tests."""
        used_productions = set()
        module_ir.build_ir(_MINIMAL_SAMPLE, used_productions)
        for test in _get_test_cases():
            module_ir.build_ir(test.parse_tree, used_productions)
        self.assertEqual(set(module_ir.PRODUCTIONS) - used_productions, set([]))

    def test_double_negative_non_compilation(self):
        """Checks that unparenthesized double unary minus/plus is a parse error."""
        for example in ("[x: - -3]", "[x: + -3]", "[x: - +3]", "[x: + +3]"):
            parse_result = parser.parse_module(tokenizer.tokenize(example, "")[0])
            self.assertTrue(parse_result.error)
            self.assertEqual(7, parse_result.error.token.source_location.start.column)
        for example in ("[x:-(-3)]", "[x:+(-3)]", "[x:-(+3)]", "[x:+(+3)]"):
            parse_result = parser.parse_module(tokenizer.tokenize(example, "")[0])
            self.assertFalse(parse_result.error)


def _make_superset_tests():

    def _make_superset_test(test):

        def test_case(self):
            ir = module_ir.build_ir(test.parse_tree)
            is_superset, error_message = test_util.proto_is_superset(ir, test.ir)

            self.assertTrue(
                is_superset,
                error_message
                + "\n"
                + ir_data_utils.IrDataSerializer(ir).to_json(indent=2)
                + "\n"
                + ir_data_utils.IrDataSerializer(test.ir).to_json(indent=2),
            )

        return test_case

    for test in _get_test_cases():
        test_name = "test " + test.name + " proto superset"
        assert not hasattr(ModuleIrTest, test_name)
        setattr(ModuleIrTest, test_name, _make_superset_test(test))


def _make_source_location_tests():

    def _make_source_location_test(test):

        def test_case(self):
            error_list = _check_all_source_locations(
                module_ir.build_ir(test.parse_tree)
            )
            self.assertFalse(error_list, "\n".join([test.name] + error_list))

        return test_case

    for test in _get_test_cases():
        test_name = "test " + test.name + " source location"
        assert not hasattr(ModuleIrTest, test_name)
        setattr(ModuleIrTest, test_name, _make_source_location_test(test))


def _make_negative_tests():

    def _make_negative_test(test):

        def test_case(self):
            parse_result = parser.parse_module(tokenizer.tokenize(test.text, "")[0])
            self.assertEqual(test.error_token, parse_result.error.token.text.strip())

        return test_case

    for test in _get_negative_test_cases():
        test_name = "test " + test.name + " compilation failure"
        assert not hasattr(ModuleIrTest, test_name)
        setattr(ModuleIrTest, test_name, _make_negative_test(test))


_make_negative_tests()
_make_superset_tests()
_make_source_location_tests()


if __name__ == "__main__":
    unittest.main()
