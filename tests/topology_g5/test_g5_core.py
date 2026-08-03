from topology_g5.frontier import run_candidate
from topology_g5.generator import build_dataset, validate_dataset
from topology_g5.summaries import SummaryCatalog
from topology_g5.summary_index import SummaryIndexes


def test_summary_catalog_is_sound_and_base_certifies():
    dataset = build_dataset(1733, 2_000, 12); validate_dataset(dataset)
    catalog = SummaryCatalog(dataset["store"], dataset["influences"], dataset["summary_modes"]); indexes = SummaryIndexes(catalog)
    base = next(row for row in dataset["cases"] if row["variant"] == "base")
    result = run_candidate(dataset, catalog, indexes, base)
    assert result.disposition == "certified"


def test_answer_changing_twin_widens_or_abstains():
    dataset = build_dataset(1733, 4_000, 40); catalog = SummaryCatalog(dataset["store"], dataset["influences"], dataset["summary_modes"]); indexes = SummaryIndexes(catalog)
    twin = next(row for row in dataset["cases"] if row["variant"] == "twin" and dataset["summary_modes"][row["remote_region"]] == "quantized")
    result = run_candidate(dataset, catalog, indexes, twin)
    assert result.widening_rounds > 0 or result.disposition == "abstain"


def test_uncertifiable_region_abstains():
    dataset = build_dataset(1733, 4_000, 40); catalog = SummaryCatalog(dataset["store"], dataset["influences"], dataset["summary_modes"]); indexes = SummaryIndexes(catalog)
    twin = next(row for row in dataset["cases"] if row["variant"] == "twin" and dataset["summary_modes"][row["remote_region"]] == "unbounded")
    assert run_candidate(dataset, catalog, indexes, twin).disposition == "abstain"
