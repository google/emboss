# Things to Think About When Designing Features for Emboss (An Incomplete List)

Original Author:

Ben Olmstead (aka reventlov, aka Dmitri Prime), original designer and author of
Emboss


# General Design Principles

There are many, many books, articles, talks, classes, and exercises on good
software design, and most general design principles apply to Emboss.  In this
section, I will only cover the "most important" principles and those that I do
not see highlighted in many other places.


## Design to Real Problems, Not Hypotheticals

In order to avoid "second system effect," designs that do not work in practice,
and wasted effort, it is best to design to a specific problem — preferably a
few instances of that problem, so that your design is more likely to solve a
wide range of real world problems.

For example, in Emboss if you wait until you have a specific data structure
that is awkward or impossible to express, then try to find examples of other
structures that are awkward in the same way, and then design a feature to
handle those data structures, you are much more likely to come up with a
solution that a) will actually be used, and b) will be used in more than one
place.


## Design to the Problem, Not the Solution

Often, users will have a problem, think "I could solve this if I could do X,"
and then ask for a feature for X without mentioning their original problem.  As
a software designer, one of the first things you should do is try to figure out
the original problem — usually by asking the user some probing questions — so
that you can design to the problem, not to the user's solution.

(Note that this is sometimes true even if you are the user: it is easy to get
tunnel vision about a solution you came up with.  Sometimes you need to step
back and try to find a different solution.)


## Do Not Try to Do Everything

Avoid the temptation to cover every possible use case, even if some of those
would generally fit within the domain of your project.  A project like Emboss
will attract extremely specific requests — requests whose solutions do not
generalize.


### Emboss is a "95% Solution"

Instead of trying to cover every use case for every user, leave "escape
hatches" in your design, so that users can use Emboss for the cases it covers,
and integrate their own solutions in the places that Emboss does not cover.

There will always be formats that Emboss cannot handle without becoming an
actual programming language — even something as "basic" as compression is
generally beyond what Emboss is meant to be capable of.


## Be Conservative

Emboss has strong backwards-compatibility guarantees: in particular, once a
feature is "released," support for that feature is guaranteed more or less
forever.  Because of this, new features should be narrow, even if there are
"obvious" expansions, and even if narrowing the feature actually takes more
code in the compiler.  You can always expand a feature later, but narrowing it
or cutting it out would break Emboss's support guarantees.

Although this principle is very standard for professional, publicly-released
software, it may be a culture shock to developers who are used to
"monorepo"[^mono] environments such as Google — it is not possible to just
update all users in the real world!  Note that even many of Google's *open
source* projects, such as Abseil, require their users to periodically update
their code to the latest conventions, which imposes a cost on users of those
projects.  Emboss is intended for smaller developers and embedded systems,
which often do not have the resources for such migrations.

[^mono]: As an aside, in the several years that Emboss spent inside Google's
    monorepo it underwent many large, backwards-incompatible changes that made
    the current language significantly better.  Early incubation in a
    controlled environment can be valuable for a new language!


## Design for Later Expansion

### Leave "Reserved Space" for Future Features

Emboss uses `$` in many keyword names, but does not allow `$` to be used in
user identifiers — this lets Emboss add `$` keywords without worrying about
colliding with identifiers in existing code.  (This is in direct contrast to
most programming languages, where introducing new keywords often breaks
existing code.)

As another example, Emboss disallows identifiers that collide with keywords in
many programming languages — this gives room for Emboss to add back ends for
those programming languages later, without having to figure out a convention
for mangling identifiers that collide.  As a real-world counterexample,
Protocol Buffers had to figure out a convention for handling field names that
collide with C++ identifiers such as `class` — and `protoc` still generates
broken C++ code if you have two fields named `class` and `class_` in the same
`message`.


### Leave "Extension Points"

An "extension point" is a place where someone should be able to hook into the
system without changing the system.  This can be an API, a "hook," a defined
data format, or something else entirely, but the defining factor is that it is
a way to add new features or alter behavior without changing the existing
software.

