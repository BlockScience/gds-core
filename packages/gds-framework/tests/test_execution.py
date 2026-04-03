"""Tests for ExecutionContract dataclass."""

import pytest

from gds.execution import ExecutionContract


class TestExecutionContractConstruction:
    """Construction and validation of ExecutionContract."""

    def test_discrete_default_params(self):
        """Discrete contract with default synchrony/ordering."""
        c = ExecutionContract(time_domain="discrete")
        assert c.time_domain == "discrete"
        assert c.synchrony == "synchronous"
        assert c.observation_delay == 0
        assert c.update_ordering == "Moore"

    def test_discrete_explicit_params(self):
        """Discrete contract with explicit Mealy ordering."""
        c = ExecutionContract(
            time_domain="discrete",
            synchrony="asynchronous",
            observation_delay=1,
            update_ordering="Mealy",
        )
        assert c.synchrony == "asynchronous"
        assert c.observation_delay == 1
        assert c.update_ordering == "Mealy"

    def test_atemporal(self):
        """Atemporal contract with defaults."""
        c = ExecutionContract(time_domain="atemporal")
        assert c.time_domain == "atemporal"
        assert c.synchrony == "synchronous"

    def test_continuous(self):
        """Continuous contract with defaults."""
        c = ExecutionContract(time_domain="continuous")
        assert c.time_domain == "continuous"

    def test_event(self):
        """Event-driven contract with defaults."""
        c = ExecutionContract(time_domain="event")
        assert c.time_domain == "event"

    def test_frozen(self):
        """ExecutionContract is immutable."""
        c = ExecutionContract(time_domain="discrete")
        with pytest.raises(AttributeError):
            c.time_domain = "continuous"  # type: ignore[misc]


class TestExecutionContractValidation:
    """Post-init validation of discrete-only fields."""

    def test_non_discrete_rejects_synchrony(self):
        """Non-discrete with non-default synchrony raises ValueError."""
        with pytest.raises(ValueError, match="synchrony"):
            ExecutionContract(time_domain="continuous", synchrony="asynchronous")

    def test_non_discrete_rejects_observation_delay(self):
        """Non-discrete with non-zero observation_delay raises ValueError."""
        with pytest.raises(ValueError, match="observation_delay"):
            ExecutionContract(time_domain="atemporal", observation_delay=1)

    def test_non_discrete_rejects_update_ordering(self):
        """Non-discrete with non-Moore update_ordering raises ValueError."""
        with pytest.raises(ValueError, match="update_ordering"):
            ExecutionContract(time_domain="event", update_ordering="Mealy")

    def test_non_discrete_defaults_ok(self):
        """Non-discrete with all defaults is fine."""
        c = ExecutionContract(time_domain="continuous")
        assert c.synchrony == "synchronous"
        assert c.observation_delay == 0
        assert c.update_ordering == "Moore"


class TestExecutionContractCompatibility:
    """Compatibility checking between contracts."""

    def test_same_domain_compatible(self):
        """Two discrete contracts are compatible."""
        a = ExecutionContract(time_domain="discrete")
        b = ExecutionContract(time_domain="discrete", update_ordering="Mealy")
        assert a.is_compatible_with(b)

    def test_different_domain_incompatible(self):
        """Discrete and continuous are incompatible."""
        a = ExecutionContract(time_domain="discrete")
        b = ExecutionContract(time_domain="continuous")
        assert not a.is_compatible_with(b)

    def test_atemporal_universal_donor(self):
        """Atemporal is compatible with everything."""
        at = ExecutionContract(time_domain="atemporal")
        d = ExecutionContract(time_domain="discrete")
        c = ExecutionContract(time_domain="continuous")
        e = ExecutionContract(time_domain="event")

        assert at.is_compatible_with(d)
        assert at.is_compatible_with(c)
        assert at.is_compatible_with(e)
        assert d.is_compatible_with(at)
        assert c.is_compatible_with(at)
        assert e.is_compatible_with(at)

    def test_atemporal_with_atemporal(self):
        """Two atemporal contracts are compatible."""
        a = ExecutionContract(time_domain="atemporal")
        b = ExecutionContract(time_domain="atemporal")
        assert a.is_compatible_with(b)

    def test_symmetry(self):
        """Compatibility is symmetric."""
        a = ExecutionContract(time_domain="discrete")
        b = ExecutionContract(time_domain="continuous")
        assert a.is_compatible_with(b) == b.is_compatible_with(a)
