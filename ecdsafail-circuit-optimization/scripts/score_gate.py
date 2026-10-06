#!/usr/bin/env python3
"""Strict product-score gate for an official rounded-Toffoli benchmark."""
import argparse
import json


def max_rounded_t(best_score: int, qubits: int) -> int:
    if best_score <= 0 or qubits <= 0:
        raise ValueError("score and qubits must be positive integers")
    return (best_score - 1) // qubits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best-score", type=int, required=True)
    parser.add_argument("--qubits", type=int, required=True)
    parser.add_argument("--rounded-toffoli", type=int)
    args = parser.parse_args()
    limit = max_rounded_t(args.best_score, args.qubits)
    result = {"best_score": args.best_score, "qubits": args.qubits,
              "max_rounded_t_for_strict_beat": limit}
    if args.rounded_toffoli is not None:
        if args.rounded_toffoli <= 0:
            parser.error("rounded Toffoli must be positive")
        score = args.qubits * args.rounded_toffoli
        result.update(candidate_score=score, strict_beat=score < args.best_score,
                      score_margin=args.best_score - score)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
