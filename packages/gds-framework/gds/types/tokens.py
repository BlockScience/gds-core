"""Signature tokenization for structural type comparison.

The token system is the foundation of the type checker. Rather than requiring
exact string equality between port names and wiring labels, it splits
signatures into normalized tokens and checks set relationships.
"""

from __future__ import annotations

import unicodedata


def tokenize(signature: str) -> frozenset[str]:
    """Tokenize a signature string into a normalized frozen set of tokens.

    Splitting rules (applied in order):
    1. Apply Unicode NFC normalization (so that e.g. é as base+combining
       matches precomposed é).
    2. Split on ' + ' (the compound-type joiner).
    3. Split each part on ', ' (comma-space).
    4. Strip whitespace and lowercase each token.
    5. Discard empty strings.
    """
    if not signature:
        return frozenset()
    signature = unicodedata.normalize("NFC", signature)
    tokens: set[str] = set()
    for plus_part in signature.split(" + "):
        for comma_part in plus_part.split(", "):
            normalized = comma_part.strip().lower()
            if normalized:
                tokens.add(normalized)
    return frozenset(tokens)


def tokens_subset(child: str, parent: str) -> bool:
    """Return True if every token in *child* appears in *parent*.

    Returns True if child is empty (vacuous truth).
    """
    child_tokens = tokenize(child)
    if not child_tokens:
        return True
    return child_tokens <= tokenize(parent)


def tokens_overlap(a: str, b: str) -> bool:
    """Return True if *a* and *b* share at least one token."""
    a_tokens = tokenize(a)
    b_tokens = tokenize(b)
    if not a_tokens or not b_tokens:
        return False
    return bool(a_tokens & b_tokens)
