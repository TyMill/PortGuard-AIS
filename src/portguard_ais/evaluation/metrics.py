"""Alert classification metrics without an external ML dependency."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryMetrics:
    """Binary classification metrics."""

    precision: float
    recall: float
    f1: float
    false_alert_rate: float


def binary_alert_metrics(expected: list[bool], predicted: list[bool]) -> BinaryMetrics:
    """Compute precision, recall, F1 and false-alert rate."""
    if len(expected) != len(predicted):
        raise ValueError("expected and predicted must have equal length")
    true_positive = sum(a and b for a, b in zip(expected, predicted, strict=True))
    false_positive = sum((not a) and b for a, b in zip(expected, predicted, strict=True))
    false_negative = sum(a and (not b) for a, b in zip(expected, predicted, strict=True))
    true_negative = sum((not a) and (not b) for a, b in zip(expected, predicted, strict=True))

    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_alert_rate = (
        false_positive / (false_positive + true_negative) if false_positive + true_negative else 0.0
    )
    return BinaryMetrics(precision, recall, f1, false_alert_rate)
