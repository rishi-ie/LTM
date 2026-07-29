"""Smoke tests for the installable package."""

import ltm_poc
from ltm_poc.__main__ import main


def test_package_has_a_version() -> None:
    assert ltm_poc.__version__ == "0.1.0"


def test_command_accepts_no_arguments() -> None:
    assert main([]) == 0
