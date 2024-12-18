# Contributing to Emboss

If you would like to fix a bug or add a new feature to Emboss, great!  This
document is intended to help you understand the procedure, so that your change
can land in the main Emboss repository.

You do not have to take a change all the way from start to finish, either: if
you can get a design approved, then someone else can implement it much more
easily.  Conversely, if you are looking for a way to help, you might look for
existing [feature
requests](https://github.com/google/emboss/labels/enhancement) that have
designs or at [open design sketches](design_docs/) that you might be able to
implement.


## All Changes

Because Emboss is a Google project, in order to submit code you will need to
sign a [Google Contributor License Agreement
(CLA)](https://cla.developers.google.com/).

**IMPORTANT**: if your contribution includes code that is not covered by a
Google CLA and is not owned by Google, the Emboss project has to follow special
procedures to include it.  Please let us know ([filing an issue on
GitHub](https://github.com/google/emboss/issues/new) is probably the easiest
way) so that we can walk you through the process.  In particular, we generally
cannot accept any code from StackExchange or similar sites, and any code that
comes from a non-Google open source project needs to have an acceptable license
and be committed to the Emboss repository in a specific location.


### How-To Guides

This document covers the process of getting a change into the main Emboss
repository — i.e., what you need to do to get your change into
[the main Emboss repository](https://github.com/google/emboss/).

[How to Implement Changes to Emboss](how-to-implement.md) has an overview of
how to make code changes to Emboss.

[How to Design Features for Emboss](how-to-design.md) has an overview of what
to think about during your design.


### Bug Fixes vs New Features

The general process for bug fixes and new features is the same, but bug fixes
usually require less design work, and therefore can go through lighter
processes.


## Very Small Changes

If you have a tiny change — for example,  making a fix that does not change the
design of `embossc` — you can jump directly into coding.

This process works best if your change is small and not likely to be
controversial, or if you have already completed [the steps for small
changes](#small-changes).

1.  [Code up your proposed change](how-to-implement.md) and open a [pull
    request
    (PR)](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)
    to [the main Emboss repository](https://github.com/google/emboss/).  If you
    have not completed [the steps for small changes](#small-changes), this
    gives the Emboss maintainers something more concrete to look at, but you
    may end up doing more work if your initial proposal turns out to be the
    wrong approach.

2.  The Emboss maintainers will review your PR, and may request changes.  Don't
    be discouraged if your PR is not immediately accepted — even PRs that
    maintainers send to each other often have requests for changes!  We want
    the Emboss code to be high-quality, which means helping you make your code
    better.

3.  Once your PR reaches a point where it is good enough, an Emboss maintainer
    will merge it into the Emboss repository.


## Small Changes

If your change is small, but still requires some design work — for example,
adding a new utility function in the C++ runtime library, or making a bug fix
that involves re-structuring some of the `embossc` code — it is usually best to
get some feedback before you start coding.

1.  [File an issue on GitHub](https://github.com/google/emboss/issues/new), if
    there is not an issue already.  It is best to use the *problem you want to
    solve* for the issue title and description, and then propose your design in
    a comment.

2.  Once the Emboss maintainers have had a chance to review your proposal and
    agree on the general outline, follow [the procedure for very small
    changes](#very-small-changes).


## Medium and Large Changes

If you have a medium or large change — for example, introducing a new pass in
`embossc`, adding a new data type, adding a new operator to the Emboss
expression language, making a cross-cutting refactoring of `embossc`, etc. —
then you should start by writing a *design sketch*.

A design sketch is, basically, an informal design doc — it covers the topics
that a design doc would cover, but may have open questions or alternatives that
haven't been locked down.

1.  [File an issue on GitHub](https://github.com/google/emboss/issues/new), if
    there is not an issue already.  It is best to use the *problem you want to
    solve* for the issue title and description.

2.  Look at [existing design sketches](design_docs/) and [archived design docs
    for changes that have already landed](design_docs/archive/) to get a feel
    for what should be in a design sketch.

3.  If you have not already done so, read [How to Design Features for
    Emboss](how-to-design.md).

4.  Write a draft design sketch for your change, and open a pull request
    against [the main Emboss repository](https://github.com/google/emboss/).

5.  It is very likely that your design sketch will need revision before it is
    accepted.  If it does, do not be discouraged — we want your change to
    succeed!

6.  Once your design sketch has been accepted, you can move on to
    implementation, following (more or less) the same procedure you would
    follow for [small](#small-changes) or [very small
    changes](#very-small-changes).  Depending on the complexity of the change,
    you may need to split your implementation into multiple changes.
