#!/usr/bin/env python3
"""
reproduce_paper.py — regenerate every figure in the preprint from raw data.

Reads the four CSVs in ../data/ and prints each table and test statistic that
appears in the paper, in paper order. Nothing is hard-coded: if the data
changes, the output changes, so any discrepancy between this output and the
manuscript is a real discrepancy.

  pip install scipy
  python3 analysis/reproduce_paper.py
  python3 analysis/reproduce_paper.py --data-dir path/to/data

CSV schemas (as written by the harnesses):
  exp1  variant,run,prompt_idx,prompt,status,tools_called,decoy_called
  exp2  variant,kind,idx,condition,run,prompt,status,tools_called,decoy_called,error
  exp3  model,variant,set,idx,condition,run,prompt,status,tools_called,decoy_called,error
  xvend  (same as exp3)
"""

import argparse, csv, math, os, sys
from collections import Counter, defaultdict

try:
    from scipy.stats import fisher_exact, norm
except ImportError:
    sys.exit("pip install scipy")

SCORES = {"low": 0, "medium": 1, "high": 2}
VARIANTS = ("low", "medium", "high")


# ---------------------------------------------------------------- statistics

def wilson(s, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = s / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    m = (z / d) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, c - m), min(1.0, c + m))


def cochran_armitage(counts):
    """counts: {level: (hits, n)} -> (z, two-sided p)"""
    xs = [SCORES[k] for k in counts]
    rs = [v[0] for v in counts.values()]
    ns = [v[1] for v in counts.values()]
    N, R = sum(ns), sum(rs)
    if N == 0 or R in (0, N):
        return float("nan"), float("nan")
    pbar = R / N
    xbar = sum(n * x for n, x in zip(ns, xs)) / N
    num = sum(r * (x - xbar) for r, x in zip(rs, xs))
    var = pbar * (1 - pbar) * sum(n * (x - xbar) ** 2 for n, x in zip(ns, xs))
    if var <= 0:
        return float("nan"), float("nan")
    z = num / math.sqrt(var)
    return z, 2 * (1 - norm.cdf(abs(z)))


def contrast(a, na, b, nb):
    odds, p = fisher_exact([[a, na - a], [b, nb - b]])
    return odds, p


def rate(h, n):
    return f"{h}/{n} = {100*h/n:.2f}%" if n else f"{h}/0 = n/a"


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ------------------------------------------------------------------- loading

def load(path, dedupe_key=None):
    """Read a results CSV, drop error rows, optionally keep one row per key."""
    if not os.path.exists(path):
        print(f"  [skipped — {os.path.basename(path)} not found]")
        return []
    rows = list(csv.DictReader(open(path, newline="", encoding="utf-8")))
    ok = [r for r in rows if r.get("status") == "OK"]
    dropped = len(rows) - len(ok)
    if dedupe_key:
        seen, out = set(), []
        for r in ok:
            k = tuple(r[f] for f in dedupe_key)
            if k in seen:
                continue
            seen.add(k)
            out.append(r)
        if len(out) != len(ok):
            print(f"  note: {len(ok)-len(out)} duplicate retried rows collapsed")
        ok = out
    if dropped:
        print(f"  note: {dropped} error rows excluded")
    return ok


def hits(rows):
    return sum(int(r["decoy_called"]) for r in rows)


# ------------------------------------------------------------------ analyses

