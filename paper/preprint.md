# Ungrounded: Entity Grounding Failure Drives Tool Misselection in LLM Agents

**Taran Douley**
Independent Researcher, United Kingdom
taran@shroudlabs.io · ORCID: 0009-0002-3673-4500

*Preprint. August 2026.*

---

## Abstract

Tool-using language model agents must decide which tool to invoke, and whether to invoke one at all. Benchmarks measure how often that choice is correct; less is known about what an agent reaches for when the correct choice is unavailable to it.

We instrument tool selection with a decoy — a tool no legitimate task should ever call — which makes misselection directly observable. Across 101 benign engineering prompts spurious invocation was rare (0–0.59%), but every positive trial came from a single prompt, and that prompt turned out to belong to a class.

When an agent cannot ground an entity referenced in a request, because it is unnamed ("our CDN provider") or named but unfamiliar ("Northbrook CDN"), it invokes internal-lookup tools to resolve the entity as a prerequisite sub-goal. Tool-routing data identifies the pathway. The tool that legitimately serves these requests is invoked in 78.1% of trials when the entity is groundable and 5.0% when it is not, with the same gradient in all six models tested. The correct tool is not absent; it is rendered inapplicable, since a URL cannot be fetched for a provider that cannot be named. The agent substitutes a broad configuration-export tool, which fires on up to 51.67% of ungroundable requests.

Under prompt-clustered inference the effect holds in five of six models across two vendors, with matched controls at zero throughout. One model recorded a single invocation in 720 ungroundable trials without elevated abstention, routing to legitimate internal search instead — evidence that the behaviour is tractable to training rather than inherent to tool use.

**Keywords:** LLM agents, tool selection, function calling, agent reliability, abstention, Model Context Protocol

---

## 1. Introduction

A tool-using language model agent must decide, for each request, which of the available tools to invoke and whether to invoke any at all. Existing benchmarks measure how often that decision is correct [13, 17]. Comparatively little is known about its failure modes — in particular, what an agent reaches for when the tool that would serve the request is unavailable to it.

Measuring misselection directly is awkward, because a wrong tool call is usually only wrong in context, and adjudicating each call requires a ground-truth trajectory. We borrow an instrument from a different field to avoid that problem. Canary tokens and honey accounts [1] derive their signal quality from an asymmetry: legitimate users have no reason to touch them, so every alert is real. A tool with the same property — one no legitimate task should ever call — placed in an agent's registry makes misselection observable without per-call adjudication. This paper uses such a decoy tool as a probe.

The instrument also has a defensive application, and that is where this work began. If benign agents reliably leave a decoy tool alone, it is a tripwire on a surface with little existing instrumentation. That application depends on a false-positive rate which, to our knowledge, has not been published. Measuring it produced the reliability result that is the substance of this paper, and a corollary about decoy placement reported in §7.

**Contributions.**

1. Identification of entity grounding failure as a driver of tool misselection in LLM agents, with matched-control isolation of two contributing components.
2. Direct tool-routing evidence for the pathway: the correct tool is selected when the entity is groundable and abandoned when it is not, in every model tested.
3. Cross-vendor replication across six models and two vendors (7,200 trials), under inference clustered on the prompt.
4. Evidence that one production model does not exhibit the behaviour, and that its immunity is not explained by increased abstention.
5. A false-positive baseline for decoy tools in an agent tool registry (3,030 trials), and the resulting placement corollary.
6. Retraction of three of our own earlier hypotheses, with the data that overturned them.

### 1.1 Related work

**Function-calling reliability.** A body of work measures how reliably models select and invoke tools under benign conditions. The Berkeley Function Calling Leaderboard [13] evaluates serial and parallel calls across languages using abstract-syntax-tree matching, and — most relevantly here — includes explicit irrelevance-detection and relevance-detection categories that test whether a model correctly declines to call a tool when none is appropriate. ToolBench [14] and its successor StableToolBench [15] evaluate tool use against large API collections; ToolSandbox [16] adds stateful, conversational evaluation; τ-bench [17] evaluates agents in dynamic conversations against domain policy, and reports that state-of-the-art function-calling agents succeed on fewer than half of its tasks and behave inconsistently across repeated trials.

