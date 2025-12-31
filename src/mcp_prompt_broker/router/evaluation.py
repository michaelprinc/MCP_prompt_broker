"""Routing evaluation framework for measuring accuracy and performance.

This module provides tools for evaluating the routing accuracy of the
MCP Prompt Broker, including benchmark suite support, confusion matrices,
and per-profile metrics.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from .profile_router import EnhancedMetadata, ProfileRouter
from ..config.profiles import InstructionProfile
from ..metadata.parser import analyze_prompt


logger = logging.getLogger(__name__)


@dataclass
class TestCase:
    """A single benchmark test case."""
    
    id: str
    prompt: str
    expected_profile: str
    min_score: int = 0
    tags: tuple[str, ...] = field(default_factory=tuple)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create TestCase from dictionary."""
        return cls(
            id=str(data.get("id", "")),
            prompt=str(data.get("prompt", "")),
            expected_profile=str(data.get("expected_profile", "")),
            min_score=int(data.get("min_score", 0)),
            tags=tuple(data.get("tags", [])),
        )


@dataclass
class TestResult:
    """Result of a single test case evaluation."""
    
    test_case: TestCase
    actual_profile: str
    score: int
    passed: bool
    latency_ms: float
    error: Optional[str] = None
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.test_case.id,
            "prompt": self.test_case.prompt[:100] + "..." if len(self.test_case.prompt) > 100 else self.test_case.prompt,
            "expected": self.test_case.expected_profile,
            "actual": self.actual_profile,
            "score": self.score,
            "passed": self.passed,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


@dataclass
class RoutingEvaluationResult:
    """Aggregated evaluation results."""
    
    total_cases: int
    passed_cases: int
    failed_cases: int
    accuracy: float
    fallback_count: int
    fallback_rate: float
    avg_latency_ms: float
    per_profile_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: Dict[str, Dict[str, int]]
    results: List[TestResult]
    critical_recall: Optional[Dict[str, float]] = None
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": {
                "total_cases": self.total_cases,
                "passed_cases": self.passed_cases,
                "failed_cases": self.failed_cases,
                "accuracy": round(self.accuracy, 4),
                "fallback_count": self.fallback_count,
                "fallback_rate": round(self.fallback_rate, 4),
                "avg_latency_ms": round(self.avg_latency_ms, 2),
            },
            "per_profile_metrics": self.per_profile_metrics,
            "critical_recall": self.critical_recall,
            "confusion_matrix": self.confusion_matrix,
            "results": [r.as_dict() for r in self.results],
        }
    
    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# Routing Evaluation Report",
            "",
            "## Summary",
            "",
            f"- **Total Cases**: {self.total_cases}",
            f"- **Passed**: {self.passed_cases}",
            f"- **Failed**: {self.failed_cases}",
            f"- **Accuracy**: {self.accuracy:.1%}",
            f"- **Fallback Rate**: {self.fallback_rate:.1%}",
            f"- **Avg Latency**: {self.avg_latency_ms:.2f}ms",
            "",
            "## Per-Profile Metrics",
            "",
            "| Profile | Precision | Recall | F1 | Support |",
            "|---------|-----------|--------|----|---------",
        ]
        
        for profile, metrics in sorted(self.per_profile_metrics.items()):
            lines.append(
                f"| {profile} | {metrics.get('precision', 0):.2f} | "
                f"{metrics.get('recall', 0):.2f} | {metrics.get('f1', 0):.2f} | "
                f"{int(metrics.get('support', 0))} |"
            )
        
        if self.critical_recall:
            lines.extend([
                "",
                "## Critical Profile Recall",
                "",
            ])
            for profile, recall in sorted(self.critical_recall.items()):
                status = "✅" if recall >= 0.9 else "⚠️" if recall >= 0.75 else "❌"
                lines.append(f"- {status} **{profile}**: {recall:.1%}")
        
        lines.extend([
            "",
            "## Failed Cases",
            "",
        ])
        
        failed = [r for r in self.results if not r.passed]
        if failed:
            lines.append("| ID | Expected | Actual | Score |")
            lines.append("|----|----------|--------|-------|")
            for r in failed[:20]:  # Limit to 20
                lines.append(
                    f"| {r.test_case.id} | {r.test_case.expected_profile} | "
                    f"{r.actual_profile} | {r.score} |"
                )
        else:
            lines.append("No failed cases! 🎉")
        
        return "\n".join(lines)


def load_benchmark(path: Path) -> Tuple[List[TestCase], Dict[str, Any]]:
    """Load benchmark test cases from YAML file.
    
    Args:
        path: Path to the benchmark YAML file.
        
    Returns:
        Tuple of (test_cases, metadata).
    """
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    test_cases = [
        TestCase.from_dict(tc) for tc in data.get("test_cases", [])
    ]
    
    metadata = {
        "version": data.get("metadata", {}).get("version", "unknown"),
        "critical_profiles": data.get("critical_profiles", []),
        "thresholds": data.get("thresholds", {}),
    }
    
    return test_cases, metadata


