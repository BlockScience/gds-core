"""Tests for View 2 — Canonical GDS renderer."""

from gds.canonical import CanonicalGDS
from gds.parameters import ParameterDef, ParameterSchema
from gds.types.typedef import TypeDef
from gds_viz.canonical import canonical_to_mermaid


class TestCanonicalMinimal:
    def test_empty_canonical_renders_x_nodes(self):
        c = CanonicalGDS()
        out = canonical_to_mermaid(c)
        assert "flowchart LR" in out
        assert "X_t" in out
        assert "X_next" in out

    def test_empty_canonical_no_subgraphs(self):
        c = CanonicalGDS()
        out = canonical_to_mermaid(c)
        assert "subgraph" not in out

    def test_state_variables_listed_in_x_nodes(self):
        c = CanonicalGDS(
            state_variables=(("Pop", "count"), ("Pop", "growth")),
        )
        out = canonical_to_mermaid(c)
        assert "count" in out
        assert "growth" in out

    def test_duplicate_variable_names_qualified_with_entity(self):
        c = CanonicalGDS(
            state_variables=(("S", "count"), ("I", "count"), ("R", "count")),
        )
        out = canonical_to_mermaid(c)
        assert "S.count" in out
        assert "I.count" in out
        assert "R.count" in out


class TestCanonicalSubgraphs:
    def test_boundary_subgraph_rendered(self):
        c = CanonicalGDS(boundary_blocks=("Sensor",))
        out = canonical_to_mermaid(c)
        assert "subgraph U" in out
        assert "Boundary (U)" in out
        assert "Sensor" in out

    def test_policy_subgraph_rendered(self):
        c = CanonicalGDS(policy_blocks=("Decide",))
        out = canonical_to_mermaid(c)
        assert "subgraph g" in out
        assert "Policy (g)" in out

    def test_mechanism_subgraph_rendered(self):
        c = CanonicalGDS(mechanism_blocks=("Update",))
        out = canonical_to_mermaid(c)
        assert "subgraph f" in out
        assert "Mechanism (f)" in out

    def test_control_subgraph_only_when_present(self):
        c = CanonicalGDS(mechanism_blocks=("Update",))
        out = canonical_to_mermaid(c)
        assert "Control" not in out

        c2 = CanonicalGDS(control_blocks=("Ctrl",))
        out2 = canonical_to_mermaid(c2)
        assert "subgraph ctrl" in out2
        assert "Control" in out2

    def test_empty_role_omitted(self):
        c = CanonicalGDS(
            boundary_blocks=("Sensor",),
            mechanism_blocks=("Update",),
        )
        out = canonical_to_mermaid(c)
        assert "Policy (g)" not in out


class TestCanonicalParameters:
    def _make_params(self, *names: str) -> ParameterSchema:
        ps = ParameterSchema()
        for n in names:
            ps = ps.add(
                ParameterDef(name=n, typedef=TypeDef(name=n, python_type=float))
            )
        return ps

    def test_theta_shown_when_params_exist(self):
        c = CanonicalGDS(
            parameter_schema=self._make_params("beta", "gamma"),
            policy_blocks=("P",),
            mechanism_blocks=("M",),
        )
        out = canonical_to_mermaid(c)
        assert "Theta" in out
        assert "beta" in out
        assert "gamma" in out

    def test_theta_hidden_when_no_params(self):
        c = CanonicalGDS()
        out = canonical_to_mermaid(c)
        assert "Theta" not in out

    def test_theta_hidden_when_show_parameters_false(self):
        c = CanonicalGDS(
            parameter_schema=self._make_params("beta"),
            policy_blocks=("P",),
        )
        out = canonical_to_mermaid(c, show_parameters=False)
        assert "Theta" not in out

    def test_theta_edges_to_g_and_f(self):
        c = CanonicalGDS(
            parameter_schema=self._make_params("rate"),
            policy_blocks=("P",),
            mechanism_blocks=("M",),
        )
        out = canonical_to_mermaid(c)
        assert "Theta -.-> g" in out
        assert "Theta -.-> f" in out


class TestCanonicalEdges:
    def test_update_edges_labeled_by_default(self):
        c = CanonicalGDS(
            mechanism_blocks=("UpdatePop",),
            update_map=(("UpdatePop", (("Pop", "count"),)),),
        )
        out = canonical_to_mermaid(c)
        assert "UpdatePop -.-> |Pop.count| X_next" in out

    def test_update_edges_plain_when_show_updates_false(self):
        c = CanonicalGDS(
            mechanism_blocks=("UpdatePop",),
            update_map=(("UpdatePop", (("Pop", "count"),)),),
        )
        out = canonical_to_mermaid(c, show_updates=False)
        assert "UpdatePop --> X_next" in out
        assert "Pop.count" not in out

    def test_control_feedback_edges(self):
        c = CanonicalGDS(
            policy_blocks=("P",),
            mechanism_blocks=("M",),
            control_blocks=("Ctrl",),
        )
        out = canonical_to_mermaid(c)
        assert "f -.-> Ctrl" in out
        assert "Ctrl -.-> g" in out

    def test_block_names_with_spaces_sanitized(self):
        c = CanonicalGDS(boundary_blocks=("My Sensor",))
        out = canonical_to_mermaid(c)
        assert "My_Sensor" in out


class TestCanonicalIntegration:
    def test_sir_epidemic(self):
        sir = __import__("pytest").importorskip("sir_epidemic")
        from gds.canonical import project_canonical

        spec = sir.model.build_spec()
        canon = project_canonical(spec)
        out = canonical_to_mermaid(canon)

        assert "flowchart LR" in out
        # 3 entities all have "count" — should be qualified
        assert "Susceptible.count" in out
        assert "Infected.count" in out
        assert "Recovered.count" in out
        # Roles present
        assert "Boundary (U)" in out
        assert "Policy (g)" in out
        assert "Mechanism (f)" in out
        # Parameters
        assert "Theta" in out
        assert "beta" in out
        # Update edges
        assert "X_next" in out

    def test_thermostat_has_control(self):
        thermo = __import__("pytest").importorskip("thermostat")
        from gds.canonical import project_canonical

        spec = thermo.model.build_spec()
        canon = project_canonical(spec)
        out = canonical_to_mermaid(canon)

        assert "Control" in out
        assert "Room_Plant" in out
