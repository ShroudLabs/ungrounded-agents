#!/usr/bin/env python3
"""Generate all figures for the Ungrounded paper. Vector PDF + PNG preview."""
import os, argparse
_ap = argparse.ArgumentParser()
_here = os.path.dirname(os.path.abspath(__file__))
_ap.add_argument("--data-dir", default=os.path.join(_here, "..", "data"))
_ap.add_argument("--out-dir",  default=os.path.join(_here, "..", "figures"))
_a, _ = _ap.parse_known_args()
DATA, OUT = _a.data_dir, _a.out_dir
os.makedirs(OUT, exist_ok=True)
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
rng = np.random.default_rng(17)


plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150, "savefig.bbox": "tight",
})
GREY = ["#2b2b2b", "#7a7a7a", "#c4c4c4"]

def load(f):
    d = pd.read_csv(os.path.join(DATA, f), encoding="utf-8-sig")
    d = d[d.status=="OK"].copy()
    d["decoy_called"] = d.decoy_called.astype(int)
    d["tools_called"] = d.tools_called.fillna("")
    return d

def boot_ci(vals_by_prompt, n=3000):
    k = len(vals_by_prompt)
    if k == 0: return 0, 0
    ms = [np.concatenate([vals_by_prompt[i] for i in rng.integers(0,k,k)]).mean() for _ in range(n)]
    return np.percentile(ms, [2.5, 97.5])

def short(m): return m.split(":")[-1].replace("-20251001","")

xv = load("cross_vendor_results.csv")
core = xv[xv["set"]=="core"]
CONDS = ["unresolved","resolved_unknown","resolved_known"]
LABELS = ["Unnamed referent\n(\"our CDN provider\")","Named but unfamiliar\n(\"Northbrook CDN\")","Named and familiar\n(\"Cloudflare\")"]
models = sorted(core.model.unique(), key=lambda m: -core[(core.model==m)&(core.condition=="unresolved")].decoy_called.mean())

# ---- Figure 1: decoy rate by condition and model ---------------------------
fig, ax = plt.subplots(figsize=(7.0, 3.4))
w, x = 0.26, np.arange(len(models))
for i, c in enumerate(CONDS):
    rates, los, his = [], [], []
    for m in models:
        s = core[(core.model==m)&(core.condition==c)]
        rates.append(100*s.decoy_called.mean())
        gp = [g.decoy_called.values for _, g in s.groupby("idx")]
        lo, hi = boot_ci(gp); los.append(100*lo); his.append(100*hi)
    rates = np.array(rates)
    err = np.vstack([rates-np.array(los), np.array(his)-rates]).clip(0)
    ax.bar(x+(i-1)*w, rates, w, yerr=err, capsize=2, color=GREY[i],
           edgecolor="black", linewidth=.4, error_kw=dict(lw=.7))
ax.set_xticks(x); ax.set_xticklabels([short(m) for m in models], rotation=18, ha="right")
ax.set_ylabel("Decoy tool invocation (%)")
ax.set_title("Decoy invocation by entity grounding condition\n(error bars: 95% CI, bootstrapped over prompts)")
ax.legend(handles=[Patch(facecolor=GREY[i], edgecolor="black", lw=.4, label=l.replace("\n"," "))
                   for i, l in enumerate(LABELS)], frameon=False, loc="upper right")
fig.savefig(os.path.join(OUT,"fig1_decoy_by_condition.pdf")); fig.savefig(os.path.join(OUT,"fig1_decoy_by_condition.png")); plt.close(fig)

# ---- Figure 2: tool routing gradient (THE mechanism figure) ----------------
fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
groups = {"fetch_url (correct tool)": ["fetch_url"],
          "internal search": ["search_docs","search_code"],
          "internal_config_export (decoy)": ["internal_config_export"]}
for ax, (title, sub) in zip(axes, [("All six models pooled", core), (None, None)]):
    pass
ax = axes[0]
for j, (lab, tools) in enumerate(groups.items()):
    ys = []
    for c in CONDS:
        s = core[core.condition==c]
        ys.append(100*np.mean([any(t in r.split("|") for t in tools) for r in s.tools_called]))
    ax.plot([0,1,2], ys, marker="os^"[j], color=GREY[j%3] if j<2 else "#000000",
            lw=1.4, ms=5, label=lab, ls=["-","--",":"][j])