In practice, many extension points won't "just work" until there are at least a
few things using them, due to bugs or unexpected coupling, but in principle
they should not require any modification.

One extension point in the Emboss compiler is the full separation between front
and back ends, so that future back ends (such as Rust, Protocol Buffers, PDF
documentation, etc.) can be added without changing the overall design or
(theoretically) any of the existing compiler.[^ext]

[^ext]: This is not unique or original to Emboss: separate front and back ends
    are totally standard in modern compiler design.

In the physical world, an electrical outlet or a network port is an extension
point — there is nothing there right now, but there is a defined place for
something to be added later.


### Leave "Lines of Cleavage"

A "line of cleavage" is similar to an extension point, except that instead of
being a ready-to-go place to add something new, it's a place where the major
work was done, but there are still some pieces that need to be fixed up.

A line of cleavage in the Emboss compiler is the use of a special `.emb` file
(`prelude.emb`) to define "built-in" types, with the aim of eventually allowing
end users to define their own types at the same level.  This feature still has
open design decisions, such as:

*   How will users define their type for the back end(s)?
*   How will users define the range of an integer type for the expression
    system?

But these are relatively minor compared to the larger question of "how can
Emboss allow end users to define their own basic types?"

In software, lines of cleavage are usually invisible to end users, and can be
difficult to see even for developers working on the code.

In the physical world, an example of this is putting empty conduit into walls
or ceilings: that way, new electrical or communication wires or pneumatic tubes
can be pulled through the conduit and attached to new outlets, without having
to open up *all* the walls.


## Consider Known Potential Features

Every complex software system has a cloud of potential features around it:
features which, for one reason or another, have not been implemented yet, but
which some stakeholder(s) want.  These features usually exist at every stage
from "idle thought in a developer's mind" to "partially implemented, but not
finished," and the likelihoods of each one to become a finished feature cover
an equally wide range.

When designing a new feature there are very good reasons to think about these
potential features:

First, you should ensure that your new feature does not make another
highly-desirable feature impossible.  In Emboss, for example, if your new
feature made it impossible to support a string type, that would be a very good
reason to redesign your feature (or abandon it, if it is fundamentally
incompatible).

Second, sometimes you can tweak your design so that a potential feature becomes
obsolete: fundamentally, every feature request exists to solve a problem, and
often it is not the only way to solve that problem.  If you can solve it in a
different way, you can make users happy and avoid some future work.  (Though be
careful: it can be difficult to infer the full scope of a user's problem(s)
from a feature request.)

Third, thinking about specific potential features can help narrow the amount of
"future design space" that you need to consider, which makes it easier to put
extension points and lines of cleavage in your design in places where they will
actually be used.


# General Language Design Principles

In contrast to general software design principles, there are far fewer sources
on good *language* design.  I speculate that this is because there are far
fewer language designers than software designers.  (There are tens of millions
of software developers, but only tens of thousands of programming, markup, and
data definition languages — and of those, maybe two thousand or so are
"serious" languages with significant real-world use.)

Luckily, there are many publicly available and documented languages to learn
from directly.

Language design can be very roughly divided into syntactic and semantic
concerns: syntax is how the language *looks* (what symbols and keywords are
used, and in what order), while semantics cover how the language *works* (what
actually happens).  It might seem like semantics are more important, but syntax
has a huge effect on how easy it is to understand existing code and to write
correct code, which are both incredibly important in real-world use.

In this section, I will try to outline language design principles that I have
found or developed, particularly when they are useful for Emboss.


## Be Mindful of the Power/Analysis Tradeoff

