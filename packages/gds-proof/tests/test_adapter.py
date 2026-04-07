"""Tests for gds_proof.adapter — GDS framework integration layer."""

from __future__ import annotations

import sympy
from gds import (
    GDSSpec,
    Mechanism,
    interface,
)

from gds_proof import (
    GDSSymbolicBlock,
    analyze_inductive_safety,
    analyze_invariants,
    derive_state_symbols,
    hash_model,
)
from tests.conftest import ACCOUNT_ENTITY, Balance, U, X


class TestDeriveStateSymbols:
    """derive_state_symbols extracts symbols from updates + variables."""

    def test_derives_from_entity_symbol_field(self):
        """When StateVariable.symbol is set, use that as the symbol name."""
        spec = GDSSpec(name="test")
        spec.collect(Balance, ACCOUNT_ENTITY)
        mechanism = Mechanism(
            name="m",
            interface=interface(forward_in=["cmd"]),
            updates=[("Account", "balance")],
        )
        spec.register_block(mechanism)

        symbols = derive_state_symbols(mechanism, spec)
        assert symbols == frozenset({sympy.Symbol("x_prev")})

    def test_falls_back_to_namespaced_default(self):
        """When StateVariable.symbol is empty, use entity_variable format."""
        from gds import Entity, state_var, typedef

        spec = GDSSpec(name="test")
        nosym_entity = Entity(
            name="Wallet",
            variables={"coins": state_var(typedef("Coins", int))},
        )
        spec.collect(typedef("Coins", int), nosym_entity)
        mechanism = Mechanism(
            name="m",
            interface=interface(forward_in=["cmd"]),
            updates=[("Wallet", "coins")],
        )
        spec.register_block(mechanism)

        symbols = derive_state_symbols(mechanism, spec)
        assert symbols == frozenset({sympy.Symbol("Wallet_coins")})


class TestGDSSymbolicBlock:
    """GDSSymbolicBlock wraps an AtomicBlock with symbolic expressions."""

    def test_satisfies_protocol(self, gds_withdrawal_spec):
        """GDSSymbolicBlock satisfies the SymbolicBlock protocol."""
        from gds_proof.protocols import SymbolicBlock

        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"x_prev": X - U},
            inputs=frozenset({U}),
        )
        assert isinstance(block, SymbolicBlock)

    def test_derives_prev_state_from_mechanism(self, gds_withdrawal_spec):
        """prev_state_symbols auto-derived from Mechanism.updates."""
        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"x_prev": X - U},
        )
        assert block.prev_state_symbols == frozenset({X})

    def test_explicit_prev_state_overrides(self, gds_withdrawal_spec):
        """Explicit prev_state takes precedence over auto-derivation."""
        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        custom = frozenset({sympy.Symbol("custom")})
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"custom": X - U},
            prev_state=custom,
        )
        assert block.prev_state_symbols == custom

    def test_substitution_maps_state_and_output(self, gds_withdrawal_spec):
        """substitution() maps both state symbols and output symbols."""
        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"x_prev": X - U},
            output_expressions={"balance": X - U},
            inputs=frozenset({U}),
        )
        subs = block.substitution()
        assert subs[X] == X - U
        assert subs[sympy.Symbol("balance")] == X - U

    def test_name_comes_from_gds_block(self, gds_withdrawal_spec):
        """Block name delegates to the underlying GDS block."""
        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"x_prev": X - U},
        )
        assert block.name == "withdrawal"

    def test_block_property_returns_gds_block(self, gds_withdrawal_spec):
        """The .block property returns the underlying AtomicBlock."""
        spec = gds_withdrawal_spec
        mechanism = spec.blocks["withdrawal"]
        block = GDSSymbolicBlock(
            block=mechanism,
            spec=spec,
            state_transition={"x_prev": X - U},
        )
        assert block.block is mechanism


class TestGDSSymbolicModel:
    """GDSSymbolicModel wraps a GDSSpec with enrichments."""

    def test_satisfies_protocol(self, gds_withdrawal_model):
        """GDSSymbolicModel satisfies the SymbolicModel protocol."""
        from gds_proof.protocols import SymbolicModel

        assert isinstance(gds_withdrawal_model, SymbolicModel)

    def test_spec_property(self, gds_withdrawal_model):
        """The .spec property returns the underlying GDSSpec."""
        assert gds_withdrawal_model.spec.name == "bank_account"

    def test_canonical_dict_includes_spec_name(self, gds_withdrawal_model):
        """canonical_dict includes the spec name."""
        cd = gds_withdrawal_model.canonical_dict()
        assert cd["spec_name"] == "bank_account"

    def test_canonical_dict_includes_entities(self, gds_withdrawal_model):
        """canonical_dict includes entity names from the spec."""
        cd = gds_withdrawal_model.canonical_dict()
        assert "Account" in cd["entities"]

    def test_analyze_invariants_integration(self, gds_withdrawal_model):
        """Full end-to-end: analyze_invariants with GDS-backed model."""
        result = analyze_invariants(gds_withdrawal_model)
        assert len(result.results) == 1  # 1 invariant x 1 block
        r = result.results[0]
        assert r.invariant_name == "balance_nonneg"
        assert r.mechanism_name == "withdrawal"
        # Withdrawal is not DISPROVED — the predicate prevents violation.
        # SymPy may resolve to PROVED or INCONCLUSIVE depending on version.
        assert r.status != "DISPROVED"
        assert r.proof_method is not None

    def test_analyze_inductive_safety_integration(self, gds_withdrawal_model):
        """Full end-to-end: analyze_inductive_safety with GDS-backed model."""
        result = analyze_inductive_safety(gds_withdrawal_model)
        assert len(result.single_step) == 1
        # Not DISPROVED — the withdrawal predicate guards against violation
        assert result.single_step[0].verdict.value != "DISPROVED"

    def test_hash_model_integration(self, gds_withdrawal_model):
        """hash_model works with GDS-backed model."""
        h = hash_model(gds_withdrawal_model)
        assert len(h) == 64
        # Deterministic
        assert h == hash_model(gds_withdrawal_model)


class TestFindingsIntegration:
    """Test the findings.py conversion layer."""

    def test_symbolic_analysis_to_findings(self, gds_withdrawal_model):
        """Convert symbolic analysis results to Finding objects."""
        from gds_proof.findings import symbolic_analysis_to_findings

        result = analyze_invariants(gds_withdrawal_model)
        findings = symbolic_analysis_to_findings(result)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "PROOF-001"
        assert "withdrawal" in f.message
        # Not an error — withdrawal is at worst INCONCLUSIVE, never DISPROVED
        assert f.severity.value != "error"

    def test_proof_findings_to_report(self, gds_withdrawal_model):
        """Wrap findings in a VerificationReport."""
        from gds_proof.findings import (
            proof_findings_to_report,
            symbolic_analysis_to_findings,
        )

        result = analyze_invariants(gds_withdrawal_model)
        findings = symbolic_analysis_to_findings(result)
        report = proof_findings_to_report("bank_account", findings)
        assert report.system_name == "bank_account"
        assert report.checks_total == 1
        assert report.errors == 0

    def test_exportable_predicate_populated(self, gds_withdrawal_model):
        """exportable_predicate is set when invariant_expr is provided."""
        from gds_proof.findings import symbolic_analysis_to_findings

        result = analyze_invariants(gds_withdrawal_model)
        inv_exprs = {
            name: inv.expr for name, inv in gds_withdrawal_model.invariants().items()
        }
        findings = symbolic_analysis_to_findings(result, inv_exprs)
        assert findings[0].exportable_predicate != ""
