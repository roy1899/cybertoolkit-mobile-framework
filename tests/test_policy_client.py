from engine.core.policy_client import PolicyClient
from engine.policy.policy_engine import PolicyEngine
from engine.policy.schema import Capability


def test_policy_client_delegates_to_engine_with_module_name():
    engine = PolicyEngine(profile_name="safe")
    client = PolicyClient(engine, module_name="context_detector")
    decision = client.request(Capability.PASSIVE_LOCAL)
    assert decision.allowed


def test_policy_client_forwards_target():
    engine = PolicyEngine(profile_name="home_lab")
    client = PolicyClient(engine, module_name="port_scanner")
    decision = client.request(Capability.ACTIVE_PROBE, target="192.168.1.5")
    assert decision.allowed

    denied = client.request(Capability.ACTIVE_PROBE, target="8.8.8.8")
    assert not denied.allowed