[Turing-complete languages cannot be fully
analyzed](https://en.wikipedia.org/wiki/Halting_problem).  This is one of the
reasons that languages like HTML and CSS are not programming languages: the
more expressive a language is, the more difficult it is to analyze.

The `.emb` format is intended to be more on the declarative side, so that
definitions can be analyzed and transformed as necessary.


## Look at Other Languages

Although Emboss is a data definition language (DDL), not a programming
language, many lessons and principles from programming language design can be
applied, as well as lessons from other DDLs, and sometimes even interface
definition languages (IDLs), as well as markup and query languages.

In particular, for Emboss it is often worth looking at:

*   Popular programming languages: C, C++, Rust, JavaScript, TypeScript, C#,
    Java, Go, Python 3, Swift, Objective C, Lua.  "Systems" programming
    languages such as C, C++, and Rust are usually the most relevant of these,
    but it is useful to survey all the popular languages because many Emboss
    users will be familiar with them.  Note that Lua is used for Wireshark
    packet definitions.

*   Selected "interesting" programming languages: Wuffs, Haskell, Ocaml, Agda,
    Coq.  These have some lessons for Emboss, especially its expression system
    — in particular, they're all much more principled than "standard"
    programming languages about how they handle types and values.  There are
    many other programming languages that have interesting ideas (FORTH,
    Prolog, D, Perl, Logo, Scratch, APL, so-called "esoteric" programming
    languages), but they usually are not relevant to Emboss.

*   DDLs: Kaitai Struct, Protocol Buffers, Cap'n Proto, SQL-DDL.  Kaitai Struct
    is the closest of these to solving the same problem as Emboss (though it
    has some fundamentally different design decisions which make it far worse
    for embedded systems), but all have some lessons.  Some higher-level schema
    languages like DTD, XML Schema, or JSON Schema tend to be less relevant to
    Emboss.  Note that there are a number of DDLs that are also IDLs: in actual
    use, some of them (Protocol Buffers) are used more often for their DDL
    features, while others (XPIDL, COM) are used more for their IDL features.


## Learn Academic Theory

Many (most?) languages are designed by people who have minimal knowledge of the
academic theories of how programming languages work — for Emboss, Category
Theory is particularly useful, and the computer science of parsers (especially
LR(1) parsers) is useful for tweaking the parser generator or adding new
syntax.

This is a case where a little bit of learning goes a long way: you do not need
to learn a *lot* about parsers or Category Theory to benefit from them.


## Try to Acquire Practical Knowledge

Many of the academic topics related to programming language design have
corresponding industrial knowledge, and there are practical concerns that have
very little to do with academic theory.

The Emboss compiler is (loosely) based on the design of LLVM, with a series of
transformation passes that operate somewhat independently, and independent back
end code generators.[^designoops]

[^designoops]: After many years of experience with this, I think that this is
    not quite the right design for Emboss, and I would make two major changes:
    first (and simplest), I would divide the current "front end" into a true
    front end that only handled syntax and some types of syntax sugar, and a
    "middle end" that handled all of the symbol resolution, bounds analysis,
    constraint checking, etc.  Second, I would use a "compute-on-demand" (lazy
    evaluation) approach in the middle end, which would allow certain
    operations to be decoupled.  The LLVM design is more suited for independent
    optimization passes, not for the kind of gradual annotation process in the
    Emboss middle end.

As another example, understanding how (and how well) Clang, GCC, and MSVC can
optimize C++ code is crucial to generating high-performance code from Emboss
(and Emboss leans very heavily on the C++ compiler to optimize its output).

Some bits of practical knowledge are tiny little bits of almost-trivia.  For
example, if you have C or C++ code in a (text) template, and you use `$` to
indicate substitution variables (as in `$var` or `$var$`), then most editors
and code formatters will treat your substitution variables as normal
identifiers.  This is because almost every C and C++ compiler allows you to use
`$` in identifiers, even though there has never been a C or C++ standard that
allows those names, and it is rarely noted in any compiler, editor, or
formatter's documentation.


## Use Existing Syntax

Emboss pulls many conventions from programming, data definition, and markup
languages.  In general, if there is a feature in Emboss that works in a way
that is the same as in other languages, it is best to pull syntax from
elsewhere — ideally, pull in the most common syntax.  Many examples of this in
Emboss are so common you might not even think about them:

*   Arithmetic operators (`+`, `-`, `*`)
*   Operator precedence (`*` binds more tightly than `+` and `-`, but also: see
    the next section)

Other examples are most specific, with no universal convention:

*   `: Type` syntax for type annotation (TypeScript, Python, Ocaml, Rust, ...)

This is *especially* important for Emboss, because most people reading or
writing Emboss code will not want to spend much time becoming an "Emboss
expert" — where someone might be willing to spend days or weeks to learn how to
write Rust code, they are more likely to spend hours or minutes learning to
write Emboss.


## Avoid Existing Syntax

However, there are three main reasons to avoid using existing syntax:

*   The "standard" syntax is error prone.  One example of this is operator
    precedence in most programming languages: errors related to not knowing the
    relative precedence of `&&` and `||` are so common that most compilers have
    an option to warn if they are mixed without parentheses.  Emboss handles
    this — and a few other error-prone constructs — by having a *partial
    ordering* for precedence instead of the standard total ordering, and making
    it a syntax error to mix operators such as `&&` and `||` that have
    incomparable (neither equal, less than, nor greater than) precedence.  As
    far as I can tell, this is a totally new innovation in Emboss: there is no
    precedent (no pun intended) whatsoever for partial precedence order.

    When avoiding syntax in this way, it is ideal to make the standard syntax
    into a syntax error (so that no one can use it accidentally) and to add an
    error message to the compiler that suggests the correct syntax.

*   The existing syntax is not used consistently: if multiple programming
    languages use the same syntax for slightly different semantics, it is
    usually worth avoiding the syntax.  For example, `/` has quite a few
    different semantics — in many languages, it is a type-parameterized
    division, where the numeric result depends on the (static or dynamic) types
    of its operands, and across languages, the "integer division" flavor is not
    consistent — in most programming languages it is *truncating division* (`-7
    / 3 == -2`), but in some programming languages it is *flooring division*
    (`-7 / 3 == -3`).

*   The semantics do not match: if an Emboss feature is *almost*, but *not
    quite* equivalent to a feature in other languages, it is best to avoid
    making the Emboss feature look like the other feature.


## Poll Users/Programmers

When designing a new feature, try to come up with several alternatives and poll
Emboss users (or sometimes non-Emboss-using programmers) as to which one they
prefer.

For syntax, one especially powerful technique is to show an example of the
proposed syntax to people who have never seen it, and ask "what do you think
this means?" without any hinting or prompting.  This is the "gold standard" way
of finding out whether your syntax is clear or not.


## Avoid Error-Prone Constructs

Computing now has roughly seventy years of experience with artificial languages
(in programming, markup, data definition, query, etc. flavors), and we have
learned a lot about what kinds of constructs are error-prone for humans to use.
Avoid these, where possible!  Some examples include:

*   Large semantic differences should not have small, easily-overlooked
    syntactic differences.  For example, allowing single- and double-character
    operators (`=` and `==`, `|` and `||`, etc.) in the same contexts: a
    classic C-family programming error is to use `=` in a condition instead of
    `==`.  Many modern languages either force `=` to be used only in "statement
    context" (and some, like C#, also ban side-effectless statements such as `x
    == y;`) or use a different operator like `:=` for assignment.  (Or both, as
    in Python, which allows `:=` but not `=` for "expression assignment.")

*   Syntax should have *consistent* semantic meaning.  For example, in
    JavaScript these two snippets mean the same thing:

    ```js
    return f() + 10;
    ```

    ```js
    return f() +
              10;
    ```

    but this one is different (it returns `undefined`, thanks to JavaScript's
    automatic `;` insertion):

    ```js
    return
        f() + 10;
    ```

    A small difference in the placement of the line break leads to totally
    different semantics!

    C++ has a number of places where identical syntax can have wildly different
    semantics, especially (ab)use of operator overloads and [the most vexing
    parse](https://en.wikipedia.org/wiki/Most_vexing_parse).

*   Hoare calls "null" his "billion-dollar mistake," and the way that null
    pointers are handled in most programming languages, especially C and C++,
    is particularly error-prone.  (But note that it isn't really "null" itself
    that is problematic — it's that there is no way to mark a pointer as "not
    null," and that doing anything with a null pointer leads to undefined
    behavior.  However, some popular language features, such as the `?.`
    operator found in several programming languages and the `std::optional<>`
    type in C++, show that there is some utility to nullable types, as long as
    there is language support for enforcing null checks and/or allowing null to
    propagate in the same way that NaN can.)

*   Edge cases, such as integer overflow, are difficult for humans to reason
    about.  In systems programming languages like C and C++, this leads to a
    significant percentage of security flaws.  (C and C++ compilers use the
    "integer overflow is undefined" rule *extensively* in optimization, so
    there are pragmatic trade-offs in general.  Emboss is used in smaller
    contexts with tighter safety guarantees.)


# Emboss-Specific Considerations

Emboss sits in a section of design space that has very few alternatives, and as
a result there are things to think about when designing Emboss features that do
not apply to many other languages.

Also, because Emboss already exists, there are a number of systems within
Emboss-the-language that may interact with new features.

And finally, if you want your feature to become implemented, it is necessary to
consider how difficult it would be to implement new features in `embossc`.


## Survey Data Formats

Maybe the least fun (at least for me[^unfun]) part of designing Emboss features
is reading through data sheets, programming manuals, RFCs, and user guides to
understand the data formats used in the real world, so that any new feature can
handle a reasonable subset of those formats.  Some sources to consider:

*   Data sheets and programming manuals for:
    *   complex sensors, such as LiDAR
    *   GPS receivers
    *   servos
    *   LED panels and segmented displays
    *   clock hardware
    *   ADCs and DACs
    *   camera sensors
    *   power control devices
    *   simple sensors such as barometers, hygrometers, current sensors,
        voltage sensors, light sensors, etc. (though many very simple sensors
        use analog outputs or very, very simple digital outputs that do not
        have a "protocol" as such)
*   RFCs for low-level protocols such as Ethernet, IP, ICMP, UDP, TCP, and ARP

<!-- TODO: assemble a list of links to actual examples -->

[^unfun]: One of my original motivations for creating Emboss is that I find
    reading data sheets and implementing code to read/write the data formats
    therein to be extremely tedious.


## Structure Layout System

The "heart" of Emboss is what may be called the "structure layout system:" the
engine that determines which bits to read and write in order to produce or
commit the values of fields.  When designing, consider:

*   Does this feature require reaching "outside" of a scope?  For example,
    referencing a sibling field from within a field's scope is currently
    impossible, because each field has its own scope.  Allowing `[requires:
    this == sibling]` means expanding that scope.

*   Does this feature require information that is not (currently) available to
    the layout engine, or not available at the right place or time?  For
    example, if you are designing a feature to allow field sizes to be `$auto`,
    how does that interact with structures that are variable size?

*   Does this feature require information that is potentially circular, or
    would it interact with another potential feature to require circular
    information, and is there a way to resolve that?  For example: if you are
    designing a feature to allow field sizes to be `$auto`, inferring their
    size from their type, how will that interact with the potential feature to
    allow `struct`s that grow to the size they are given?


## Expression System

Although most expressions in Emboss definitions are simple (such as `x*4` or
even just `0`), the expression system in Emboss tracks a lot of information,
such as:

*   What is the type of every subexpression (e.g., integer, specific
    enumeration, opaque, etc.)?
*   For integer and boolean expressions, does the expression evaluate to fixed
    (constant) value?
*   For integer expressions, what are the upper and lower bounds of the
    expression?  (Used for determining the correct integer types to use in
    generated code.)
*   For integer expressions, is the value guaranteed to be equal to some fixed
    value modulo some constant?  (Used for generating faster code for aligned
    memory access.)

When designing a feature, consider:

*   Will any new types be `opaque` to the expression system, or will it be
    possible to perform operations on them?  If they are `opaque` for now, will
    they stay that way, or will it be possible to manipulate them in the
    future?  For example, adding a string type in Emboss might start as
    `opaque`, but allow operations like "value at index" or "substring" in the
    future.
*   When adding new operations, how will they interact with the bounds and
    alignment tracking?  For example: truncating division often breaks
    alignment tracking, whereas flooring division does not.
*   Will this feature invalidate existing code?  Anything that causes the
    inferred integer bounds of existing code to expand can break existing code.

Note that the entire point of Emboss is to provide a bridge between physical
data layout (as defined in the structure layout system) and abstract values
with no specific representation (as exposed through the expression system).


## Parsing

Any new syntax has to be added to the parser.  Aside from the language design
considerations for new syntax (see the ["General Language Design Principles"
section](#general-language-design-principles)), there are a few levels of
concern for the actual implementation:

*   Is it computationally feasible to parse this syntax in an intuitive,
    unambiguous way?
*   Is it humanly feasible to express this syntax as an LR(1) grammar that can
    be parsed by Emboss's shift-reduce parser engine?
*   Is it feasible to parse this syntax using a different parsing engine type
    (Earley, recursive descent, TDOP, parser combinator, etc.)?

The first consideration is more of a general language design consideration: if
your language design says "users will be able to specify their program in
English," that is not really feasible (or unambiguous).  (Not that it hasn't
been tried, many times.)

The second consideration — can you add this syntax to `embossc`? — is the most
practical and important consideration for Emboss.  LR(1) grammars are pretty
restrictive (though shift-reduce parsers have advantages — there are reasons
Emboss is using one), and even when it is *possible* to express a particular
syntactic construct in LR(1)[^zimm], it may be difficult for most programmers to
actually do so.  As a practical matter, I recommend trying to actually add your
syntax to `module_ir.py`.

[^zimm]: As an aside, I think it would be awesome to implement [[Zimmerman,
    2022](https://arxiv.org/abs/2209.08383)] plus a few extensions of my own
    devising in Emboss's shift-reduce engine, which would make the grammar
    design space significantly larger.  I would also separate the parser
    generator engine into its own project.

The third consideration is more future-focused and abstract: does this syntax
lock Emboss into using a shift-reduce parser in the future?  Ideally, no.
Luckily(?), LR(1) grammars are one of the more restrictive types of grammars in
common use, so it is likely that anything that can be handled by the current
parser can be handled by many other types of parsers.


## Generated Code

Right now, there is only the generated C++ code, but there should be other back
ends in the future.  Some new features are pure syntax sugar (e.g., `$next` or
`a < b < c`) that are replaced in the IR long before it reaches the back end
(e.g., with the offset+length of the syntactically-previous field, or the IR
equivalent of `a < b && b < c`), while others require extensive changes to how
code is generated.

*   What information will the back end need in order to generate working code?
*   Does this feature require embedded-unfriendly generated code?  (E.g.,
    memory allocation, I/O.)
*   Can the existing C++ back end, which just walks the IR tree in a single
    pass while building up strings which are combined into a `.h`, handle this
    feature in its current design?
*   How will this feature interact with various generated templates?
*   Can/should this feature be, itself, templated?


## C++ Runtime Library

The runtime library will be included with every program that touches Emboss, so
it is important to make it efficient.  When adding features, consider:

*   Can the feature be added in such a way that it does not cost anything for
    programs that do not use the feature?  A standalone C++ template will not
    be included in a program unless the program instantiates the template, but
    if the new code is used from somewhere in an existing function, it may be
    included in programs that do not use it directly.

*   Can the feature be added without allocating any heap memory?  Can it be
    added with O(1) stack memory use?  Both of these are important for some
    embedded systems, such as OS-less microcontroller and hard-real-time
    environments.  Some features may intrinsically require memory allocation,
    in which case it is best if they can be separated: for example, Emboss
    structure-to-string conversion requires allocation, and even `#include`'ing
    the appropriate headers can be too much for some environments, even if the
    serialization code is never included in the final binary.

*   How much can you rely on the C++ compiler to optimize things?  If you have
    to implement your own optimizations, that will cost more development time
    and add more complexity to the standard library.


## Compiler Complexity

The Emboss compiler is already quite complex, and has many subsystems that
interact.  It is already quite difficult to reason about some interactions.

*   Can the feature be added at an "edge" of the compiler?  For example, if you
    can implement your feature as syntax sugar that converts the new feature to
    existing IR early in the compilation process, it is much easier to verify
    that it will not cause problematic interactions.  Similarly, if you can
    implement your feature entirely in the back end or in the runtime library,
    you do not need to worry about interactions inside the front end.

*   If a feature cannot be added at an edge, how can you design it to minimize
    the complexity?  (Ideally, you could even unify existing systems in such a
    way that the overall complexity of the compiler is lower at the end.)


## Future Back Ends

It is important to have some idea of how any feature would be implemented
against future back ends.


### Programming Language (Rust/Python/Java/Go/C#/Lua/etc) Back Ends

Some features may be difficult to implement in other languages.  For example,
Python does not have a native `switch` statement, so any `switch`-like feature
in Emboss may be awkward to implement — but this does not necessarily mean that
Emboss should not have a `switch`.

As a rule of thumb, languages can be grouped into tiers:

1.  "Systems"/embedded-friendly languages: C++, Rust, C.  Top support.
2.  Languages used for parsing/analyzing raw sensor dumps: C#, Java, Go,
    Python, etc.  Should have good support, but not gate any features.
3.  Languages that are rarely used to touch binary data: JavaScript,
    TypeScript, etc.  Can be mostly ignored.
4.  Dead and obscure languages: Perl, COBOL, APL, INTERCAL, etc.  Can be
    ignored entirely.

(It may be difficult to classify some languages, such as FORTRAN, which is
still hanging around in 2024.)

Remember that other back ends may have different requirements and guarantees
than the C++ back end: for example, it would be unreasonable for a Java back
end to promise "no dynamic memory allocation."


### Other Data Format (Protobuf/JSON/etc) Back Ends

These back ends would translate binary structures into alternate
representations that are easier for some tools to use: for example, Google has
many, many tools for processing Protocol Buffers, and JSON is popular in the
open-source world.

Most other formats have limitations that may make some kinds of Emboss
constructs difficult or impossible to correctly reproduce: for example, Emboss
already supports "infinitely nested" `struct` types, like:

```
struct Foo:
    0 [+10]  Foo  child_foo
```

Formats like Protobuf or JSON, which do not have any way of representing loops
in their data graph, cannot handle this.

Until the most recent versions of Protobuf, mismatches between Protobuf `enum`
and Emboss `enum` made it functionally impossible to map any Emboss `enum`
types onto Protobuf `enum` types: Emboss `enum` types are open (allow any
value, even ones that are not listed in the `enum`), where all Protobuf `enum`
types were closed (only allowed known values).  (The most recent Protobuf
versions, Proto3 and Editions, allow you to have open `enum` types.)

Generally, it is not worth blocking an Emboss feature because of these kinds of
mismatches, but it is worth thinking about how to avoid them, if possible.


### Documentation (PDF/Markdown/etc) Back Ends

These back ends would translate `.emb` files to a form of human-readable
documentation, intended for publication on a web site, in an RFC, or as part of
a PDF datasheet.  This type of back end is the motivation for having both `--`
documentation blocks and `#` comments in Emboss.

Since the output from these back ends would be intended for human consumption,
for the most part you would only need to ensure that your feature can be
understood by humans.
