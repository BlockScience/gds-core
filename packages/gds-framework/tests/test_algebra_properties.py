"""Property-based tests for the GDS composition algebra.

Tests the algebraic properties that the composition operators must satisfy
for the block algebra to form a symmetric monoidal category:

- Interchange law: (g >> f) | (j >> h) = (g | j) >> (f | h)
- Associativity of >> and |
- Commutativity of | (up to interface reordering)
- Identity behavior of blocks with empty interfaces

See: docs/research/verification-plan.md (Phase 1a)
     docs/research/formal-representability.md (Def 1.1)
"""

import os

from hypothesis import given, settings
from hypothesis import strategies as st

from gds.blocks.base import AtomicBlock
from gds.types.interface import Interface, Port, port

# ---------------------------------------------------------------------------
# Reproducibility: fixed seed database ensures CI determinism.
# Run with --hypothesis-seed=<N> to reproduce a specific failure.
# ---------------------------------------------------------------------------
settings.register_profile("ci", database=None, derandomize=True, max_examples=200)
settings.register_profile("dev", max_examples=200)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Port names that tokenize cleanly (single lowercase token, no delimiters)
port_names = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
    min_size=1,
    max_size=8,
)

# Unique block names
block_names = st.text(
    alphabet=st.sampled_from("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
    min_size=1,
    max_size=6,
)


@st.composite
def port_tuples(draw, min_size=0, max_size=3, exclude=frozenset()):
    """Generate a tuple of Ports with distinct names.

    Parameters
    ----------
    exclude : frozenset[str]
        Port names to exclude (e.g. a shared token already in use).
    """
    n = draw(st.integers(min_value=min_size, max_value=max_size))
    names = draw(
        st.lists(
            port_names.filter(lambda name: name not in exclude),
            min_size=n,
            max_size=n,
            unique=True,
        )
    )
    return tuple(port(name) for name in names)


@st.composite
def interfaces(draw):
    """Generate a random Interface with ports on all four slots."""
    return Interface(
        forward_in=draw(port_tuples()),
        forward_out=draw(port_tuples()),
        backward_in=draw(port_tuples()),
        backward_out=draw(port_tuples()),
    )


@st.composite
def named_block(draw, name=None, iface=None):
    """Generate an AtomicBlock with optional name/interface override."""
    return AtomicBlock(
        name=name or draw(block_names),
        interface=iface or draw(interfaces()),
    )


@st.composite
def stackable_pair(draw):
    """Generate two blocks where first.forward_out overlaps
    second.forward_in.

    Uses a shared token to guarantee >> succeeds without explicit
    wiring. Extra ports exclude the shared token to prevent
    duplicate port names.
    """
    shared = draw(port_names)
    exclude = frozenset({shared})

    extra_out = draw(port_tuples(max_size=2, exclude=exclude))
    extra_in = draw(port_tuples(max_size=2, exclude=exclude))

    first = AtomicBlock(
        name=draw(block_names.filter(lambda n: n != "B")),
        interface=Interface(
            forward_in=draw(port_tuples(max_size=2)),
            forward_out=(port(shared), *extra_out),
            backward_in=draw(port_tuples(max_size=1)),
            backward_out=draw(port_tuples(max_size=1)),
        ),
    )
    second = AtomicBlock(
        name="B_" + draw(block_names),
        interface=Interface(
            forward_in=(port(shared), *extra_in),
            forward_out=draw(port_tuples(max_size=2)),
            backward_in=draw(port_tuples(max_size=1)),
            backward_out=draw(port_tuples(max_size=1)),
        ),
    )
    return first, second


@st.composite
def interchange_quadruple(draw):
    """Generate four blocks (f, g, h, j) for the interchange law.

    Interchange law: (g >> f) | (j >> h) = (g | j) >> (f | h)

    Requires:
    - g >> f is valid (g.forward_out overlaps f.forward_in)
    - j >> h is valid (j.forward_out overlaps h.forward_in)
    - (g | j) >> (f | h) is valid (union of g,j forward_out
      overlaps union of f,h forward_in)

    Strategy: two distinct shared tokens, one per sequential chain.
    """
    token1 = draw(port_names)
    token2 = draw(port_names.filter(lambda t: t != token1))

    g = AtomicBlock(
        name="g",
        interface=Interface(
            forward_in=draw(port_tuples(max_size=1)),
            forward_out=(port(token1),),
        ),
    )
    f = AtomicBlock(
        name="f",
        interface=Interface(
            forward_in=(port(token1),),
            forward_out=draw(port_tuples(max_size=1)),
        ),
    )
    j = AtomicBlock(
        name="j",
        interface=Interface(
            forward_in=draw(port_tuples(max_size=1)),
            forward_out=(port(token2),),
        ),
    )
    h = AtomicBlock(
        name="h",
        interface=Interface(
            forward_in=(port(token2),),
            forward_out=draw(port_tuples(max_size=1)),
        ),
    )
    return f, g, h, j


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def interface_eq(a: Interface, b: Interface) -> bool:
    """Compare interfaces by port name sets (order-independent)."""

    def port_set(ports: tuple[Port, ...]) -> frozenset[str]:
        return frozenset(p.name for p in ports)

    return (
        port_set(a.forward_in) == port_set(b.forward_in)
        and port_set(a.forward_out) == port_set(b.forward_out)
        and port_set(a.backward_in) == port_set(b.backward_in)
        and port_set(a.backward_out) == port_set(b.backward_out)
    )


def flat_names(block) -> list[str]:
    """Get ordered list of atomic block names from a composition."""
    return [b.name for b in block.flatten()]


# ---------------------------------------------------------------------------
# Interchange Law
# ---------------------------------------------------------------------------


class TestInterchangeLaw:
    """The interchange law: (g >> f) | (j >> h) = (g | j) >> (f | h)

    This is the central property of a symmetric monoidal category.
    Both sides must produce the same interface and the same flattened
    block topology.
    """

    @given(interchange_quadruple())
    @settings(max_examples=200)
    def test_interface_equality(self, quad):
        """Both sides of interchange produce the same interface."""
        f, g, h, j = quad

        left = (g >> f) | (j >> h)
        right = (g | j) >> (f | h)

        assert interface_eq(left.interface, right.interface), (
            f"Interchange law violated:\n"
            f"  LHS interface: {left.interface}\n"
            f"  RHS interface: {right.interface}"
        )

    @given(interchange_quadruple())
    @settings(max_examples=200)
    def test_flatten_same_blocks(self, quad):
        """Both sides flatten to the same set of atomic blocks."""
        f, g, h, j = quad

        left = (g >> f) | (j >> h)
        right = (g | j) >> (f | h)

        assert set(flat_names(left)) == set(flat_names(right))


# ---------------------------------------------------------------------------
# Associativity
# ---------------------------------------------------------------------------


class TestAssociativity:
    """>> and | must be associative: (a op b) op c = a op (b op c)"""

    @given(data=st.data())
    @settings(max_examples=200)
    def test_sequential_associativity(self, data):
        """(a >> b) >> c has the same interface as a >> (b >> c)."""
        token1 = data.draw(port_names)
        token2 = data.draw(port_names.filter(lambda t: t != token1))

        a = AtomicBlock(
            name="a",
            interface=Interface(
                forward_in=data.draw(port_tuples(max_size=1)),
                forward_out=(port(token1),),
            ),
        )
        b = AtomicBlock(
            name="b",
            interface=Interface(
                forward_in=(port(token1),),
                forward_out=(port(token2),),
            ),
        )
        c = AtomicBlock(
            name="c",
            interface=Interface(
                forward_in=(port(token2),),
                forward_out=data.draw(port_tuples(max_size=1)),
            ),
        )

        left = (a >> b) >> c
        right = a >> (b >> c)

        assert interface_eq(left.interface, right.interface), (
            f"Sequential associativity violated:\n"
            f"  (a >> b) >> c: {left.interface}\n"
            f"  a >> (b >> c): {right.interface}"
        )
        assert flat_names(left) == flat_names(right)

    @given(
        a=named_block(name="a"),
        b=named_block(name="b"),
        c=named_block(name="c"),
    )
    @settings(max_examples=200)
    def test_parallel_associativity(self, a, b, c):
        """(a | b) | c has the same interface as a | (b | c)."""
        left = (a | b) | c
        right = a | (b | c)

        assert interface_eq(left.interface, right.interface), (
            f"Parallel associativity violated:\n"
            f"  (a | b) | c: {left.interface}\n"
            f"  a | (b | c): {right.interface}"
        )
        assert flat_names(left) == flat_names(right)


# ---------------------------------------------------------------------------
# Commutativity of Parallel
# ---------------------------------------------------------------------------


class TestParallelCommutativity:
    """Parallel composition is commutative up to port ordering:
    a | b has the same port name sets as b | a.
    """

    @given(
        a=named_block(name="a"),
        b=named_block(name="b"),
    )
    @settings(max_examples=200)
    def test_parallel_commutativity(self, a, b):
        """a | b and b | a have the same port name sets."""
        left = a | b
        right = b | a

        assert interface_eq(left.interface, right.interface), (
            f"Parallel commutativity violated:\n"
            f"  a | b: {left.interface}\n"
            f"  b | a: {right.interface}"
        )


# ---------------------------------------------------------------------------
# Identity / Unit
# ---------------------------------------------------------------------------


class TestIdentity:
    """An empty-interface block acts as a right-identity for >> and
    as a two-sided identity for |.
    """

    @given(a=named_block(name="a"))
    @settings(max_examples=100)
    def test_parallel_right_identity(self, a):
        """a | empty has the same interface as a."""
        empty = AtomicBlock(name="empty", interface=Interface())
        comp = a | empty
        assert interface_eq(comp.interface, a.interface)

    @given(a=named_block(name="a"))
    @settings(max_examples=100)
    def test_parallel_left_identity(self, a):
        """empty | a has the same interface as a."""
        empty = AtomicBlock(name="empty", interface=Interface())
        comp = empty | a
        assert interface_eq(comp.interface, a.interface)

    @given(a=named_block(name="a"))
    @settings(max_examples=100)
    def test_sequential_right_identity(self, a):
        """a >> empty has the same interface as a."""
        empty = AtomicBlock(name="empty", interface=Interface())
        comp = a >> empty
        assert interface_eq(comp.interface, a.interface)

    @given(a=named_block(name="a"))
    @settings(max_examples=100)
    def test_sequential_left_identity(self, a):
        """empty >> a has the same interface as a."""
        empty = AtomicBlock(name="empty", interface=Interface())
        comp = empty >> a
        assert interface_eq(comp.interface, a.interface)


# ---------------------------------------------------------------------------
# Structural Properties
# ---------------------------------------------------------------------------


class TestStructuralProperties:
    """Additional algebraic properties of the composition operators."""

    @given(stackable_pair())
    @settings(max_examples=200)
    def test_sequential_flatten_order(self, pair):
        """>> preserves left-to-right order in flatten()."""
        first, second = pair
        comp = first >> second
        names = flat_names(comp)
        assert names[0] == first.name
        assert names[1] == second.name

    @given(
        a=named_block(name="a"),
        b=named_block(name="b"),
    )
    @settings(max_examples=100)
    def test_parallel_flatten_order(self, a, b):
        """| preserves left-right order in flatten()."""
        comp = a | b
        names = flat_names(comp)
        assert names == ["a", "b"]

    @given(
        a=named_block(name="a"),
        b=named_block(name="b"),
    )
    @settings(max_examples=100)
    def test_parallel_interface_is_concatenation(self, a, b):
        """| interface is tuple concatenation of both blocks'."""
        comp = a | b
        ai, bi = a.interface, b.interface
        ci = comp.interface
        assert ci.forward_in == ai.forward_in + bi.forward_in
        assert ci.forward_out == ai.forward_out + bi.forward_out
        assert ci.backward_in == ai.backward_in + bi.backward_in
        assert ci.backward_out == ai.backward_out + bi.backward_out

    @given(stackable_pair())
    @settings(max_examples=100)
    def test_sequential_interface_is_concatenation(self, pair):
        """>> interface is tuple concatenation of both blocks'."""
        first, second = pair
        comp = first >> second
        fi, si = first.interface, second.interface
        ci = comp.interface
        assert ci.forward_in == fi.forward_in + si.forward_in
        assert ci.forward_out == fi.forward_out + si.forward_out
        assert ci.backward_in == fi.backward_in + si.backward_in
        assert ci.backward_out == fi.backward_out + si.backward_out
