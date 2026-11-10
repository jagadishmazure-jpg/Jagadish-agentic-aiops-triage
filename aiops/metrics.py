"""Small, explicit metrics so every README number can be traced to code."""

from __future__ import annotations

import math

import numpy as np


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0 <= k <= n:
        raise ValueError("k must be between 0 and n")
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def rate(k: int, n: int) -> dict:
    k, n = int(k), int(n)
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4), "ci95": [round(lo, 4), round(hi, 4)]}


def percentile(xs: list[float], q: float) -> float:
    if not xs:
        raise ValueError("empty")
    return float(np.percentile(np.array(xs), q, method="linear"))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pair counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * p)


def cohen_kappa(a: list, b: list) -> float:
    """Agreement between two raters beyond chance (labels of any hashable type)."""
    if len(a) != len(b) or not a:
        raise ValueError("need two equal, non-empty label lists")
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    pe = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)
