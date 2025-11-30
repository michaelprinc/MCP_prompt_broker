import pytest

from metadata.parser import analyze_prompt


def test_brainstorm_prompt_classification():
    prompt = "Brainstorm creative product launch ideas for the marketing team"

    parsed = analyze_prompt(prompt)

    assert parsed.intent == "brainstorm"
    assert parsed.domain == "marketing"
    assert "storytelling" in parsed.topics
    assert parsed.safety_score == 0
    assert parsed.sensitivity == "low"
    assert parsed.complexity == "low"


def test_sensitive_healthcare_prompt_flags_safety():
    prompt = (
        "Patient SSN and medical history need to be scrubbed before sharing with "
        "hospital auditors."
    )

    parsed = analyze_prompt(prompt)

    assert parsed.domain == "healthcare"
    assert parsed.intent in {"diagnosis", "question", "statement", "review"}
    assert "pii" in parsed.topics
    assert parsed.safety_score >= 8
    assert parsed.sensitivity == "critical"
    assert parsed.tone == "neutral"


def test_bug_report_prompt_assigns_engineering_context():
    prompt = (
        "Seeing repeated stack trace errors during upload flows; please investigate "
        "the crash and provide guidance."
    )

    parsed = analyze_prompt(prompt)

    assert parsed.intent == "bug_report"
    assert parsed.domain == "engineering"
    assert "incident" in parsed.topics
    assert parsed.complexity in {"low", "low-medium"}


def test_security_incident_escalates_risk():
    prompt = "Urgent: investigate exploit payload in server logs and assess breach impact!"

    parsed = analyze_prompt(prompt)

    assert parsed.domain == "security"
    assert parsed.intent in {"diagnosis", "review", "question"}
    assert parsed.sensitivity == "critical"
    assert parsed.safety_score >= 9
    assert parsed.tone == "urgent"
    assert "security" in parsed.topics
    assert "incident" in parsed.topics
