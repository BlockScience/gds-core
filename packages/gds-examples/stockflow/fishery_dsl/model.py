"""Gordon-Schaefer Fishery — StockFlow DSL variant.

Same fishery as fishery/model.py, expressed using the declarative
StockFlowModel DSL. The DSL auto-generates types, spaces, entities,
blocks, wiring, and TransitionSignatures.

GDS Decomposition (auto-generated):
    X  = Fish Population level
    U  = {Growth Rate r, Carrying Capacity K, Catchability q, Effort e}
    g  = {converters, auxiliaries, flows}
    f  = {Fish Population Accumulation}
    Theta = {Growth Rate r, Carrying Capacity K, Catchability q, Effort e}

Note: This DSL variant models the AGGREGATE fishery (total effort as
exogenous input). Individual fisher decisions and game-theoretic
analysis require the raw GDS model or the OGS game formulation.
"""

from gds.canonical import CanonicalGDS, project_canonical
from gds.ir.models import SystemIR
from gds.spec import GDSSpec
from stockflow.dsl.compile import compile_model, compile_to_system
from stockflow.dsl.elements import Auxiliary, Converter, Flow, Stock
from stockflow.dsl.model import StockFlowModel


def build_model() -> StockFlowModel:
    """Declare the Gordon-Schaefer fishery as a stock-flow model.

    Stock: Fish Population (biomass, non-negative)
    Inflow: Natural Growth = r * N * (1 - N/K) - m * N
    Outflow: Harvest = q * E * N

    Converters provide exogenous parameters. Auxiliaries compute
    density-dependent rates from stock levels and parameters.
    """
    return StockFlowModel(
        name="Gordon-Schaefer Fishery",
        stocks=[
            Stock(name="Fish Population", initial=50_000.0, non_negative=True),
        ],
        flows=[
            Flow(name="Natural Growth", target="Fish Population"),
            Flow(name="Harvest", source="Fish Population"),
        ],
        auxiliaries=[
            Auxiliary(
                name="Growth Rate Calc",
                inputs=[
                    "Fish Population",
                    "Intrinsic Growth Rate",
                    "Carrying Capacity",
                    "Mortality Rate",
                ],
            ),
            Auxiliary(
                name="Harvest Rate Calc",
                inputs=[
                    "Fish Population",
                    "Catchability",
                    "Total Effort",
                ],
            ),
        ],
        converters=[
            Converter(name="Intrinsic Growth Rate"),
            Converter(name="Carrying Capacity"),
            Converter(name="Catchability"),
            Converter(name="Mortality Rate"),
            Converter(name="Total Effort"),
        ],
        description=(
            "Gordon-Schaefer common-pool fishery: logistic growth with "
            "bilinear harvest function H = q * E * N."
        ),
    )


def build_spec() -> GDSSpec:
    """Compile to GDSSpec (specification registry)."""
    return compile_model(build_model())


def build_system() -> SystemIR:
    """Compile to SystemIR (flat IR with composition tree)."""
    return compile_to_system(build_model())


def build_canonical() -> CanonicalGDS:
    """Project the canonical form h = f . g."""
    return project_canonical(build_spec())