ax.set_xticks([0,1,2]); ax.set_xticklabels(["unnamed","named,\nunfamiliar","named,\nfamiliar"])
ax.set_ylabel("Trials invoking tool (%)"); ax.set_ylim(-3,103)
ax.set_title("Tool routing collapses when\nthe entity cannot be grounded")
ax.legend(frameon=False, fontsize=7.5)
ax2 = axes[1]
for i, m in enumerate(models):
    ys = [100*np.mean(["fetch_url" in r.split("|") for r in core[(core.model==m)&(core.condition==c)].tools_called]) for c in CONDS]
    ax2.plot([0,1,2], ys, marker="o", ms=3.5, lw=1.1, color=plt.cm.Greys(0.35+0.11*i), label=short(m))
ax2.set_xticks([0,1,2]); ax2.set_xticklabels(["unnamed","named,\nunfamiliar","named,\nfamiliar"])
ax2.set_ylabel("fetch_url invoked (%)"); ax2.set_ylim(-3,103)
ax2.set_title("The same gradient in every model")
ax2.legend(frameon=False, fontsize=6.5, ncol=2)
fig.savefig(os.path.join(OUT,"fig2_tool_routing.pdf")); fig.savefig(os.path.join(OUT,"fig2_tool_routing.png")); plt.close(fig)

# ---- Figure 3: per-prompt heterogeneity ------------------------------------
fig, ax = plt.subplots(figsize=(7.0, 3.0))
sub = core[core.model=="anthropic:claude-sonnet-4-6"]
pr = sub[sub.condition=="unresolved"].groupby("idx").decoy_called.mean()*100
pk = sub[sub.condition=="resolved_known"].groupby("idx").decoy_called.mean()*100
x = np.arange(len(pr))
ax.bar(x-0.19, pr.values, 0.38, color=GREY[0], edgecolor="black", lw=.4, label="ungroundable (unnamed)")
ax.bar(x+0.19, pk.reindex(pr.index).values, 0.38, color=GREY[2], edgecolor="black", lw=.4, label="groundable (named, familiar)")
ax.set_xticks(x); ax.set_xticklabels([f"P{i}" for i in pr.index])
ax.set_xlabel("Prompt triple"); ax.set_ylabel("Decoy invocation (%)")
ax.set_title("The effect is a prompt class, not one prompt (claude-sonnet-4-6)")
ax.legend(frameon=False)
fig.savefig(os.path.join(OUT,"fig3_per_prompt.pdf")); fig.savefig(os.path.join(OUT,"fig3_per_prompt.png")); plt.close(fig)

# ---- Figure 4: variant inversion -------------------------------------------
fig, ax = plt.subplots(figsize=(4.6, 3.0))
e1 = load("exp1_results.csv")
s1 = [100*e1[e1.variant==v].decoy_called.mean() for v in ["low","medium","high"]]
s4 = [100*core[(core.variant==v)&(core.condition=="unresolved")].decoy_called.mean() for v in ["low","medium","high"]]
x = np.arange(3)
ax.bar(x-0.19, s1, 0.38, color=GREY[2], edgecolor="black", lw=.4, label="Study 1 (all prompts)")
ax.bar(x+0.19, s4, 0.38, color=GREY[0], edgecolor="black", lw=.4, label="Study 4 (ungroundable)")
ax.set_xticks(x)
ax.set_xticklabels(["legacy_batch\n(low)","config_export\n(medium)","credentials\n(high)"], fontsize=7)
ax.set_xlabel("Decoy variant, ordered by a priori attacker-attractiveness")
ax.set_ylabel("Decoy invocation (%)")
ax.set_title("Attacker-attractiveness is the\nwrong placement heuristic")
ax.legend(frameon=False, fontsize=7.5)
fig.savefig(os.path.join(OUT,"fig4_variant_inversion.pdf")); fig.savefig(os.path.join(OUT,"fig4_variant_inversion.png")); plt.close(fig)
print("figures written")
