"""Cross-diagram tests — verify all 6 diagram types compile through GDS pipeline."""

import pytest

from gds.canonical import project_canonical
from gds.spec import GDSSpec

from gds_software.c4.elements import C4Relationship, Container, Person
from gds_software.c4.model import C4Model
from gds_software.component.elements import Component, Connector
from gds_software.component.model import ComponentModel
from gds_software.dependency.elements import Dep, Module
from gds_software.dependency.model import DependencyModel
from gds_software.dfd.elements import DataFlow, DataStore, ExternalEntity, Process
from gds_software.dfd.model import DFDModel
from gds_software.erd.elements import Attribute, ERDEntity, ERDRelationship
from gds_software.erd.model import ERDModel
from gds_software.statemachine.elements import Event, State, Transition
from gds_software.statemachine.model import StateMachineModel
from gds_software.verification.engine import verify


@pytest.fixture
def dfd():
    return DFDModel(
        name="DFD",
        external_entities=[ExternalEntity(name="User")],
        processes=[Process(name="Auth")],
        data_stores=[DataStore(name="DB")],
        data_flows=[
            DataFlow(name="Login", source="User", target="Auth"),
            DataFlow(name="Save", source="Auth", target="DB"),
        ],
    )


@pytest.fixture
def sm():
    return StateMachineModel(
        name="SM",
        states=[State(name="Off", is_initial=True), State(name="On")],
        events=[Event(name="Toggle")],
        transitions=[
            Transition(name="TurnOn", source="Off", target="On", event="Toggle"),
            Transition(name="TurnOff", source="On", target="Off", event="Toggle"),
        ],
    )


@pytest.fixture
def comp():
    return ComponentModel(
        name="Comp",
        components=[
            Component(name="A", provides=["I"]),
            Component(name="B", requires=["I"]),
        ],
        connectors=[
            Connector(
                name="C1",
                source="A",
                source_interface="I",
                target="B",
                target_interface="I",
            ),
        ],
    )


@pytest.fixture
def c4():
    return C4Model(
        name="C4",
        persons=[Person(name="User")],
        containers=[Container(name="API")],
        relationships=[
            C4Relationship(name="Uses", source="User", target="API"),
        ],
    )


@pytest.fixture
def erd():
    return ERDModel(
        name="ERD",
        entities=[
            ERDEntity(
                name="User", attributes=[Attribute(name="id", is_primary_key=True)]
            ),
            ERDEntity(
                name="Order", attributes=[Attribute(name="id", is_primary_key=True)]
            ),
        ],
        relationships=[
            ERDRelationship(name="places", source="User", target="Order"),
        ],
    )


@pytest.fixture
def dep():
    return DependencyModel(
        name="Dep",
        modules=[Module(name="core", layer=0), Module(name="api", layer=1)],
        deps=[Dep(source="api", target="core")],
    )


class TestAllDiagramsCompile:
    """Every diagram type produces a valid GDSSpec."""

    def test_dfd_spec(self, dfd):
        spec = dfd.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

    def test_sm_spec(self, sm):
        spec = sm.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

    def test_comp_spec(self, comp):
        spec = comp.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

    def test_c4_spec(self, c4):
        spec = c4.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

    def test_erd_spec(self, erd):
        spec = erd.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0

    def test_dep_spec(self, dep):
        spec = dep.compile()
        assert isinstance(spec, GDSSpec)
        assert len(spec.blocks) > 0


class TestAllDiagramsCompileToSystem:
    """Every diagram type produces a valid SystemIR."""

    def test_dfd_system(self, dfd):
        ir = dfd.compile_system()
        assert ir.name == "DFD"
        assert len(ir.blocks) > 0

    def test_sm_system(self, sm):
        ir = sm.compile_system()
        assert ir.name == "SM"
        assert len(ir.blocks) > 0

    def test_comp_system(self, comp):
        ir = comp.compile_system()
        assert ir.name == "Comp"
        assert len(ir.blocks) > 0

    def test_c4_system(self, c4):
        ir = c4.compile_system()
        assert ir.name == "C4"
        assert len(ir.blocks) > 0

    def test_erd_system(self, erd):
        ir = erd.compile_system()
        assert ir.name == "ERD"
        assert len(ir.blocks) > 0

    def test_dep_system(self, dep):
        ir = dep.compile_system()
        assert ir.name == "Dep"
        assert len(ir.blocks) > 0


class TestAllDiagramsVerify:
    """Every diagram type can be verified."""

    def test_dfd_verify(self, dfd):
        report = verify(dfd)
        assert report.system_name == "DFD"

    def test_sm_verify(self, sm):
        report = verify(sm)
        assert report.system_name == "SM"

    def test_comp_verify(self, comp):
        report = verify(comp)
        assert report.system_name == "Comp"

    def test_c4_verify(self, c4):
        report = verify(c4)
        assert report.system_name == "C4"

    def test_erd_verify(self, erd):
        report = verify(erd)
        assert report.system_name == "ERD"

    def test_dep_verify(self, dep):
        report = verify(dep)
        assert report.system_name == "Dep"


class TestCanonicalProjection:
    """Diagram types with state produce meaningful canonical forms."""

    def test_dfd_canonical(self, dfd):
        spec = dfd.compile()
        canon = project_canonical(spec)
        # DFD has DataStore → has mechanisms (state update f)
        assert len(canon.mechanism_blocks) > 0 or len(canon.policy_blocks) > 0

    def test_sm_canonical(self, sm):
        spec = sm.compile()
        canon = project_canonical(spec)
        assert len(canon.mechanism_blocks) > 0 or len(canon.policy_blocks) > 0

    def test_dep_canonical_stateless(self, dep):
        spec = dep.compile()
        canon = project_canonical(spec)
        # Dependency graphs are stateless: h = g (no mechanisms)
        assert len(canon.mechanism_blocks) == 0
