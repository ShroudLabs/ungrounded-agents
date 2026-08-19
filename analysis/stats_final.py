#!/usr/bin/env python3
"""Corrected statistics for the Ungrounded paper: prompt-clustered inference."""
import os, argparse
_ap = argparse.ArgumentParser()
_here = os.path.dirname(os.path.abspath(__file__))
_ap.add_argument("--data-dir", default=os.path.join(_here, "..", "data"))
_ap.add_argument("--out-dir",  default=os.path.join(_here, "..", "figures"))
_a, _ = _ap.parse_known_args()
DATA, OUT = _a.data_dir, _a.out_dir
os.makedirs(OUT, exist_ok=True)
import numpy as np, pandas as pd, warnings, json
from scipy.stats import fisher_exact, wilcoxon
import statsmodels.api as sm, statsmodels.formula.api as smf
warnings.filterwarnings("ignore")
rng = np.random.default_rng(17)


def load(f):
    d = pd.read_csv(os.path.join(DATA, f), encoding="utf-8-sig")
    d = d[d.status == "OK"].copy()
    d["decoy_called"] = d.decoy_called.astype(int)
    d["tools_called"] = d.tools_called.fillna("")
    return d

# ---------- cluster-level inference -----------------------------------------
def cluster_perm(df, group, outcome, treat, n=20000):
    """Permute the treatment label WITHIN each cluster. Assumption-free,
    handles zero cells, respects clustering. Statistic = rate difference."""
    obs = df[df[treat]==1][outcome].mean() - df[df[treat]==0][outcome].mean()
    gs = [g for _, g in df.groupby(group)]
    cnt = 0
    for _ in range(n):
        a = b = an = bn = 0
        for g in gs:
            lab = rng.permutation(g[treat].values)
            y = g[outcome].values
            a += y[lab==1].sum(); an += (lab==1).sum()
            b += y[lab==0].sum(); bn += (lab==0).sum()
        if abs(a/max(an,1) - b/max(bn,1)) >= abs(obs) - 1e-12: cnt += 1
    return obs, (cnt+1)/(n+1)

def cluster_boot_ci(df, group, outcome, n=4000):
    """Bootstrap resampling whole prompts, not trials."""
    gs = [g[outcome].values for _, g in df.groupby(group)]
    k = len(gs)
    means = [np.concatenate([gs[i] for i in rng.integers(0,k,k)]).mean() for _ in range(n)]
    return np.percentile(means, [2.5, 97.5])

def gee_p(df):
    try:
        m = smf.gee("decoy_called ~ ungroundable", groups="idx", data=df,
                    family=sm.families.Binomial(),
                    cov_struct=sm.cov_struct.Exchangeable()).fit()
        b, p = m.params["ungroundable"], m.pvalues["ungroundable"]
        if not np.isfinite(p) or abs(b) > 15: return None, None   # separation
        return float(np.exp(b)), float(p)
    except Exception:
        return None, None

def analyse(df, label, out):
    print("\n" + "="*80); print(label); print("="*80)
    for m in sorted(df.model.unique()):
        core = df[(df.model==m) & (df["set"]=="core")].copy()
        core["ungroundable"] = core.condition.isin(["unresolved","resolved_unknown"]).astype(int)
        ung, kn = core[core.ungroundable==1], core[core.ungroundable==0]
        a, na, b, nb = ung.decoy_called.sum(), len(ung), kn.decoy_called.sum(), len(kn)
        orr, p_trial = fisher_exact([[a,na-a],[b,nb-b]])
        _, p_perm = cluster_perm(core, "idx", "decoy_called", "ungroundable")
        gor, gp = gee_p(core)
        pl = core.groupby(["idx","ungroundable"]).decoy_called.mean().unstack()
        try: _, pw = wilcoxon(pl[1], pl[0])
        except Exception: pw = float("nan")
        lo, hi = cluster_boot_ci(ung, "idx", "decoy_called")
        rec = dict(model=m, ung_hits=int(a), ung_n=na, kn_hits=int(b), kn_n=nb,
                   ung_rate=100*a/na, kn_rate=100*b/nb, ung_ci=[100*lo,100*hi],
                   odds_ratio=float(orr) if np.isfinite(orr) else None,
                   p_trial_fisher=float(p_trial), p_cluster_perm=float(p_perm),
                   p_gee=gp, gee_or=gor, p_wilcoxon=float(pw),
                   prompts_firing=int((pl[1]>0).sum()), n_prompts=len(pl))
        out.append(rec)
        print(f"\n  {m}")
        print(f"    ungroundable {a}/{na} = {100*a/na:5.2f}%  [cluster 95% CI {100*lo:.2f}–{100*hi:.2f}]")
        print(f"    known        {b}/{nb} = {100*b/nb:5.2f}%")
        print(f"    Fisher, trial-level (AS PUBLISHED)   p = {p_trial:.4g}")
        print(f"    Cluster permutation (PRIMARY)        p = {p_perm:.4g}")
        print(f"    GEE, exchangeable, cluster=prompt    " +
              (f"OR = {gor:.2f}, p = {gp:.4g}" if gp else "not estimable (separation)"))
        print(f"    Wilcoxon over {len(pl)} prompts        p = {pw:.4g}")
        print(f"    prompts firing: {(pl[1]>0).sum()}/{len(pl)}")

res = []
analyse(load("exp3_results.csv"), "STUDY 3 — three-condition isolation", res)
analyse(load("cross_vendor_results.csv"), "STUDY 4 — cross-vendor", res)

# ---------- Study 1 pseudo-replication demonstration -------------------------
print("\n" + "="*80); print("STUDY 1 — the withdrawn attractiveness trend"); print("="*80)
e1 = load("exp1_results.csv")
S = {"low":0, "medium":1, "high":2}
def ca(counts):
    xs=[S[k] for k in counts]; rs=[v[0] for v in counts.values()]; ns=[v[1] for v in counts.values()]
    N,R=sum(ns),sum(rs); pb=R/N; xb=sum(n*x for n,x in zip(ns,xs))/N
    num=sum(r*(x-xb) for r,x in zip(rs,xs)); var=pb*(1-pb)*sum(n*(x-xb)**2 for n,x in zip(ns,xs))
    from scipy.stats import norm; z=num/np.sqrt(var); return z, 2*(1-norm.cdf(abs(z)))
trial={v:(int(e1[e1.variant==v].decoy_called.sum()), int((e1.variant==v).sum())) for v in S}
prom ={v:(int(e1[e1.variant==v].groupby("prompt_idx").decoy_called.max().sum()), 101) for v in S}
print("  trial-level  ", trial, "CA p = %.4f"%ca(trial)[1])
print("  prompt-level ", prom,  "CA p = %.4f"%ca(prom)[1])

json.dump(res, open(os.path.join(OUT,"corrected_stats.json"),"w"), indent=2)
print("\nwrote", os.path.join(OUT, "corrected_stats.json"))
