"""Domain analysis report generator with advanced tag-based insights."""

from jinja2 import Environment, PackageLoader

from ogs.ir.models import PatternIR


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment loading from the templates directory."""
    return Environment(
        loader=PackageLoader("ogs.reports", "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _analyze_domains(pattern: PatternIR, tag_key: str = "domain") -> dict:
    """Analyze patterns by domain/tag with cross-domain flow detection."""
    # Group games by domain
    domains: dict[str, list] = {}
    ungrouped = []

    for game in pattern.games:
        tag_value = game.tags.get(tag_key) if game.tags else None
        if tag_value:
            domains.setdefault(tag_value, []).append(game)
        else:
            ungrouped.append(game)

    # Analyze flows
    internal_flows: dict[str, list] = {d: [] for d in domains}
    external_flows: list[dict] = []

    for flow in pattern.flows:
        source_domain = None
        target_domain = None

        # Find domains for source and target
        for game in pattern.games:
            if game.name == flow.source:
                source_domain = game.tags.get(tag_key) if game.tags else None
            if game.name == flow.target:
                target_domain = game.tags.get(tag_key) if game.tags else None

        if source_domain and target_domain:
            if source_domain == target_domain:
                internal_flows[source_domain].append(flow)
            else:
                external_flows.append(
                    {
                        "flow": flow,
                        "source_domain": source_domain,
                        "target_domain": target_domain,
                    }
                )

    # Build interaction matrix
    domain_names = sorted(domains.keys())
    interaction_matrix: dict[str, dict[str, int]] = {}

    for src in domain_names:
        interaction_matrix[src] = {}
        for tgt in domain_names:
            if src == tgt:
                interaction_matrix[src][tgt] = len(internal_flows[src])
            else:
                count = sum(
                    1
                    for ef in external_flows
                    if ef["source_domain"] == src and ef["target_domain"] == tgt
                )
                interaction_matrix[src][tgt] = count

    # Calculate coupling metrics
    coupling = {}
    for domain in domain_names:
        outgoing = sum(1 for ef in external_flows if ef["source_domain"] == domain)
        incoming = sum(1 for ef in external_flows if ef["target_domain"] == domain)
        internal = len(internal_flows[domain])
        total = outgoing + incoming + internal

        coupling[domain] = {
            "outgoing": outgoing,
            "incoming": incoming,
            "internal": internal,
            "total": total,
            "coupling_ratio": (outgoing + incoming) / total if total > 0 else 0,
        }

    return {
        "domains": domains,
        "ungrouped": ungrouped,
        "internal_flows": internal_flows,
        "external_flows": external_flows,
        "interaction_matrix": interaction_matrix,
        "coupling": coupling,
        "domain_names": domain_names,
    }


def generate_domain_analysis(pattern: PatternIR, tag_key: str = "domain") -> str:
    """Generate a domain analysis report with tag-based insights."""
    env = _get_jinja_env()
    template = env.get_template("domain_analysis.md.j2")

    analysis = _analyze_domains(pattern, tag_key)

    return template.render(
        pattern=pattern,
        tag_key=tag_key,
        **analysis,
    )
