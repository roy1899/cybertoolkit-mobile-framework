"""
Ensures context_detector tests never make a real network call by default.
Individual tests can still override urllib.request.urlopen explicitly if
they need to test captive-portal-specific behavior.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _no_real_network_by_default():
    """By default, simulate a normal (non-captive-portal) 204 response so
    tests that don't care about captive portal detection aren't slowed
    down or made flaky by real network access.
    """

    class FakeResponse:
        status = 204

        def read(self):
            return b""

        def geturl(self):
            return "http://connectivitycheck.gstatic.com/generate_204"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    with patch("urllib.request.urlopen", return_value=FakeResponse()):
        yield