**Adversarial manipulation of tool registries.** Existing MCP security research concentrates on attacks against the registry itself. Invariant Labs characterised Tool Poisoning Attacks [5], in which instructions are embedded in tool descriptions at registration, together with shadowing and rug-pull variants; MCPTox [6] provides a large-scale empirical benchmark for this class. Wang et al. [7] extend the surface to tool selection, showing that persuasive or genetic-algorithm-optimised descriptions can bias which tool an agent chooses. A parallel line addresses transport-layer defects, including missing DNS rebinding protection in both official SDKs [8, 9]. Broader agent-security work covers indirect prompt injection, where instructions reach the agent through content it reads rather than through the user turn [10], with benchmarks including AgentDojo [11] and InjecAgent [12].

All of this work requires an adversary. The present work does not: tool descriptions are ordinary, prompts are benign, and misselection arises from a property of the request rather than of the registry. We use a decoy tool as a measurement instrument, not as a defence.

Our work sits adjacent to this literature but asks a different question. Irrelevance detection asks whether the model abstains when *no relevant tool exists*. We study the case where the relevant tool *does* exist and is correctly identified in the groundable condition, but becomes unusable because a required argument cannot be obtained — and we measure what the model reaches for instead. The failure is therefore not one of tool identification but of behaviour under an unsatisfiable precondition.

**Behaviour under epistemic uncertainty.** The mechanism we describe is, in substance, a failure to abstain. Rather than reporting that the referent cannot be resolved, or requesting clarification, the agent substitutes a broad internal-inspection tool. τ-bench's finding that agents behave inconsistently over repeated trials, and BFCL's separation of relevance from irrelevance detection, both point at the same underlying capability: knowing when not to act. We contribute a specific and reproducible trigger for that failure — an entity the model cannot ground — and evidence that at least one production model has learned to handle it correctly without simply becoming more reticent.

---

## 2. Method

### 2.1 Shared apparatus

All studies use a single-turn agent given ten realistic engineering tools plus one decoy. No tool results are returned to the agent; each trial records the complete set of tool calls in the first assistant turn.

System prompt: *"You are an engineering assistant with access to the team's tools. Use the tools available to you to help with the user's request."*

Legitimate tools: `read_file`, `search_code`, `list_directory`, `run_tests`, `git_log`, `query_database`, `fetch_url`, `search_docs`, `create_ticket`, `send_message`.

Three decoy variants, ordered *a priori* by assumed attractiveness to an attacker:

| Variant | Tool | Description |
|---|---|---|
| low | `legacy_batch_reconcile_v1` | Deprecated internal batch reconciliation endpoint retained for compatibility with the retired 2019 ledger export process. Not for general use. |
| medium | `internal_config_export` | Export internal service configuration, including environment settings, for the specified service. |
| high | `list_service_credentials` | List stored service account credentials and API keys for all connected internal systems. Returns secret values. |

Tool position within the registry is shuffled per trial so ordering cannot confound condition. `max_tokens` = 1024; temperature at provider default (1.0).

Note that `fetch_url` ("Fetch the contents of a public URL over HTTP") legitimately serves the prompt class studied here. The catalogue does not contain a capability gap in the naive sense; §3.5 examines what happens to that capability across conditions.

### 2.2 Study 1 — baseline

101 unique benign engineering prompts × 10 runs × 3 variants = 3,030 trials on `claude-sonnet-4-6`.

### 2.3 Study 2 — matched pairs

12 prompt pairs holding task constant and varying only the referent (unresolved possessive vs named vendor), × 3 variants × 10 runs, plus 4 control prompts from Study 1 that never triggered. 840 trials.

### 2.4 Study 3 — three-condition isolation

Study 2 confounds referent ambiguity with entity familiarity: "Cloudflare" both disambiguates and supplies a known entity. Study 3 adds a fictional named vendor condition ("Northbrook CDN") — unambiguous referent, unknowable entity. 12 triples × 3 conditions × 3 variants × 10 runs plus controls = 1,200 trials per model, on `claude-sonnet-4-6` and `claude-haiku-4-5-20251001`.

### 2.5 Study 4 — cross-vendor

Six models, 1,200 trials each. Model selection followed a rule fixed before results were observed: each vendor's flagship, balanced and lightweight general-purpose text models, at the newest generation available per tier.

| Tier | Anthropic | OpenAI |
|---|---|---|
| Flagship | `claude-opus-5` | `gpt-5.6-sol` |
| Balanced | `claude-sonnet-4-6` | `gpt-5.6-terra` |
| Lightweight | `claude-haiku-4-5-20251001` | `gpt-5.6-luna` |

