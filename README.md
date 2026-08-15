# Ungrounded

**Entity grounding failure drives spurious internal-tool invocation in LLM agents.**

Four studies, 13,470 trials, six models, two vendors. Harnesses, raw per-trial data, and analysis scripts.

📄 Preprint: [`paper/preprint.md`](paper/preprint.md) · DOI: 10.5281/zenodo.21958704
🔬 Full record: [`docs/MASTER_BRIEFING.md`](docs/MASTER_BRIEFING.md)

---

## What this is

Canary tokens work because nothing legitimate touches them. Connect an LLM agent to internal tools over MCP and the same primitive suggests itself: plant a decoy tool no legitimate task should ever call, alert when something calls it.

That only works if benign agents leave it alone. Nobody had measured whether they do.

We did — and the answer turned out to be less about the decoy than about the request. When an agent cannot ground an entity it has been asked about, because the entity is unnamed (*"our CDN provider"*) or named but unfamiliar (*"Northbrook CDN"*), it reaches into internal-lookup tools to work out what the thing is. A configuration-export decoy fires on up to **51.67%** of such requests. A credential-listing decoy stays largely quiet — inverting the placement heuristic you would reach for intuitively.

The effect is significant in **five of six models across two vendors**, with matched controls at zero throughout. One model recorded a single invocation in 1,200 trials, which suggests the behaviour is trainable away rather than inherent to tool-using agents.

## Headline numbers

| Model | Ungroundable entity | Known entity | p |
|---|---|---|---|
| `claude-sonnet-4-6` | 12.64% | 0.83% | 1.0 × 10⁻¹³ |
| `gpt-5.6-terra` | 10.42% | 1.94% | 7.7 × 10⁻⁸ |
| `claude-haiku-4-5` | 5.56% | 1.11% | 2.4 × 10⁻⁴ |
| `gpt-5.6-sol` | 5.00% | 0.28% | 7.8 × 10⁻⁶ |
| `gpt-5.6-luna` | 4.03% | 0.00% | 9.0 × 10⁻⁶ |
| `claude-opus-5` | 0.14% | 0.00% | n.s. |

Controls: 0/120 on every model.

## Two findings we withdrew

This work overturned two of our own hypotheses. Both are documented rather than quietly dropped:

- **Attractiveness monotonicity.** The baseline suggested spurious invocation rises with how attractive a decoy looks to an attacker. It rested on nine observations and reverses at higher n, in both vendors.
- **A fixed ambiguity/unknowability split.** The two components of the effect exist, but their relative weight is model-specific, not a constant.

See §5 of the preprint.

## Repository layout

```
harnesses/     four experiment harnesses, all resumable
data/          raw per-trial CSVs for every study
analysis/      analysis and statistics scripts
paper/         preprint
docs/          master briefing — complete record incl. limitations
```

## Reproducing

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic requests scipy
export ANTHROPIC_API_KEY=...

# Study 1 — baseline, 3,030 trials
python3 harnesses/decoy_tool_fp_experiment.py --variant all --runs 10

# Study 3 — three-condition isolation, 1,200 trials per model
python3 harnesses/exp3.py --runs 10 --models claude-sonnet-4-6

# Study 4 — cross-vendor, 1,200 trials per model
export OPENAI_API_KEY=...
python3 harnesses/cross_vendor.py --list-models openai   # get current model IDs
python3 harnesses/cross_vendor.py --runs 10 \
  --models anthropic:claude-sonnet-4-6 openai:<id>
```

All runs are resumable — rerun the same command after an interruption and it continues. Failed trials retry automatically. Tool position within the registry is shuffled per trial so ordering cannot confound condition.

Re-analyse existing data without spending API calls:

```bash
python3 harnesses/cross_vendor.py analyse data/cross_vendor_results.csv
```

## Limitations

Read §6 of the preprint before building on this. The material ones in brief: stimuli were LLM-authored after the hypothesis was formed; only two vendors were tested; all trials are single-turn with no tool results returned; the Study 4 harness has parameter-schema drift from Studies 1–3, so those datasets must not be pooled; and no true-positive rate was measured — this characterises false positives only.

## Citing

See [`CITATION.cff`](CITATION.cff), or use GitHub's *Cite this repository* button.

## Licence

Code: [MIT](LICENSE). Data and paper: [CC BY 4.0](LICENSE-DATA).

---

Research by [Taran Douley](https://github.com/ShroudLabs) at [Shroud Labs](https://shroudlabs.io).
