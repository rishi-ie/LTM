"""Deterministic ingestion checks."""

from ltm_poc.ingest import ingest


def test_ingests_supported_formats_in_stable_order(tmp_path) -> None:
    (tmp_path / "b.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "a.json").write_text('{"b": true, "a": [2, null]}', encoding="utf-8")
    (tmp_path / "rows.csv").write_text("name,score\nAda,10\n", encoding="utf-8")
    (tmp_path / "events.jsonl").write_text(
        '{"z": "one"}\n{"a": "two"}\n', encoding="utf-8"
    )
    (tmp_path / "blob.bin").write_bytes(b"\x00")

    result = ingest(tmp_path)

    assert [record.record_id for record in result.records] == [
        "a.json::000000",
        "b.txt::000000",
        "events.jsonl::000000",
        "events.jsonl::000001",
        "rows.csv::000000",
    ]
    assert result.records[0].text == "a.0: 2\na.1: null\nb: true"
    assert result.records[-1].text == "name: Ada\nscore: 10"
    assert result.skipped_files == ["blob.bin"]


def test_bad_and_hidden_files_are_skipped_without_changing_other_records(
    tmp_path,
) -> None:
    (tmp_path / "note.txt").write_text("valid", encoding="utf-8")
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    (tmp_path / ".hidden.txt").write_text("hidden", encoding="utf-8")

    first = ingest(tmp_path)
    second = ingest(tmp_path)

    assert [record.model_dump_json() for record in first.records] == [
        record.model_dump_json() for record in second.records
    ]
    assert first.skipped_files == ["bad.json"]