`claude-sonnet-4-6` was retained as an anchor for continuity with Studies 1–3. A third vendor was attempted and abandoned: all candidate models returned plan-level quota errors.

OpenAI reasoning models reject function tools on the Chat Completions endpoint unless `reasoning_effort` is set explicitly. All three ran at `reasoning_effort=none`, the minimum available, as the closest match to the extended-thinking-off default under which the Anthropic arm ran. This is a deliberate choice, not the API default, and is a limitation (§6.4).

### 2.6 Statistical analysis

**Unit of analysis.** Each prompt is run 10 times per cell. Trials within a prompt are not independent, and treating them as such is pseudo-replication: it inflates the effective sample size and produces standard errors that are too small. The effect is severe in this data because invocations concentrate within prompts — in Study 1, all nine positives came from one prompt out of 101. All inference below therefore treats the prompt as the clustering unit. Twelve prompt triples, not 720 or 1,080 trials, is the sample size that governs precision.

**Primary test.** A cluster permutation test: the condition label is permuted *within* each prompt, preserving the clustering structure, and the observed rate difference is compared against 20,000 such permutations. This makes no distributional assumptions and remains valid when a cell contains zero events. The Monte Carlo resolution floor is 1/20,001 ≈ 5 × 10⁻⁵; results at that floor are reported as *p* < 10⁻⁴.

**Secondary tests.** Generalised estimating equations (logistic, exchangeable working correlation, clustered on prompt) provide a population-average odds ratio with cluster-robust standard errors. GEE is reported as a cross-check rather than as the primary test, because its asymptotics are unreliable with twelve clusters, and because it is not estimable under complete separation (§3.4). A Wilcoxon signed-rank test over the 12 prompt-level rate pairs provides a conservative robustness check.

**Resolution limit.** With 12 prompt triples, the smallest two-sided *p* obtainable from a signed-rank test is 2/2¹² ≈ 4.9 × 10⁻⁴. No test on this design can support claims beyond that order of magnitude, and the earlier version of this work reported trial-level *p*-values that did.

**Intervals.** Binomial confidence intervals are cluster bootstrap intervals, resampling whole prompts with replacement (4,000 replicates), rather than Wilson intervals on trial counts.

**Multiplicity.** Approximately 40 tests are reported. The confirmatory contrasts in §3.3 and §3.4 clear a Bonferroni threshold of 0.05/40 = 1.25 × 10⁻³ except where noted. The per-model decompositions in §5 are exploratory and are labelled as such.

---

## 3. Results

Per-model totals are reported over the 1,080 core trials, excluding the 120 control trials. Where the abstract refers to 1,200 trials per model it means the full allocation including controls.

### 3.1 Study 1 — baseline and the single-prompt anomaly

| Variant | Hits | Trials | Rate |
|---|---|---|---|
| low | 0 | 1,010 | 0.00% |
| medium | 3 | 1,010 | 0.30% |
| high | 6 | 1,010 | 0.59% |

All nine positive trials came from one prompt: *"Get the status page contents for our CDN provider."* The remaining 100 prompts produced zero hits across 3,000 trials. Conditional on the single prompt, rates were 0% / 30% / 60%.

At the prompt level the three variants produced 0, 1 and 1 hitting prompts out of 101. We initially read a monotonic trend into these counts; §5 explains why that reading was invalid.

### 3.2 Study 2 — the prompt belongs to a class

| Condition | Hits | Trials | Rate |
|---|---|---|---|
| Unresolved referent | 67 | 360 | 18.61% |
| Named vendor | 0 | 360 | 0.00% |
| Controls | 0 | 120 | 0.00% |

Eleven of twelve pairs produced at least one hit. Prompt-level Wilcoxon signed-rank: *p* = 9.77 × 10⁻⁴, at the resolution floor for 12 pairs.

The variant ordering inverted relative to Study 1: `internal_config_export` 60/120 (50.00%), `list_service_credentials` 7/120 (5.83%), `legacy_batch_reconcile_v1` 0/120.

### 3.3 Study 3 — isolating the components

Pooled across variants:

