"""Offline evaluation — runs the pipeline against labeled examples in data/eval_set.jsonl.

Usage:
    python eval.py
    python eval.py --path data/eval_set.jsonl

Each line must be a JSON object:
    {"metin": "...", "expected": "dusuk" | "orta" | "yuksek"}
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

from app.pipeline.classify import classify
from app.pipeline.deterministic import run_deterministic
from app.pipeline.extract import extract
from app.pipeline.fusion import fuse
from app.pipeline.verify import verify

LEVELS = ["dusuk", "orta", "yuksek"]


async def _run_pipeline(text: str) -> str:
    """Run a single example through the pipeline and return the predicted risk level."""
    try:
        extracted = await extract(text=text, image=None)
        det_flags, link_analysis = run_deterministic(extracted)
        classify_output = await classify(extracted)
        verified = verify(classify_output, extracted)
        det_ids = {f.id for f in det_flags}
        merged = det_flags + [f for f in verified.flags if f.id not in det_ids]
        result = fuse(
            flags=merged,
            link_analysis=link_analysis,
            verdict=verified.verdict,
            recommended_actions=verified.recommended_actions,
        )
        return result.risk_level
    except Exception as exc:
        print(f"  [ERROR] Pipeline failed: {exc}", file=sys.stderr)
        return "orta"


def _precision_recall_f1(y_true: list[str], y_pred: list[str], label: str) -> tuple[float, float, float]:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def _print_confusion_matrix(y_true: list[str], y_pred: list[str]) -> None:
    matrix = {s: {s2: 0 for s2 in LEVELS} for s in LEVELS}
    for t, p in zip(y_true, y_pred):
        if t in matrix and p in LEVELS:
            matrix[t][p] += 1
    header = f"{'':>8} | " + " | ".join(f"{'PRED:'+s:>12}" for s in LEVELS)
    print(header)
    print("-" * len(header))
    for true_label in LEVELS:
        row = f"{'TRUE:'+true_label:>8} | " + " | ".join(
            f"{matrix[true_label][pred]:>12}" for pred in LEVELS
        )
        print(row)


async def main(path: str) -> None:
    eval_path = pathlib.Path(path)
    if not eval_path.exists():
        print(f"Error: {path} not found.", file=sys.stderr)
        sys.exit(1)

    cases = []
    with eval_path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"Line {lineno}: JSON error — {exc}", file=sys.stderr)

    if not cases:
        print("No test cases found.", file=sys.stderr)
        sys.exit(1)

    print(f"Running {len(cases)} test cases...")

    y_true: list[str] = []
    y_pred: list[str] = []

    for i, case in enumerate(cases, 1):
        text = case.get("metin", "")
        expected = case.get("expected", case.get("beklenen", ""))
        if expected not in LEVELS:
            print(f"  [{i}] invalid 'expected' value: {expected!r} — skipping")
            continue

        print(f"  [{i}/{len(cases)}] analyzing...", end=" ", flush=True)
        predicted = await _run_pipeline(text)
        marker = "✓" if predicted == expected else "✗"
        print(f"{marker}  expected={expected}, predicted={predicted}")

        y_true.append(expected)
        y_pred.append(predicted)

    if not y_true:
        print("No evaluable examples.")
        return

    print("\n" + "=" * 52)
    print("PER-CLASS METRICS")
    print("=" * 52)
    print(f"{'Class':>8} | {'Precision':>9} | {'Recall':>9} | {'F1':>9}")
    print("-" * 52)

    f1_scores = []
    for label in LEVELS:
        p, r, f1 = _precision_recall_f1(y_true, y_pred, label)
        f1_scores.append(f1)
        print(f"{label:>8} | {p:>9.3f} | {r:>9.3f} | {f1:>9.3f}")

    macro_f1 = sum(f1_scores) / len(f1_scores)
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true)
    print("-" * 52)
    print(f"{'MacroF1':>8}                            {macro_f1:>9.3f}")
    print(f"{'Accuracy':>8}: {accuracy:.3f}  ({sum(1 for t,p in zip(y_true,y_pred) if t==p)}/{len(y_true)})")

    print("\n" + "=" * 52)
    print("CONFUSION MATRIX (rows=true, cols=predicted)")
    print("=" * 52)
    _print_confusion_matrix(y_true, y_pred)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kalkan pipeline evaluation")
    parser.add_argument("--path", default="data/eval_set.jsonl")
    args = parser.parse_args()
    asyncio.run(main(args.path))
