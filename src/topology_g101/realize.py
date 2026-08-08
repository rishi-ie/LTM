from __future__ import annotations

import json

from topology_g10.validator import validate

from .grammar import candidates
from .model import FlanCandidateScorer
from .schemas import AnswerMR, DecoderBundle, RankedRealization, answer_mr


def mr_text(mr: AnswerMR) -> str:
    return json.dumps({"disposition": mr.disposition, "status": mr.status, "claim_ids": mr.claim_ids, "mandatory_disclosures": mr.mandatory_disclosures, "style": mr.style}, sort_keys=True)


def realize(bundle: DecoderBundle, scorer: FlanCandidateScorer) -> RankedRealization:
    mr = answer_mr(bundle)
    options = candidates(bundle, mr)
    scored = [(scorer.score(mr_text(mr), option.text)[0], option) for option in options]
    score, selected = max(scored, key=lambda item: (item[0], item[1].template_id))
    accepted = validate(selected.text, bundle).accepted
    if not accepted:
        raise RuntimeError("GRAMMAR_CANDIDATE_VALIDATION_FAILURE")
    return RankedRealization(bundle.bundle_id, mr, selected, options, score, accepted)