| Condition | Sonnet 4-6 | Haiku 4-5 |
|---|---|---|
| Unresolved | 69/360 = 19.17% | 27/360 = 7.50% |
| Fictional vendor | 43/360 = 11.94% | 16/360 = 4.44% |
| Real vendor | 8/360 = 2.22% | 5/360 = 1.39% |
| Controls | 0/120 | 0/120 |

Configuration-export variant, where the effect concentrates:

| Condition | Sonnet 4-6 | Haiku 4-5 |
|---|---|---|
| Unresolved | 62/120 = 51.67% | 26/120 = 21.67% |
| Fictional vendor | 39/120 = 32.50% | 15/120 = 12.50% |
| Real vendor | 5/120 = 4.17% | 2/120 = 1.67% |

Core contrast — ungroundable entity (unnamed or unfamiliar) versus groundable and familiar:

| Model | Ungroundable | Known | Permutation | GEE | Wilcoxon | Prompts firing |
|---|---|---|---|---|---|---|
| `claude-sonnet-4-6` | 15.56% | 2.22% | *p* < 10⁻⁴ | OR 8.11, *p* = 2.14 × 10⁻⁴ | 4.88 × 10⁻⁴ | 12/12 |
| `claude-haiku-4-5` | 5.97% | 1.39% | *p* = 3.5 × 10⁻⁴ | OR 4.51, *p* = 5.47 × 10⁻³ | 0.078 (n.s.) | 8/12 |

The Haiku arm is significant under the primary test but not under the conservative prompt-level test. We report it as not established by this study; it replicates in Study 4 (§3.4).

### 3.4 Study 4 — cross-vendor

Core contrast, with cluster bootstrap intervals on the ungroundable rate:

| Model | Ungroundable [95% CI] | Known | Permutation | GEE | Wilcoxon | Prompts firing |
|---|---|---|---|---|---|---|
| `claude-sonnet-4-6` | 12.64% [6.11–19.58] | 0.83% | *p* < 10⁻⁴ | OR 17.2, *p* = 2.70 × 10⁻⁴ | 0.0088 | 11/12 |
| `gpt-5.6-terra` | 10.42% [6.11–14.72] | 1.94% | *p* < 10⁻⁴ | OR 5.9, *p* = 6.06 × 10⁻³ | 9.77 × 10⁻⁴ | 11/12 |
| `claude-haiku-4-5` | 5.56% [2.22–9.44] | 1.11% | *p* = 1.5 × 10⁻⁴ | OR 5.2, *p* = 2.04 × 10⁻⁶ | 0.0078 | 8/12 |
| `gpt-5.6-sol` | 5.00% [1.94–9.44] | 0.28% | *p* < 10⁻⁴ | OR 18.9, *p* = 4.90 × 10⁻³ | 0.0039 | 9/12 |
| `gpt-5.6-luna` | 4.03% [1.39–7.36] | 0.00% | *p* < 10⁻⁴ | not estimable | 0.031 | 6/12 |
| `claude-opus-5` | 0.14% [0.00–0.42] | 0.00% | *p* = 1 (n.s.) | not estimable | 1 (n.s.) | 1/12 |

Odds ratios are undefined for Luna and Opus 5 because the reference condition contains zero events; GEE does not converge under complete separation. The permutation test operates on a rate difference and is unaffected.

Controls: 0/120 on every model. All six arms completed with zero request errors.

Configuration-export cell, unresolved condition (120 trials each): Sonnet 4-6 39.17%, Terra 30.00%, Haiku 13.33%, Sol 4.17%, Luna 2.50%, Opus 5 0.00%.

### 3.5 Tool routing — the correct tool is present and abandoned

The prompts studied here are legitimately served by `fetch_url`. Whether the agent uses it depends almost entirely on whether the entity can be grounded. Proportion of trials invoking each tool at least once, pooled across all six models:

| Tool | Unnamed referent | Named, unfamiliar | Named, familiar |
|---|---|---|---|
| `fetch_url` (correct tool) | 5.0% | 15.1% | **78.1%** |
| internal search (`search_docs`, `search_code`) | 67.7% | 77.2% | 14.7% |
| `internal_config_export` (decoy) | 5.0% | 5.8% | 0.3% |

The gradient holds in every model independently:

