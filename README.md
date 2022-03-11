# Emboss

Emboss is a tool for generating code that reads and writes binary data
structures.  It is designed to help write code that communicates with hardware
devices such as GPS receivers, LIDAR scanners, or actuators.

## What does Emboss *do*?

Emboss takes specifications of binary data structures, and produces code that
will efficiently and safely read and write those structures.

Currently, Emboss only generates C++ code, but the compiler is structured so
that writing new back ends is relatively easy -- contact emboss-dev@google.com
if you think Emboss would be useful, but your project uses a different language.


## When should I use Emboss?

If you're sitting down with a manual that looks something like
[this](https://hexagondownloads.blob.core.windows.net/public/Novatel/assets/Documents/Manuals/om-20000094/om-20000094.pdf) or
[this](https://www.u-blox.com/sites/default/files/products/documents/u-blox6_ReceiverDescrProtSpec_%28GPS.G6-SW-10018%29_Public.pdf),
Emboss is meant for you.


## When should I not use Emboss?

Emboss is not designed to handle text-based protocols; if you can use minicom or
telnet to connect to your device, and manually enter commands and see responses,
Emboss probably won't help you.

Emboss is intended for cases where you do not control the data format.  If you
are defining your own format, you may be better off using [Protocol
Buffers](https://developers.google.com/protocol-buffers/) or [Cap'n
Proto](https://capnproto.org/) or [BSON](http://bsonspec.org/) or some similar
system.


## Why not just use packed structs?

In C++, packed structs are most common method of dealing with these kinds of
structures; however, they have a number of drawbacks compared to Emboss views:

1.  Access to packed structs is not checked.  Emboss (by default) ensures that
    you do not read or write out of bounds.
2.  It is easy to accidentally trigger C++ undefined behavior using packed
    structs, for example by not respecting the struct's alignment restrictions
    or by running afoul of strict aliasing rules.  Emboss is designed to work
    with misaligned data, and is careful to use strict-aliasing-safe constructs.
3.  Packed structs do not handle variable-size arrays, nor arrays of
    sub-byte-size fields, such as boolean flags.
4.  Packed structs do not handle endianness; your code must be very careful to
    correctly convert stored endianness to native.
5.  Packed structs do not handle variable-sized fields, such as embedded
    substructs with variable length.
6.  Although unions can sometimes help, packed structs do not handle overlapping
    fields well.
7.  Although unions can sometimes help, packed structs do not handle optional
    fields well.
8.  Certain aspects of bitfields in C++, such as their exact placement within
    the larger containing block, are implementation-defined.  Emboss always
    reads and writes bitfields in a portable way.
9.  Packed structs do not have support for conversion to human-readable text
    format.
10. It is difficult to read the definition of a packed struct in order to
    generate documentation, alternate representations, or support in languages
    other than C and C++.


## What does Emboss *not* do?

Emboss does not help you transmit data over a wire -- you must use something
else to actually transmit bytes back and forth.  This is partly because there
are too many possible ways of communicating with devices, but also because it
allows you to manipulate structures independently of where they came from or
where they are going.

Emboss does not help you interpret your data, or implement any kind of
higher-level logic.  It is strictly meant to help you turn bit patterns into
something suitable for your programming language to handle.


## What state is Emboss in?

Emboss is currently under development.  While it should be entirely ready for
many data formats, it may still be missing features.  If you find something that
Emboss can't handle, please contact `emboss-dev@google.com` to see if and when
support can be added.

Emboss is not an officially supported Google product: while the Emboss authors
will try to answer feature requests, bug reports, and questions, there is no SLA
(service level agreement).


## Getting Started

Head over to the [User Guide](doc/guide.md) to get started.