def evaluate_routing(
    router: ProfileRouter,
    test_cases: Sequence[TestCase],
    fallback_profile_name: str = "general_default",
) -> RoutingEvaluationResult:
    """Evaluate router accuracy on test cases.
    
    Args:
        router: Router instance to evaluate.
        test_cases: List of test cases.
        fallback_profile_name: Name of the fallback profile.
        
    Returns:
        RoutingEvaluationResult with all metrics.
    """
    results: List[TestResult] = []
    confusion: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    # Track per-profile true/false positives/negatives
    tp: Dict[str, int] = defaultdict(int)  # True positives
    fp: Dict[str, int] = defaultdict(int)  # False positives
    fn: Dict[str, int] = defaultdict(int)  # False negatives
    support: Dict[str, int] = defaultdict(int)  # Total expected
    
    fallback_count = 0
    total_latency = 0.0
    
    for tc in test_cases:
        support[tc.expected_profile] += 1
        
        try:
            # Analyze and route
            start = time.perf_counter()
            parsed = analyze_prompt(tc.prompt)
            enhanced = parsed.to_enhanced_metadata()
            routing = router.route(enhanced)
            latency = (time.perf_counter() - start) * 1000
            
            actual = routing.profile.name
            score = routing.score
            passed = actual == tc.expected_profile
            
            # Track confusion matrix
            confusion[tc.expected_profile][actual] += 1
            
            # Track fallback
            if actual == fallback_profile_name:
                fallback_count += 1
            
            # Track TP/FP/FN
            if passed:
                tp[tc.expected_profile] += 1
            else:
                fn[tc.expected_profile] += 1
                fp[actual] += 1
            
            results.append(TestResult(
                test_case=tc,
                actual_profile=actual,
                score=score,
                passed=passed,
                latency_ms=latency,
            ))
            total_latency += latency
            
        except Exception as e:
            logger.error(f"Error evaluating {tc.id}: {e}")
            results.append(TestResult(
                test_case=tc,
                actual_profile="ERROR",
                score=0,
                passed=False,
                latency_ms=0,
                error=str(e),
            ))
            fn[tc.expected_profile] += 1
    
    # Calculate metrics
    passed_count = sum(1 for r in results if r.passed)
    failed_count = len(results) - passed_count
    accuracy = passed_count / len(results) if results else 0.0
    fallback_rate = fallback_count / len(results) if results else 0.0
    avg_latency = total_latency / len(results) if results else 0.0
    
    # Per-profile metrics
    per_profile: Dict[str, Dict[str, float]] = {}
    all_profiles = set(support.keys()) | set(tp.keys()) | set(fp.keys())
    
    for profile in all_profiles:
        precision = tp[profile] / (tp[profile] + fp[profile]) if (tp[profile] + fp[profile]) > 0 else 0.0
        recall = tp[profile] / support[profile] if support[profile] > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        per_profile[profile] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support[profile],
            "true_positives": tp[profile],
            "false_positives": fp[profile],
            "false_negatives": fn[profile],
        }
    
    return RoutingEvaluationResult(
        total_cases=len(results),
        passed_cases=passed_count,
        failed_cases=failed_count,
        accuracy=accuracy,
        fallback_count=fallback_count,
        fallback_rate=fallback_rate,
        avg_latency_ms=avg_latency,
        per_profile_metrics=per_profile,
        confusion_matrix=dict(confusion),
        results=results,
    )


def evaluate_critical_profiles(
    evaluation: RoutingEvaluationResult,
    critical_profiles: Sequence[str],
    target_recall: float = 0.9,
) -> Dict[str, float]:
    """Calculate recall for critical profiles.
    
    Args:
        evaluation: Evaluation result.
        critical_profiles: List of critical profile names.
        target_recall: Target recall threshold.
        
    Returns:
        Dictionary mapping profile name to recall.
    """
    critical_recall = {}
    
    for profile in critical_profiles:
        metrics = evaluation.per_profile_metrics.get(profile, {})
        recall = metrics.get("recall", 0.0)
        critical_recall[profile] = recall
    
    return critical_recall


def run_benchmark(
    router: ProfileRouter,
    benchmark_path: Optional[Path] = None,
) -> RoutingEvaluationResult:
    """Run the full benchmark suite.
    
    Args:
        router: Router to evaluate.
        benchmark_path: Path to benchmark YAML. Defaults to fixtures/routing_benchmark.yaml.
        
    Returns:
        Complete evaluation result.
    """
    if benchmark_path is None:
        benchmark_path = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures" / "routing_benchmark.yaml"
    
    test_cases, metadata = load_benchmark(benchmark_path)
    
    logger.info(f"Running benchmark with {len(test_cases)} test cases")
    
    evaluation = evaluate_routing(router, test_cases)
    
    # Add critical profile recall
    critical_profiles = metadata.get("critical_profiles", [])
    if critical_profiles:
        evaluation.critical_recall = evaluate_critical_profiles(
            evaluation, critical_profiles
        )
    
    return evaluation
