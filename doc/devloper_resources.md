# Links and Resources for Emboss Developers

## C++

*   [ISO C++ drafts](https://github.com/cplusplus/draft/tree/main/papers)
*   [C++14 final draft](https://github.com/cplusplus/draft/blob/main/papers/N3797.pdf)
*   [C++17 initial draft (C++14 + minor fixes)](https://github.com/cplusplus/draft/blob/main/papers/n4140.pdf)
*   [Final publicly-available drafts for each C++ revision](https://www.open-std.org/jtc1/sc22/wg21/docs/standards)
*   [cppreference](https://en.cppreference.com/)
*   [cplusplus.com reference](https://cplusplus.com/reference/)
*   [Compiler Explorer (Godbolt)](https://godbolt.org/)


### C++ Weirdness

*   [Some background about `uint8_t` vs `unsigned char` from GCC archives](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=66110#c10)
*   [A bug story: data alignment on x86](https://pzemtsov.github.io/2016/11/06/bug-story-alignment-on-x86.html)
*   [Casting unsigned to signed on OpenVMS HP C++ on Itanium](https://stackoverflow.com/questions/7601731/how-does-one-safely-static-cast-between-unsigned-int-and-int)


## Python

*   [Python official documentation, current](https://docs.python.org/3/)
*   [Python official documentation, v3.9 (oldest non-EOL until October 2025)](https://docs.python.org/3.9/)
*   [CPython lifecycle calendar](https://devguide.python.org/versions/)


## Bit Manipulation Tricks

*   [Sean Eron Anderson's Bit Twiddling Hacks page](https://graphics.stanford.edu/~seander/bithacks.html)
    *   But be careful copying code snippets: some of the C code is either
        non-portable or invokes undefined behavior.
*   [*Hacker's Delight*, Second Edition, by Henry S. Warren, Jr. (book)](https://en.wikipedia.org/wiki/Hacker%27s_Delight)


## Parsers

*   ["On the translation of languages from left to right", Knuth, D., 1965][1]

    [1]: https://doi.org/10.1016/S0019-9958(65)90426-2
    *   The paper that introduced shift-reduce parsers, and the "Canonical LR"
        table generation algorithm.
*   ["Efficient Computation of LALR(1) Look-Ahead Sets", DeRemer, D. & Pennello, T., 1982](https://dl.acm.org/doi/pdf/10.1145/69622.357187)
    *   The paper that introduced the LALR(1) table generation algorithm used
        in Berkeley YACC and GNU Bison.
*   ["Generating LR Syntax Error Messages from Examples", Jeffery, C., 2003](http://dx.doi.org/10.1145/937563.937566)
    *   [Link to non-paywalled copy](https://www.cs.tufts.edu/~nr/cs257/archive/clinton-jefferey/lr-error-messages.pdf)
    *   The paper that introduced the *Merr* error marking system.  Emboss uses
        this algorithm for specifying parser errors.
*   ["The IELR(1) algorithm for generating minimal LR(1) parser tables for non-LR(1) grammars with conflict resolution", Denny, J. & Malloy, B., 2010](https://doi.org/10.1016/j.scico.2009.08.001)
    *   An algorithm for generating minimal parser tables for LR(1) languages.
*   ["Practical LR Parser Generation", Zimmerman, J., 2022](https://doi.org/10.48550/arXiv.2209.08383)
    *   Many improvements on LR(1) parsing.
*   [*Compilers: Principles, Techniques, and Tools*, Second Edition, by Alfred V. Aho, Monica S. Lam, Ravi Sethi, and Jeffrey D. Ullman (the "Dragon Book")](https://en.wikipedia.org/wiki/Compilers:_Principles,_Techniques,_and_Tools)