| Model | Unnamed | Named, unfamiliar | Named, familiar |
|---|---|---|---|
| `claude-opus-5` | 0.0% | 0.0% | 83.3% |
| `claude-sonnet-4-6` | 4.7% | 28.6% | 82.5% |
| `gpt-5.6-terra` | 7.8% | 23.3% | 82.2% |
| `gpt-5.6-luna` | 16.4% | 22.2% | 79.7% |
| `gpt-5.6-sol` | 0.0% | 5.8% | 77.2% |
| `claude-haiku-4-5` | 0.8% | 10.6% | 63.9% |

Across Study 4's 7,200 trials the aggregate tool distribution is: `search_docs` 3,513, `fetch_url` 2,677, `search_code` 2,043, `query_database` 310, `internal_config_export` 239, `list_directory` 175, `read_file` 162, `git_log` 71, `list_service_credentials` 48, `run_tests` 7. The 48 credential-decoy invocations against 239 configuration-export invocations, across identical trial counts, is the aggregate form of the placement argument in §7.

---

## 4. Mechanism

> When a tool-using agent cannot ground an entity referenced in a request — because the entity is unnamed or named but unfamiliar — the tool that would serve the request becomes unusable, and the agent substitutes an internal-lookup tool in an attempt to resolve the entity first.

Two explanations are commonly offered for spurious tool invocation, and this data separates them.

**Semantic collision** — that the decoy description is simply similar to the request — is ruled out by construction. `internal_config_export` and `list_service_credentials` are not semantically near "fetch a status page," and the matched conditions in Studies 2–4 hold the request text nearly constant while varying only the referent.

**Capability vacuum** — that the decoy fires because no legitimate tool serves the task — is ruled out empirically by §3.5. The legitimate tool is present and is invoked in 78.1% of trials when the entity is groundable.

The correct account is that these are not alternatives but a sequence. Grounding failure *creates* the capability vacuum: `fetch_url` requires a URL, and a URL cannot be supplied for a provider that cannot be identified. The tool remains in the catalogue and becomes inapplicable. The agent then treats entity resolution as a prerequisite sub-goal, routes to internal search (67.7% of ungroundable trials), and reaches the configuration export en route.

This accounts for which decoy fires. The decoy that fires is the one plausibly answering *what is this thing?* A configuration export is a defensible way to discover which vendor an organisation uses; a credential dump is not. It also predicts the inversion of the *a priori* attractiveness ordering, and the tool distribution in §3.5 is consistent with a resolution attempt in progress.

The framing is testable. If grounding failure is what renders the correct tool inapplicable, then supplying a tool that resolves internal vendor references should restore correct routing and silence the decoy. That experiment is not reported here (§7).

---

## 5. Findings withdrawn

We report three of our own hypotheses that did not survive, and one that we tested and rejected.

**Attractiveness monotonicity.** Study 1 reported spurious invocation rising with assumed attacker-attractiveness (*p* = 0.014). That test was invalid: it treated 10 runs of each prompt as 10 independent observations, when all nine positives came from a single prompt. Computed with the prompt as the unit of analysis, the counts are 0/101, 1/101 and 1/101, and the trend disappears (Cochran-Armitage *p* = 0.385; low vs high *p* = 1.000). The finding was never supported. It is also contradicted at higher *n*: configuration export outfires credential listing in four of six models, ties in one, and reverses marginally in one (Sol: 4.17% vs 5.00%). Attacker-attractiveness is the wrong heuristic for decoy placement.

**A fixed ambiguity/unknowability split.** Study 3 decomposed the effect approximately 60% unknowability, 40% ambiguity. Study 4 shows the split direction is model-specific: `gpt-5.6-luna` (0.83% unresolved vs 7.22% fictional) and `gpt-5.6-sol` are driven almost entirely by unknowability; `gpt-5.6-terra` runs the opposite way (15.00% vs 5.83%); Sonnet and Haiku show no significant difference. These per-model contrasts are exploratory. The mechanism is general; the weighting is not.

**Capability scaling.** Study 3 suggested invocation scales with model capability (Sonnet vs Haiku OR = 2.92). This failed to generalise. Neither vendor's ordering is monotonic in capability, and the balanced tier fires most in both.

**Abstention as the explanation for immunity (tested and rejected).** A natural reading of the `claude-opus-5` result is that it avoids the decoy by declining to act when it cannot ground the entity. This is false. Opus 5 shows a 0.0% zero-tool rate in every condition and averages 2.04 tool calls per trial under ungroundable entities, invoking `search_docs` in 716 of 720 ungroundable trials and `search_code` in 696. Its mechanism is correct tool selection under uncertainty, not caution.

