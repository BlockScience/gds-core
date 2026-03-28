"""Tests for GDS OWL namespace constants."""

from rdflib import Namespace

from gds_owl._namespace import (
    DEFAULT_BASE_URI,
    GDS,
    GDS_CORE,
    GDS_IR,
    GDS_VERIF,
    PREFIXES,
)


class TestNamespaceURIs:
    def test_base_namespace_is_well_formed(self) -> None:
        assert str(GDS).startswith("https://")
        assert str(GDS).endswith("/")

    def test_sub_namespaces_extend_base(self) -> None:
        base = str(GDS)
        assert str(GDS_CORE).startswith(base)
        assert str(GDS_IR).startswith(base)
        assert str(GDS_VERIF).startswith(base)

    def test_sub_namespaces_are_distinct(self) -> None:
        uris = {str(GDS_CORE), str(GDS_IR), str(GDS_VERIF)}
        assert len(uris) == 3

    def test_prefixes_cover_all_namespaces(self) -> None:
        assert "gds" in PREFIXES
        assert "gds-core" in PREFIXES
        assert "gds-ir" in PREFIXES
        assert "gds-verif" in PREFIXES

    def test_prefixes_are_namespace_instances(self) -> None:
        for ns in PREFIXES.values():
            assert isinstance(ns, Namespace)

    def test_uriref_generation(self) -> None:
        block_uri = GDS_CORE["Block"]
        assert str(block_uri) == "https://gds.block.science/ontology/core/Block"

    def test_default_base_uri(self) -> None:
        assert DEFAULT_BASE_URI.startswith("https://")
        assert DEFAULT_BASE_URI.endswith("/")
