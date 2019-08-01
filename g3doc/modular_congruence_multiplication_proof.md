# Modular Congruence of the Product of Two Values with Known Modular Congruences

(Draft)

TODO(webstera): Try to simplify this proof.

$$\text{If}$$&nbsp;

$${a} \equiv {r} \pmod{{m}}$$

$${b} \equiv {s} \pmod{{n}}$$

$${a}, {r}, {m}, {b}, {s}, {n} \in ℤ$$

$$\text{then}$$&nbsp;

$${a}{b} \equiv {r}{s} \pmod{G\left(\dfrac{{m}}{G\left({m}, {r}\right)},
\dfrac{{n}}{G\left({n}, {s}\right)}\right) \cdot G\left({m}, {r}\right) \cdot
G\left({n}, {s}\right)}$$

$$\text{where }G\text{ is the greatest common divisor function.}$$&nbsp;

$$\text{Proof:}$$&nbsp;

1.  $$\exists {x} \in ℤ : {a} = {m}{x} + {r} \text{ by the definition of modular
    congruence}$$&nbsp;

2.  $$\exists {y} \in ℤ : {b} = {n}{y} + {s} \text{ by the definition of modular
    congruence}$$&nbsp;

3.  $$\text{Let }{q} = G\left({m}, {r}\right)$$&nbsp;

4.  $$\text{Let }{p} = G\left({n}, {s}\right)$$&nbsp;

5.  $$\text{Let }{z} = G\left(\dfrac{{m}}{{q}}, \dfrac{{n}}{{p}}\right) =
    G\left(\dfrac{{m}}{G\left({m}, {r}\right)}, \dfrac{{n}}{G\left({n},
    {s}\right)}\right)$$&nbsp;

6.  $${a} = {q}\left(\dfrac{{m}{x}}{q} + \dfrac{{r}}{q}\right) \text{ by
    multiplying } \dfrac{{q}}{{q}} \text{ and distributing }
    \dfrac{1}{{q}}$$&nbsp;

7.  $$\dfrac{{m}{x}}{q}, \dfrac{{r}}{q} \in ℤ \text{ by the definition of
    } {q} \text{ in (3) }$$&nbsp;

8.  $${b} = {p}\left(\dfrac{{n}{y}}{{p}} + \dfrac{{s}}{{p}}\right) \text{ by
    multiplying } \dfrac{{p}}{{p}} \text{ and distributing }
    \dfrac{1}{{p}}$$&nbsp;

9.  $$\dfrac{{n}{y}}{{p}}, \dfrac{{s}}{{p}} \in ℤ \text{ by the definition of
    } {p} \text{ in (4) }$$&nbsp;

10. $${a} = {q}\left({z} \cdot \dfrac{{m}{x}}{{q}{z}} +
    \dfrac{{r}}{{q}}\right) \text{ by multiplying } \dfrac{{z}}{{z}}$$&nbsp;

11. $$\dfrac{{m}{x}}{{q}{z}} \in ℤ \text{ by the definition of } {z} \text{ in
    (5) }$$&nbsp;

12. $${b} = {p}\left({z} \cdot \dfrac{{n}{y}}{{p}{z}} +
    \dfrac{{s}}{{p}}\right) \text{ by multiplying } \dfrac{{z}}{{z}}$$&nbsp;

13. $$\dfrac{{n}{y}}{{p}{z}} \in ℤ \text{ by the definition of } {z} \text{ in
    (5)}$$&nbsp;

14. $${a}{b} = {q}{p}\left({z} \cdot \dfrac{{m}{x}}{{q}{z}} +
    \dfrac{{r}}{{q}}\right)\left({z} \cdot \dfrac{{n}{y}}{{p}{z}} +
    \dfrac{{s}}{{p}}\right) \text{ by (10) and (12)}$$&nbsp;

15. $${a}{b} = {q}{p}\left({z}^2 \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + {z} \cdot \dfrac{{r}}{{q}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + {z} \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{s}}{{p}} + \dfrac{{r}}{{q}} \cdot \dfrac{{s}}{{p}}\right) \text{ by
    partially distributing (14)}$$&nbsp;

16. $${a}{b} = {q}{p}\left({z}^2 \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + {z} \cdot \dfrac{{r}}{{q}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + {z} \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{s}}{{p}}\right) + {r}{s} \text{ by extracting the
    } \dfrac{{r}{s}}{{q}{p}} \text{ term from (15) and cancelling
    } \dfrac{{q}{p}}{{q}{p}}$$&nbsp;

17. $${a}{b} = {q}{p}{z}\left({z} \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + \dfrac{{r}}{{q}} \cdot \dfrac{{n}{y}}{{p}{z}} +
    \dfrac{{m}{x}}{{q}{z}} \cdot \dfrac{{s}}{{p}}\right) + {r}{s} \text{ by
    factoring } {z} \text{ from (16)}$$&nbsp;

18. $${z} \cdot \dfrac{{m}{x}}{{q}{z}} \cdot
    \dfrac{{n}{y}}{{p}{z}} + \dfrac{{r}}{{q}} \cdot \dfrac{{n}{y}}{{p}{z}} +
    \dfrac{{m}{x}}{{q}{z}} \cdot \dfrac{{s}}{{p}} \in ℤ \text{ because
    } {z}, \dfrac{{r}}{q}, \dfrac{{s}}{{p}}, \dfrac{{m}{x}}{{q}{z}},
    \dfrac{{n}{y}}{{p}{z}}, {z} \in ℤ \text{ per (5), (7), (9), (11),
    (13)}$$&nbsp;

19. $${a}{b} \equiv {r}{s} \pmod{{q}{p}{z}} \text{ by the definition of
    modulus}$$&nbsp;

20. $${a}{b} ≡ {r}{s} \pmod{G\left(\dfrac{{m}}{G\left({m}, {r}\right)},
    \dfrac{{n}}{G\left({n}, {s}\right)}\right) \cdot G\left({m}, {r}\right)
    \cdot G\left({n}, {s}\right)} \text{ by the definitions of } {q} \text{,
    } {p} \text{, and } {z} \text{ in (3), (4), and (5)}$$&nbsp;