Abstention also fails to explain the cross-model pattern. Zero-tool rates under unnamed referents range from 76.7% (Haiku, which still fires at 5.28%) to 2.2% (Luna, which fires at 0.83%), with `gpt-5.6-terra` abstaining in 4.7% of trials while recording the highest decoy rate at 15.00%. There is no relationship between how often a model declines to act and how often it invokes the decoy.

---

## 6. Limitations

1. **Stimulus authorship.** All prompt triples and fictional vendor names were generated with LLM assistance after the hypothesis was formed. Construct-fitting is not excluded. Independently authored stimuli are in collection.
2. **Ecological validity.** One independent author, briefed blind, produced 20 realistic assistant requests of which none fell in the target class. The brief was ambiguous regarding tool access and has been revised, but the result bears on how frequently this prompt class arises naturally.
3. **Two vendors.** A third was attempted and blocked by plan-level quota.
4. **Reasoning configuration.** OpenAI models ran at `reasoning_effort=none`, not the API default.
5. **Single-turn.** No tool results are returned, so post-invocation escalation is untested. This measures invocation, not consequence.
6. **Schema drift between studies.** Study 4's harness reimplemented the tool definitions; descriptions are byte-identical but parameter schemas differ from Studies 1–3 (one property omitted, some property descriptions changed). All six models in Study 4 saw identical schemas, so cross-model comparisons hold, but Study 4 must not be pooled with Studies 1–3. Sonnet's configuration-export cell reads 39.17% in Study 4 against 51.67% in Study 3, plausibly for this reason.
7. **Run-to-run variance.** The named-vendor condition gave 0/360 in Study 2 and 8/360 in Study 3 with identical prompts.
8. **Stimulus set size.** Twelve triples. This is the binding constraint on precision: no test on this design can resolve *p* below roughly 5 × 10⁻⁴. Per-prompt breakdowns are released so concentration can be assessed directly.
9. **No true-positive measurement.** This work characterises false positives only. Whether a decoy tool detects an actual adversary is untested.
10. **Adversarial delivery untested.** All prompts were authored benignly and delivered through the user turn. Whether an attacker can induce this by placing an unfamiliar entity name into content an agent reads is not demonstrated here.

---

## 7. Implications

The recommendations below follow from single-turn invocation data. None of them has been tested as an intervention, and they should be read as hypotheses generated by this work rather than as validated mitigations.

**Agent tool catalogues.** Broad configuration-export tooling attracts invocation independent of any adversary. On the worst-affected model, roughly one in two ungroundable requests reaches for it. If §4 is correct, the mitigation is to supply what the agent is actually looking for: an explicit entity-resolution tool, gated and audited, rather than leaving internal-inspection tools as the nearest available substitute.

**Evaluation.** Existing tool-use benchmarks score whether the correct tool is called, and whether a model abstains when no tool applies. Neither measures what is called when the correct tool is identified but its preconditions cannot be met. The condition contrast used here — the same request with a groundable and an ungroundable referent — is cheap to add to an existing suite and isolates that case directly.

**Tractability.** `claude-opus-5` recorded one invocation in 720 ungroundable trials while showing no elevated abstention, indicating that the behaviour is amenable to training intervention rather than inherent to tool-using agents. What appears to have been trained is not reticence but correct routing under uncertainty.

**Decoy placement (security corollary).** Place decoys where they cannot plausibly resolve a sub-goal. A credential-listing decoy is generally quiet; a configuration-export decoy is not. Expect noise wherever agents encounter entities they cannot ground.

**Detection.** The anomaly is not in the request, the permissions, or the user. A least-privilege gateway observes a correctly permissioned agent making an authorised call on behalf of a user with normal history. On this data the discriminating signal is the grounding state of the entity under discussion — a quantity no current control measures. Whether it can be measured reliably in production is untested.

**Next experiment.** The mechanism in §4 predicts that adding a tool which resolves internal vendor references will restore `fetch_url` routing and silence the decoy. This is a direct test and is the natural successor to this work.

---

## 8. Availability

Harnesses, per-trial raw data for all four studies, analysis scripts, and the figure-generation code: `github.com/ShroudLabs/ungrounded-agents`

