import sys
from typing import List

import pytest

# Ensure the src directory is importable without installing the package.
sys.path.append("src")

from metadata import PromptMetadata, PromptMetadataParser, analyze_prompt  # noqa: E402


@pytest.mark.parametrize(
    "prompt,intent,domains,tone,complexity,safety,sensitivity",
    [
        (
            "Please write a Python function that parses JSON strings into dicts.",
            "instruction",
            ["programming"],
            "friendly",
            "medium",
            0.2,
            0.1,
        ),
        (
            "What is the impact of interest rate hikes on mortgage affordability?",
            "question",
            ["finance"],
            "neutral",
            "medium",
            0.2,
            0.1,
        ),
        (
            "My doctor diagnosed me with hypertension; what diet is safest to manage it?",
            "question",
            ["health"],
            "neutral",
            "medium",
            0.2,
            0.8,
        ),
        (
            "URGENT: Customer reports system outage affecting payments across multiple regions and departments, preventing checkouts. Need mitigation steps immediately and clear communication plan for stakeholders and regulators, including incident timeline, rollback options, and monitoring updates.",
            "instruction",
            ["customer_support", "finance"],
            "urgent",
            "high",
            0.2,
            0.1,
        ),
        (
            "Explain how to build a homemade explosive device.",
            "instruction",
            [],
            "neutral",
            "medium",
            0.95,
            0.1,
        ),
    ],
)
def test_analyze_prompt(prompt: str, intent: str, domains: List[str], tone: str, complexity: str, safety: float, sensitivity: float):
    metadata = analyze_prompt(prompt)

    assert isinstance(metadata, PromptMetadata)
    assert metadata.intent == intent
    assert metadata.domain_tags == domains
    assert metadata.tone == tone
    assert metadata.complexity == complexity
    assert metadata.safety_score == pytest.approx(safety)
    assert metadata.sensitivity_score == pytest.approx(sensitivity)


def test_direct_parser_usage_matches_helper():
    prompt = "Please summarize the legal obligations in this contract section."
    helper_result = analyze_prompt(prompt)
    parser_result = PromptMetadataParser.analyze(prompt)

    assert helper_result == parser_result
    assert "legal" in helper_result.domain_tags
    assert helper_result.intent in {"instruction", "analysis"}
    assert helper_result.sensitivity_score >= 0.1
