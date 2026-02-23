# Changelog

## gds-framework v0.2.3

- Add `StructuralWiring` to public API (compiler intermediate for domain DSL wiring emitters)
- Switch to dynamic versioning — `__version__` in `__init__.py` is the single source of truth
- Tighten `gds-framework>=0.2.3` lower bound across all dependent packages

## gds-games v0.2.0

- Add canonical bridge (`compile_pattern_to_spec`) — projects OGS patterns to `GDSSpec`
- Add view stratification architecture
- Require `gds-framework>=0.2.3`

## gds-stockflow v0.1.0

- Initial release — declarative stock-flow DSL over GDS semantics

## gds-control v0.1.0

- Initial release — state-space control DSL over GDS semantics

## gds-viz v0.1.2

- Mermaid renderers for structural, canonical, architecture, parameter, and traceability views
