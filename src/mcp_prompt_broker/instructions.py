"""Instruction definitions and selection utilities for the MCP prompt broker."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence
import re


@dataclass(frozen=True)
class Instruction:
    """A reusable instruction that can be selected for a user prompt."""

    name: str
    description: str
    guidance: str
    keywords: Sequence[str]

    def match_score(self, prompt: str) -> int:
        """Return a score representing how well the prompt matches this instruction.

        The score is based on normalized keyword matches and their frequency. Higher
        scores indicate a stronger relationship between the prompt and the
        instruction's intended use.
        """

        normalized_prompt = _normalize(prompt)
        score = 0
        for keyword in self.keywords:
            # reward both presence and repeated signals of intent
            occurrences = len(re.findall(rf"\b{re.escape(keyword)}\b", normalized_prompt))
            score += occurrences * 3 if occurrences else 0
        # reward direct name references lightly
        score += len(re.findall(rf"\b{re.escape(self.name)}\b", normalized_prompt))
        return score


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for easier matching."""

    return re.sub(r"\s+", " ", text.strip().lower())


class InstructionCatalog:
    """Maintains a collection of instructions and selects the best fit."""

    def __init__(self, instructions: Iterable[Instruction]):
        self._instructions: List[Instruction] = list(instructions)

    def list(self) -> List[Instruction]:
        """Return all instructions in insertion order."""

        return list(self._instructions)

    def select(self, prompt: str) -> Instruction:
        """Select the best instruction for a prompt.

        If multiple instructions tie for the top score, the earliest instruction in
        the catalog is chosen to keep the selection stable.
        """

        prompt = prompt.strip()
        if not prompt:
            raise ValueError("Prompt must not be empty")

        best = None
        best_score = -1
        for instruction in self._instructions:
            score = instruction.match_score(prompt)
            if score > best_score:
                best = instruction
                best_score = score

        if best is None or best_score <= 0:
            raise LookupError("No suitable instruction found for the prompt")

        return best


DEFAULT_INSTRUCTIONS: List[Instruction] = [
    Instruction(
        name="code-review",
        description="Review code for correctness, clarity, and security concerns.",
        guidance=(
            "Perform a focused code review. Summarize intent, highlight risks, and "
            "offer actionable improvements without changing the author's voice."
        ),
        keywords=("review", "bug", "security", "refactor", "lint"),
    ),
    Instruction(
        name="architecture-advice",
        description="Suggest system design or architectural approaches to a problem.",
        guidance=(
            "Explain trade-offs between options, call out dependencies, and keep the "
            "solution aligned with the user's constraints."
        ),
        keywords=("architecture", "design", "pattern", "scaling", "roadmap"),
    ),
    Instruction(
        name="coding-help",
        description="Assist with writing or explaining code snippets.",
        guidance=(
            "Provide concise examples that are ready to paste. Note assumptions about "
            "inputs and environment."
        ),
        keywords=("write", "implement", "example", "snippet", "explain"),
    ),
]
