import pytest

from engine.policy.policy_engine import PolicyEngine
from engine.policy.schema import AuthorizationRequest, Capability


def test_safe_profile_allows_passive_local():
    engine = PolicyEngine(profile_name="safe")
    decision = engine.authorize(
        AuthorizationRequest(module_name="context_detector", capability=Capability.PASSIVE_LOCAL)
    )
    assert decision.allowed


def test_safe_profile_denies_active_probe():
    engine = PolicyEngine(profile_name="safe")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner",
            capability=Capability.ACTIVE_PROBE,
            target="192.168.1.10",
        )
    )
    assert not decision.allowed
    assert "safe" in decision.reason


def test_active_intrusive_is_hard_denied_on_every_profile():
    for profile_name in ("safe", "home_lab", "authorized_client", "research", "developer"):
        engine = PolicyEngine(profile_name=profile_name)
        decision = engine.authorize(
            AuthorizationRequest(
                module_name="whatever", capability=Capability.ACTIVE_INTRUSIVE, target="1.2.3.4"
            )
        )
        assert not decision.allowed, f"{profile_name} must never allow ACTIVE_INTRUSIVE"
        assert "permanently disabled" in decision.reason


def test_home_lab_allows_probe_within_declared_range():
    engine = PolicyEngine(profile_name="home_lab")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner", capability=Capability.ACTIVE_PROBE, target="192.168.1.10"
        )
    )
    assert decision.allowed


def test_home_lab_denies_probe_outside_declared_range():
    engine = PolicyEngine(profile_name="home_lab")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner", capability=Capability.ACTIVE_PROBE, target="8.8.8.8"
        )
    )
    assert not decision.allowed


def test_authorized_client_denies_probe_before_explicit_authorization():
    engine = PolicyEngine(profile_name="authorized_client")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner",
            capability=Capability.ACTIVE_PROBE,
            target="203.0.113.10",
        )
    )
    assert not decision.allowed


def test_authorized_client_allows_probe_after_authorize_scope():
    engine = PolicyEngine(profile_name="authorized_client")
    engine.authorize_scope("203.0.113.0/24")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner",
            capability=Capability.ACTIVE_PROBE,
            target="203.0.113.10",
        )
    )
    assert decision.allowed


def test_authorized_client_can_be_confirmed_at_construction_time():
    engine = PolicyEngine(
        profile_name="authorized_client", authorized_scopes=["203.0.113.0/24"]
    )
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner",
            capability=Capability.ACTIVE_PROBE,
            target="203.0.113.10",
        )
    )
    assert decision.allowed


def test_developer_profile_denies_all_active_capabilities():
    engine = PolicyEngine(profile_name="developer")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner", capability=Capability.ACTIVE_PROBE, target="127.0.0.1"
        )
    )
    assert not decision.allowed


def test_unknown_profile_raises():
    with pytest.raises(ValueError):
        PolicyEngine(profile_name="does_not_exist")


def test_hostname_target_matches_exact_scope_string():
    engine = PolicyEngine(profile_name="authorized_client")
    engine.authorize_scope("internal-app.client.example")
    decision = engine.authorize(
        AuthorizationRequest(
            module_name="port_scanner",
            capability=Capability.ACTIVE_PROBE,
            target="internal-app.client.example",
        )
    )
    assert decision.allowed