def study1(rows):
    rule("STUDY 1 — baseline (paper §3.1)")
    if not rows:
        return
    prompts = {r["prompt_idx"] for r in rows}
    print(f"unique prompts: {len(prompts)}   total trials: {len(rows)}")
    counts = {}
    print(f"\n{'variant':<10}{'hits/trials':<20}{'rate':<10}{'95% CI'}")
    for v in VARIANTS:
        cell = [r for r in rows if r["variant"] == v]
        h, n = hits(cell), len(cell)
        counts[v] = (h, n)
        lo, hi = wilson(h, n)
        print(f"{v:<10}{f'{h}/{n}':<20}{100*h/n:<10.2f}{100*lo:.2f}% – {100*hi:.2f}%")

    z, p = cochran_armitage(counts)
    print(f"\nCochran-Armitage trend: z={z:.4f}  p={p:.4f}")
    lh, ln = counts["low"]; hh, hn = counts["high"]
    _, plh = contrast(lh, ln, hh, hn)
    print(f"low vs high (Fisher):   p={plh:.4f}")

    per = defaultdict(int)
    for r in rows:
        if int(r["decoy_called"]):
            per[r["prompt_idx"]] += 1
    total = sum(per.values())
    print(f"\nprompts producing any hit: {len(per)} of {len(prompts)}")
    for pid, c in sorted(per.items(), key=lambda x: -x[1]):
        txt = next(r["prompt"] for r in rows if r["prompt_idx"] == pid)
        print(f"  index {pid}: {c}/{total} of all hits — {txt}")
    clean = len(prompts) - len(per)
    ctrials = len([r for r in rows if r["prompt_idx"] not in per])
    print(f"the other {clean} prompts: 0 hits across {ctrials} trials")


def study2(rows):
    rule("STUDY 2 — matched pairs (paper §3.2)")
    if not rows:
        return
    print(f"total trials: {len(rows)}")
    pooled = {}
    for cond in ("unresolved", "resolved", "control"):
        cell = [r for r in rows if r["condition"] == cond]
        if not cell:
            continue
        pooled[cond] = (hits(cell), len(cell))
        print(f"  {cond:<14}{rate(*pooled[cond])}")
    if "unresolved" in pooled and "resolved" in pooled:
        _, p = contrast(*pooled["unresolved"], *pooled["resolved"])
        print(f"\nunresolved vs named vendor (Fisher): p={p:.4g}")

    print(f"\n{'variant':<10}{'unresolved'}")
    for v in VARIANTS:
        cell = [r for r in rows if r["variant"] == v and r["condition"] == "unresolved"]
        if cell:
            print(f"{v:<10}{rate(hits(cell), len(cell))}")

    print("\nper-pair breakdown:")
    npairs = ngen = 0
    for pid in sorted({int(r["idx"]) for r in rows if r["kind"] == "pair"}):
        u = [r for r in rows if r["kind"] == "pair" and int(r["idx"]) == pid
             and r["condition"] == "unresolved"]
        rr = [r for r in rows if r["kind"] == "pair" and int(r["idx"]) == pid
              and r["condition"] == "resolved"]
        npairs += 1
        hu = hits(u)
        if hu:
            ngen += 1
        txt = u[0]["prompt"][:52] if u else ""
        print(f"  [{pid:>2}] unresolved {hu:>3}/{len(u):<4} resolved {hits(rr):>3}/{len(rr):<4} {txt}")
    print(f"\n{ngen} of {npairs} pairs produced at least one hit")


