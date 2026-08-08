from pathlib import Path

from ltm_a2.audit import run_audit


def test_audit_replays_all_profiles_and_retains_compiler_boundary(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    result = run_audit(root, tmp_path)

    assert result["representation_scenario_agreement"] is True
    assert result["verdicts"]["controlled_ltm_v1"] == "CONDITIONAL_GO"
    assert result["verdicts"]["unrestricted_full_vision"] == "PLAUSIBLE_BUT_UNPROVEN"
    finding = result["critical_findings"][0]
    assert finding["verdict"] == "BOUNDARY_GAP"
    assert (tmp_path / "audit-results.json").exists()
