from topology_g23.compiler import SentenceTopologyCompiler
from topology_g23.dataset import generate_sentence_examples


def test_untrained_compiler_is_fail_closed_or_g1_valid():
    example = generate_sentence_examples("development")[0]
    compiler = SentenceTopologyCompiler(recurrent=True)
    result = compiler.compile(example.source, confidence=0.0, margin=0.0)
    assert result.disposition in {"accept", "clarification_required", "quarantine"}
    if result.accepted_ir is not None:
        assert result.accepted_ir.operations
