#!/usr/bin/env python3
"""
Island-hunt runtime model (two-stage: cheap GPU classical screen -> expensive full eval).

A nonce becomes a SUBMITTABLE island only if it is clean in ALL three channels
(cls=pha=anc=0) under the trusted 9024-shot evaluator. The hunt is two stages:

  Stage 1  (cheap, GPU classical GCD pre-filter):
       screens nonces at aggregate rate R (nonce/s); a nonce passes
       ("GCD-clean" / classical-clean) with probability  d = e^(-lambda_cls).
       d is the GCD-CLEAN CANDIDATE DENSITY  (input #1).

  Stage 2  (expensive, full 9024-shot evaluator, cost T_eval s/candidate):
       each Stage-1 pass is fully evaluated for cls(confirm)/pha/anc; it is a
       real island with conditional probability
            q = P(pha=0 AND anc=0 | cls-clean)
       q is derived from the CLS/PHA/ANC DISTRIBUTION of GCD-clean
       candidates (input #2). This is the term density-only estimates ignore.

  Aggregate throughput R (nonce/s) is input #3.

Per-nonce success probability:        p = d * q
Expected nonces to first island:      N = 1 / p
Stage-1 passes that must be evaled:   N * d = 1 / q
Amortized cost per screened nonce:    (1/R) + d * T_eval      [sequential resources]
Expected total time (sequential):     (1/p) * (1/R + d*T_eval)
                                     = screen_time + eval_time
   screen_time = 1/(d*q*R)         (Stage-1 dominated by rare density)
   eval_time   = T_eval / q        (Stage-2 dominated by independent pha/anc thinning)
If screen and eval run on SEPARATE hardware (concurrent): total = max(screen, eval).

Number of trials to first success ~ Geometric(p); time is ~exponential, heavy tail:
   percentile P  ->  k_nonces = ln(1/(1-P)) / p   (median ~0.69/p, p99 ~4.6/p).
"""
import argparse, math, sys


def load_panel(path):
    """Panel of GCD-clean candidates, full-evaluated. Lines: 'cls pha anc' (ints).
    Returns (q, stats) where q = fraction with cls==pha==anc==0."""
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").split()
            cls, pha, anc = int(parts[0]), int(parts[1]), int(parts[2])
            rows.append((cls, pha, anc))
    n = len(rows)
    if n == 0:
        raise SystemExit("panel is empty")
    clean = sum(1 for c, p, a in rows if c == 0 and p == 0 and a == 0)
    cls_fail = sum(1 for c, p, a in rows if c > 0)
    pha_fail = sum(1 for c, p, a in rows if p > 0)
    anc_fail = sum(1 for c, p, a in rows if a > 0)
    # how independent is pha from cls? (pha-fails that are NOT cls-fails = leak past the screen)
    pha_only = sum(1 for c, p, a in rows if p > 0 and c == 0)
    anc_only = sum(1 for c, p, a in rows if a > 0 and c == 0)
    q = clean / n
    return q, dict(n=n, clean=clean, cls_fail=cls_fail, pha_fail=pha_fail,
                   anc_fail=anc_fail, pha_only=pha_only, anc_only=anc_only)


def fmt_time(s):
    if s < 1:      return f"{s*1e3:.0f} ms"
    if s < 90:     return f"{s:.1f} s"
    if s < 5400:   return f"{s/60:.1f} min"
    if s < 1.5*86400: return f"{s/3600:.2f} h"
    return f"{s/86400:.2f} days"


def main():
    ap = argparse.ArgumentParser(description="Island-hunt runtime model")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--density", type=float, help="GCD-clean density d (Stage-1 pass rate)")
    g.add_argument("--lambda-cls", type=float, help="classical displacement lambda_cls (d=e^-lambda)")
    gq = ap.add_mutually_exclusive_group(required=True)
    gq.add_argument("--q", type=float, help="P(pha=0 & anc=0 | cls-clean), the Stage-2 survival rate")
    gq.add_argument("--qpanel", type=str, help="panel file 'cls pha anc' of GCD-clean candidates -> q")
    ap.add_argument("--rate", type=float, required=True, help="aggregate Stage-1 screen throughput, nonce/s")
    ap.add_argument("--t-eval", type=float, default=15.0, help="seconds per full 9024-shot eval (default 15)")
    ap.add_argument("--concurrent", action="store_true",
                    help="screen and eval on separate hardware (total=max instead of sum)")
    args = ap.parse_args()

    d = args.density if args.density is not None else math.exp(-args.lambda_cls)
    lam = -math.log(d)
    panel_stats = None
    if args.qpanel:
        q, panel_stats = load_panel(args.qpanel)
    else:
        q = args.q
    R, Te = args.rate, args.t_eval

    if d <= 0 or d > 1 or q <= 0 or q > 1:
        raise SystemExit("d and q must be in (0,1]")

    p = d * q
    N = 1.0 / p
    screen_time = N / R                 # = 1/(d q R)
    eval_time = (N * d) * Te            # = Te / q
    total = max(screen_time, eval_time) if args.concurrent else screen_time + eval_time

    print("=" * 64)
    print("ISLAND-HUNT RUNTIME MODEL")
    print("=" * 64)
    print(f"  [1] GCD-clean density   d        = {d:.3e}   (lambda_cls = {lam:.2f})")
    if panel_stats:
        s = panel_stats
        print(f"  [2] cls/pha/anc panel: n={s['n']}  fully-clean={s['clean']}")
        print(f"        cls_fail={s['cls_fail']}  pha_fail={s['pha_fail']}  anc_fail={s['anc_fail']}")
        print(f"        pha-fail-with-cls-clean (LEAK past screen) = {s['pha_only']}")
        print(f"        anc-fail-with-cls-clean (LEAK past screen) = {s['anc_only']}")
        if s['pha_only'] == 0 and s['anc_only'] == 0:
            print(f"        -> pha/anc subset of cls: density IS a good predictor (q~1 path)")
        else:
            print(f"        -> INDEPENDENT pha/anc mode present: density alone is OPTIMISTIC")
    print(f"  [2] Stage-2 survival    q        = {q:.3e}   (P(pha=0,anc=0|cls-clean))")
    print(f"  [3] screen throughput   R        = {R:.3e} nonce/s")
    print(f"      full-eval cost      T_eval   = {Te:.1f} s/candidate")
    print("-" * 64)
    print(f"  per-nonce success       p = d*q  = {p:.3e}")
    print(f"  expected nonces         N = 1/p  = {N:.3e}")
    print(f"  Stage-1 passes to eval  1/q      = {1.0/q:.3e}")
    print("-" * 64)
    print(f"  Stage-1 screen time  1/(d q R)   = {fmt_time(screen_time)}")
    print(f"  Stage-2 eval time    T_eval/q    = {fmt_time(eval_time)}")
    dom = "SCREEN (density-bound)" if screen_time >= eval_time else "EVAL (pha/anc-bound)"
    print(f"  bottleneck                        = {dom}")
    mode = "max (concurrent HW)" if args.concurrent else "sum (shared HW)"
    print(f"  EXPECTED total time [{mode}]      = {fmt_time(total)}")
    print("-" * 64)
    print("  time distribution (geometric -> exponential tail):")
    for P in (0.50, 0.90, 0.95, 0.99):
        k = math.log(1.0 / (1.0 - P)) / p             # nonces to reach percentile P
        t = k * (1.0 / R + d * Te)
        if args.concurrent:
            t = max(k / R, k * d * Te)
        print(f"     p{int(P*100):<2d}: {fmt_time(t)}")
    print("=" * 64)


if __name__ == "__main__":
    main()
