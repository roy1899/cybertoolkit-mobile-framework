"""
Base contract for every analysis module.

A module:
  - declares a `name` and `description`
  - receives a PolicyClient at construction time
  - implements `run(**kwargs) -> dict`
  - calls `self.policy.request(capability, target=...)` for every capability
    it needs, BEFORE doing the corresponding work, and honors the decision
    it gets back.

Modules must never import engine.policy.policy_engine directly, and must
never contain their own notion of "is this network public" or "am I
authorized". That logic belongs exclusively to the Execution Policy engine.
This keeps modules simple, testable in isolation (mock the PolicyClient),
and keeps all security-relevant logic in one auditable place.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from engine.core.policy_client import PolicyClient


class Module(ABC):
    name: str = "unnamed_module"
    description: str = ""

    def __init__(self, policy: PolicyClient):
        self.policy = policy

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the module and return a JSON-serializable result dict.

        Convention: always include a "status" key, one of
        "ok" | "denied" | "error", so the CLI and any future reporting
        module can handle results uniformly.
        """
        raise NotImplementedError
