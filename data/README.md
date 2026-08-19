# Raw per-trial data

Every row is one trial: one prompt sent to one model with one decoy variant in the
catalogue, recording the complete set of tool calls in the first assistant turn.
No tool results are returned to the agent — all studies are single-turn.

## Files

| File | Study | Rows | Models |
|---|---|---|---|
| `exp1_results.csv` | Study 1 — baseline | 3,030 | claude-sonnet-4-6 |
| `exp2_results.csv` | Study 2 — matched pairs | 840 | claude-sonnet-4-6 |
| `exp3_results.csv` | Study 3 — three-condition isolation | 2,400 | claude-sonnet-4-6, claude-haiku-4-5-20251001 |
| `cross_vendor_results.csv` | Study 4 — cross-vendor | 8,252 | six models, two vendors |

Total: 13,470 non-error trials after filtering (see `status` below).

## Schemas

**`exp1_results.csv`**

```
variant, run, prompt_idx, prompt, status, tools_called, decoy_called
```

**`exp2_results.csv`**

```
variant, kind, idx, condition, run, prompt, status, tools_called, decoy_called, error
```

**`exp3_results.csv`** and **`cross_vendor_results.csv`**

```
model, variant, set, idx, condition, run, prompt, status, tools_called, decoy_called, error
```

## Columns

| Column | Meaning |
|---|---|
| `model` | API model identifier. Study 4 prefixes the vendor (`anthropic:`, `openai:`) |
| `variant` | Decoy variant in the catalogue: `low` (`legacy_batch_reconcile_v1`), `medium` (`internal_config_export`), `high` (`list_service_credentials`). Ordered by *a priori* assumed attacker-attractiveness — an ordering the results overturn (paper §5) |
| `set` | `core` (the prompt triples) or `control` (prompts carried from Study 1 that never triggered) |
| `kind` | Study 2 only: `pair` or `control` |
| `idx` / `prompt_idx` | Prompt identifier. **This is the clustering unit for all inference** — see below |
| `condition` | `unresolved` (unnamed referent, "our CDN provider"), `resolved_known` (real named vendor, "Cloudflare"), `resolved_unknown` (fictional named vendor, "Northbrook CDN"), `control`. Study 2 uses `resolved` for the named-vendor condition |
| `run` | Repetition index, 0-based. Each prompt × condition × variant cell is run 10 times |
| `prompt` | Verbatim user-turn text |
| `status` | `OK` or `ERROR`. **Filter to `OK` before analysis** |
| `tools_called` | Pipe-delimited names of every tool invoked in the first assistant turn. Empty string means the model called no tools |
| `decoy_called` | 1 if the decoy variant for that trial appears in `tools_called`, else 0 |
| `error` | Exception text where `status` is `ERROR` |

## Two things to know before analysing this data

### 1. Trials are not independent — cluster on prompt

Each prompt is run 10 times. Treating those 10 runs as 10 independent
observations is pseudo-replication and produces p-values that are far too small.
The effect is severe here because hits concentrate within prompts: in Study 1,
all nine positives came from a single prompt out of 101.

Study 1's attractiveness trend illustrates it:

| Unit | Counts (low / medium / high) | Cochran-Armitage |
|---|---|---|
| Trial | 0/1010, 3/1010, 6/1010 | p = 0.0142 |
| Prompt | 0/101, 1/101, 1/101 | p = 0.3849 |

All inference in the paper uses the prompt (`idx` / `prompt_idx`) as the
clustering unit. See `analysis/stats_final.py`.

### 2. Do not pool Study 4 with Studies 1–3

Study 4's harness reimplemented the tool definitions. Tool *descriptions* are
byte-identical, but the parameter schemas differ: one property is omitted and
some property descriptions changed. All six models in Study 4 saw identical
schemas, so cross-model comparisons within Study 4 are valid — but Study 4 must
not be pooled with the earlier studies.

The visible consequence: Sonnet's configuration-export cell reads 39.17% in
Study 4 against 51.67% in Study 3, on the same prompts.

## Reproducing

```bash
pip install -r ../analysis/requirements.txt
../analysis/run_all.sh
```

Writes descriptive tables, corrected statistics and all figures to `../figures/`.

## Provenance

Collected 3–12 August 2026. Harnesses in `../harnesses/`. Every run is resumable
and deterministically seeded at the registry-ordering level, so tool position
within the catalogue is reproducible per trial but the model's sampling is not
(temperature is at the provider default of 1.0).