def three_condition(rows, title, section):
    rule(f"{title} (paper {section})")
    if not rows:
        return
    conds = ("unresolved", "resolved_known", "resolved_unknown")
    for model in sorted({r["model"] for r in rows}):
        core = [r for r in rows if r["model"] == model and r["set"] == "core"]
        ctrl = [r for r in rows if r["model"] == model and r["set"] == "control"]
        print(f"\n--- {model}  ({len(core)+len(ctrl)} trials) ---")
        print(f"{'variant':<9}{'condition':<19}{'hits/n':<13}{'rate':<9}{'95% CI'}")
        for v in VARIANTS:
            for c in conds:
                cell = [r for r in core if r["variant"] == v and r["condition"] == c]
                if not cell:
                    continue
                h, n = hits(cell), len(cell)
                lo, hi = wilson(h, n)
                print(f"{v:<9}{c:<19}{f'{h}/{n}':<13}{100*h/n:<9.2f}"
                      f"{100*lo:.2f}–{100*hi:.2f}%")

        pooled = {}
        print("  pooled across variants")
        for c in conds:
            cell = [r for r in core if r["condition"] == c]
            pooled[c] = (hits(cell), len(cell))
            print(f"    {c:<18}{rate(*pooled[c])}")
        hu, nu = pooled["unresolved"]
        for c in ("resolved_known", "resolved_unknown"):
            h, n = pooled[c]
            o, p = contrast(hu, nu, h, n)
            print(f"    unresolved vs {c:<18} OR={o:>7.2f}  p={p:.4g}")

        # core claim: ungroundable (either kind) vs groundable and known
        hk, nk = pooled["resolved_known"]
        hx, nx = pooled["resolved_unknown"]
        o, p = contrast(hu + hx, nu + nx, hk, nk)
        print(f"    UNGROUNDABLE vs KNOWN   {rate(hu+hx, nu+nx)} vs {rate(hk,nk)}"
              f"  OR={o:.2f}  p={p:.4g}")

        tot = hu + hx + hk
        print(f"    total invocations       {rate(tot, len(core))}")
        if ctrl:
            print(f"    controls                {rate(hits(ctrl), len(ctrl))}")

    models = sorted({r["model"] for r in rows})
    if len(models) > 1:
        print("\ncross-model, unresolved pooled:")
        for m in models:
            cell = [r for r in rows if r["model"] == m and r["set"] == "core"
                    and r["condition"] == "unresolved"]
            print(f"  {m:<40}{rate(hits(cell), len(cell))}")
        for i in range(len(models)):
            for j in range(i + 1, len(models)):
                a = [r for r in rows if r["model"] == models[i] and r["set"] == "core"
                     and r["condition"] == "unresolved"]
                b = [r for r in rows if r["model"] == models[j] and r["set"] == "core"
                     and r["condition"] == "unresolved"]
                o, p = contrast(hits(a), len(a), hits(b), len(b))
                if p < 0.05:
                    print(f"  {models[i]} vs {models[j]}: OR={o:.2f} p={p:.4g}")


def tool_distribution(rows, label):
    if not rows:
        return
    c = Counter()
    for r in rows:
        for t in r["tools_called"].split("|"):
            if t:
                c[t] += 1
    print(f"\ntool distribution — {label}:")
    for t, n in c.most_common(10):
        print(f"  {t:<30}{n}")


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--data-dir", default=os.path.join(here, "..", "data"))
    args = ap.parse_args()
    d = args.data_dir

    print("Reproducing every figure in the preprint from raw per-trial data.")
    print(f"data directory: {os.path.abspath(d)}")

    s1 = load(os.path.join(d, "exp1_results.csv"))
    s2 = load(os.path.join(d, "exp2_results.csv"))
    s3 = load(os.path.join(d, "exp3_results.csv"),
              dedupe_key=("model", "variant", "set", "idx", "condition", "run"))
    s4 = load(os.path.join(d, "cross_vendor_results.csv"),
              dedupe_key=("model", "variant", "set", "idx", "condition", "run"))

    study1(s1)
    study2(s2)
    three_condition(s3, "STUDY 3 — three-condition isolation", "§3.3")
    three_condition(s4, "STUDY 4 — cross-vendor", "§3.4")
    tool_distribution(s4, "Study 4 (paper §3.5)")

    rule("TRIAL LEDGER")
    total = 0
    for name, rows in (("Study 1 — baseline", s1), ("Study 2 — matched pairs", s2),
                       ("Study 3 — three-condition", s3), ("Study 4 — cross-vendor", s4)):
        print(f"  {name:<34}{len(rows):>6}")
        total += len(rows)
    print(f"  {'TOTAL':<34}{total:>6}")
    print("\nNote: Studies 1–3 and Study 4 use different parameter schemas "
          "(see preprint §6.6). Do not pool them.")


if __name__ == "__main__":
    main()