Archived release: [10.5281/zenodo.21958705](https://doi.org/10.5281/zenodo.21958705)

All runs are resumable and deterministically seeded at the registry-ordering level. Every table and figure in this paper regenerates from raw per-trial data via `analysis/run_all.sh`.

### Use of AI assistance

The prompt stimuli and fictional vendor names were generated with LLM assistance (§6.1). LLM assistance was also used in statistical analysis and in drafting this manuscript. All experimental design, hypotheses, analysis decisions and conclusions are the author's, who takes full responsibility for the content, including any errors.

---

## Acknowledgements

*[Independent stimulus authors, once they have consented to be named.]*

---

## References

[1] Thinkst Applied Research. Canary and Canarytokens. https://canary.tools

[2] Model Context Protocol specification. https://modelcontextprotocol.io

[3] Wilson, E.B. (1927). Probable inference, the law of succession, and statistical inference. *JASA* 22(158), 209–212.

[4] Armitage, P. (1955). Tests for linear trends in proportions and frequencies. *Biometrics* 11(3), 375–386.

[5] Beurer-Kellner, L. and Fischer, M. (2025). MCP Security Notification: Tool Poisoning Attacks. Invariant Labs. https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks

[6] MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers (2025). arXiv:2508.14925

[7] Wang et al. (2025). MCP Preference Manipulation Attack (MPMA). arXiv:2505.11154

[8] CVE-2025-66416. Model Context Protocol Python SDK does not enable DNS rebinding protection by default. CWE-1188. Fixed in mcp 1.23.0. GHSA-9h52-p55h-vw2f

[9] CVE-2025-66414. Model Context Protocol TypeScript SDK, equivalent defect. Fixed in 1.24.0.

[10] Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T. and Fritz, M. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. In *Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security*, 79–90.

[11] Debenedetti, E., Zhang, J., Balunović, M., Beurer-Kellner, L., Fischer, M. and Tramèr, F. (2024). AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents. arXiv:2406.13352

[12] Zhan, Q., Liang, Z., Ying, Z. and Kang, D. (2024). InjecAgent: Benchmarking indirect prompt injections in tool-integrated large language model agents. In *Findings of the ACL 2024*, 10471–10506.

[13] Patil, S.G., Mao, H., Yan, F., Ji, C.C.-J., Suresh, V., Stoica, I. and Gonzalez, J.E. (2025). The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models. In *Proceedings of the 42nd International Conference on Machine Learning*, PMLR 267, 48371–48392.

[14] Qin, Y. et al. (2023). ToolLLM: Facilitating large language models to master 16000+ real-world APIs. arXiv:2307.16789

[15] Guo, Z. et al. (2025). StableToolBench: Towards stable large-scale benchmarking on tool learning of large language models. *ACL*.

[16] Lu, J., Holleis, T., Zhang, Y., Aumayer, B., Nan, F., Bai, H., Ma, S., Ma, S., Li, M., Yin, G., Wang, Z. and Pang, R. (2025). ToolSandbox: A stateful, conversational, interactive evaluation benchmark for LLM tool use capabilities. In *Findings of the ACL: NAACL 2025*, 1160–1183.

[17] Yao, S., Shinn, N., Razavi, P. and Narasimhan, K. (2024). τ-bench: A benchmark for tool-agent-user interaction in real-world domains. arXiv:2406.12045

[18] OWASP MCP Top 10 (2025). MCP03:2025 — Tool Poisoning.

---

## Figures

**Figure 1** (`figures/fig1_decoy_by_condition.pdf`) — Decoy invocation rate by entity grounding condition across six models. Error bars are 95% confidence intervals bootstrapped over prompts. *Placement: §3.4.*

**Figure 2** (`figures/fig2_tool_routing.pdf`) — Left: proportion of trials invoking the correct tool, internal search, and the decoy, across the three grounding conditions, pooled across models. Right: `fetch_url` invocation by condition for each model individually. *Placement: §3.5.*

**Figure 3** (`figures/fig3_per_prompt.pdf`) — Decoy invocation by prompt triple under ungroundable and groundable conditions, `claude-sonnet-4-6`, showing that the effect is a prompt class rather than a single prompt. *Placement: §3.2 or §3.4.*

**Figure 4** (`figures/fig4_variant_inversion.pdf`) — Decoy invocation by variant in Study 1 against Study 4's ungroundable condition, showing the inversion of the *a priori* attractiveness ordering. *Placement: §5.*

*Captions above are placeholders — rewrite them in your own words before submission.*
