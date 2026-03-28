# Representability

The formal representability analysis classifies which GDS concepts can and cannot be represented in OWL/SHACL/SPARQL.

See the full analysis: [formal-representability.md](../../research/formal-representability.md)

## Key Results

The canonical decomposition `h = f . g` is the representation boundary:

- **g** (policy mapping) is entirely R1 — fully representable in OWL
- **f_struct** (update map: "who updates what") is R1
- **f_behav** (transition function: "how values change") is R3 — not representable

## Verification Check Classification

| Tier | Checks | Count |
|------|--------|-------|
| R1 (SHACL-core) | G-002, SC-005..SC-009 | 6 |
| R2 (SPARQL) | G-004, G-006, SC-001..SC-004 | 6 |
| R3 (Python-only) | G-001, G-005 | 2 |
| Mixed | G-003 (flags R1, ports R3) | 1 |
