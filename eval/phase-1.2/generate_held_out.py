"""Generate the checked-in Phase 1.2 suite; never called by evaluation."""

from __future__ import annotations

import json
from pathlib import Path

DOMAINS = [
    ("acoustic-archaeology", "Aster", "buried chamber mapping"),
    ("alpine-mycology", "Boreal", "high-altitude fungal cultivation"),
    ("orbital-agriculture", "Canopy", "orbital crop production"),
    ("cryogenic-logistics", "Drift", "cryogenic sample transport"),
    ("desert-hydrology", "Estuary", "desert aquifer monitoring"),
    ("forensic-botany", "Flora", "forensic pollen analysis"),
    ("geothermal-ceramics", "Garnet", "geothermal ceramic processing"),
    ("historical-linguistics", "Helix", "historical language restoration"),
    ("ice-sheet-radar", "Isobar", "ice-sheet radar surveying"),
    ("jungle-epidemiology", "Jade", "jungle disease surveillance"),
    ("kinetic-architecture", "Keystone", "adaptive building control"),
    ("lunar-geodesy", "Lagrange", "lunar surface measurement"),
    ("microfluidic-ecology", "Marsh", "microfluidic ecosystem sampling"),
    ("neutrino-instrumentation", "Nadir", "neutrino detector operation"),
    ("ocean-acoustics", "Osprey", "deep-ocean acoustic sensing"),
    ("paleomagnetism", "Polaris", "ancient magnetic-field reconstruction"),
    ("quantum-metrology", "Quill", "quantum reference measurement"),
    ("river-restoration", "Rill", "river habitat restoration"),
    ("soil-robotics", "Silt", "autonomous soil assessment"),
    ("tactile-prosthetics", "Talon", "tactile prosthetic feedback"),
    ("urban-aerobiology", "Updraft", "urban airborne-spore monitoring"),
    ("volcanic-seismology", "Vesta", "volcanic tremor analysis"),
    ("wetland-photonics", "Warden", "wetland optical sensing"),
    ("xenobiotic-remediation", "Xylem", "industrial contaminant cleanup"),
]

SETTINGS = [
    (
        "balanced_consensus",
        "What combined operating policy best supports {work} in {project}?",
        [
            "{project} field records require calibrated sensors before each run.",
            "Independent review shows repeated measurements reduce local noise.",
            "Operators retain raw observations so later audits can reproduce results.",
        ],
        [6.0, 6.0, 3.0],
        [],
    ),
    (
        "unequal_authority",
        "Which evidence should guide the disputed material choice for {project}?",
        [
            "The certified {project} safety study approves ceramic housings "
            "for the site.",
            "A controlled durability trial found ceramic housings stable "
            "during operation.",
            "An early informal memo preferred polymer housings before "
            "durability tests existed.",
        ],
        [12.0, 8.0, 1.0],
        [],
    ),
    (
        "contradictory_evidence",
        "How should {project} report the unresolved calibration disagreement?",
        [
            "The primary {project} calibration team reports a positive "
            "two-percent offset.",
            "An independent accredited laboratory reports a negative "
            "two-percent offset.",
            "A preliminary notebook reports no offset but has low "
            "measurement confidence.",
        ],
        [10.0, 10.0, 1.0],
        [0, 1],
    ),
    (
        "irrelevant_density",
        "What reliable evidence determines the sampling interval for {project}?",
        [
            "The validated {project} protocol samples once every fifteen minutes.",
            "A year-long field trial found fifteen-minute sampling preserved "
            "transient events.",
            "A pilot note suggested hourly sampling but covered only one quiet day.",
        ],
        [12.0, 8.0, 1.0],
        [],
    ),
    (
        "multi_evidence_bridge",
        "Why does the {project} workflow improve decisions in {work}?",
        [
            "{project} converts raw readings into uncertainty-calibrated observations.",
            "Uncertainty calibration lets the pipeline weight observations "
            "by reliability.",
            "Reliability weighting prevents weak readings from dominating "
            "the final decision.",
        ],
        [8.0, 8.0, 4.0],
        [],
    ),
]


def generate() -> dict:
    domains = []
    for domain_id, project, work in DOMAINS:
        documents = {}
        cases = []
        for category_index, (
            category,
            query,
            facts,
            priorities,
            conflict_offsets,
        ) in enumerate(SETTINGS):
            ids = []
            for fact_index, (fact, priority) in enumerate(
                zip(facts, priorities), start=1
            ):
                chunk_id = f"{domain_id}-{category_index + 1}-{fact_index}"
                ids.append(chunk_id)
                documents[chunk_id] = {
                    "text": fact.format(project=project, work=work),
                    "metadata": {
                        "priority": priority,
                        "confidence": 1.0 if priority > 1 else 0.55,
                        "authority": 1.0 if priority > 1 else 0.5,
                        "recency": 1.0 if priority > 1 else 0.6,
                    },
                }
            cases.append(
                {
                    "id": f"{domain_id}-{category}",
                    "category": category,
                    "query": query.format(project=project, work=work),
                    "high": ids[:2],
                    "low": ids[2:],
                    "conflicts": [ids[offset] for offset in conflict_offsets],
                }
            )
        for index in range(8):
            chunk_id = f"{domain_id}-distractor-{index + 1}"
            documents[chunk_id] = {
                "text": (
                    f"A public exhibition repeats {project}, {work}, reliable "
                    f"evidence, sampling, calibration, material, and workflow "
                    f"in display {index + 1}, "
                    "but contains no operational finding."
                ),
                "metadata": {
                    "priority": 0.2,
                    "confidence": 0.2,
                    "authority": 0.2,
                    "recency": 0.5,
                },
            }
        domains.append(
            {
                "id": domain_id,
                "documents": documents,
                "cases": cases,
            }
        )
    return {
        "schema_version": "1",
        "locked": True,
        "description": (
            "Static Phase 1.2 held-out suite: 120 queries, 24 unseen domains, "
            "five balanced categories, explicit weights and conflicts."
        ),
        "domains": domains,
    }


if __name__ == "__main__":
    output = Path(__file__).with_name("held-out.json")
    output.write_text(json.dumps(generate(), indent=2) + "\n", encoding="utf-8")
