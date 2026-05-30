# Relay Prompt Metrics Integration Brief

**Status:** Planning only — no runtime changes yet  
**Scope:** How Relay dispatch should measure and use Prompt Metrics  
**Related:** `meridian_core/prompt_metrics.py`, `meridian_core/relay.py`, `meridian_core/prompt_budget.py`

---

## Problem Statement

Relay dispatch currently executes without observability into prompt performance:
- No visibility into prompt construction overhead
- No measurement of time-to-first-token (TTFT) or total response time
- No comparison against vendor baseline to detect Relay-induced overhead
- No feedback loop to Prime about dispatch performance
- No input to cost decisions or prompt budget tuning

**Principle:** *Relay Must Not Become Prompt Drag* — measure overhead, make it visible, act on it.

---

## Dispatch Lifecycle with Metrics

### Current Flow (Today)
```
Risk Assessment
    ↓
RelayRoute created (mode, lanes, context_strategy, cost_posture, council_plan)
    ↓
Worker session spawned with prompt
    ↓
Model executes
    ↓
Response returned
    ↓
[No metrics captured]
```

### Future Flow (With Metrics)
```
Risk Assessment
    ↓
RelayRoute created
    ↓
PromptBudgetPlan fetched (max tokens, allowed sources) ← BUDGET CONSTRAINT
    ↓
Prompt construction begins
    ├─ construction_time_start = now()
    └─ [BUILD PROMPT WITH BUDGET CEILING]
    ↓
construction_time_ms = now() - construction_time_start
prompt_tokens = len(tokenize(prompt))
    ↓
Worker session spawned
    ├─ ttft_start = now()
    └─ [SEND PROMPT TO MODEL]
    ↓
Model's first token arrives
    ├─ time_to_first_token_ms = now() - ttft_start
    └─ [CONTINUE STREAMING RESPONSE]
    ↓
Model completes
    ├─ total_response_time_ms = now() - session_start
    ├─ response_tokens = len(tokenize(response))
    └─ [CAPTURE SAMPLE]
    ↓
PromptMetricSample created
    ├─ sample_id = unique_id(lane, tier, timestamp)
    ├─ prompt_tokens = final count
    ├─ construction_time_ms = measured
    ├─ total_response_time_ms = measured
    ├─ time_to_first_token_ms = measured
    └─ native_baseline_ms = optional (from prior vendor baseline run)
    ↓
POST-DISPATCH: Summarize samples
    ├─ summarize_prompt_metrics(samples)
    └─ PromptMetricSummary with status (HEALTHY, WATCH, DEGRADED)
    ↓
Status-based Prime feedback
    ├─ HEALTHY → continue (acceptable overhead)
    ├─ WATCH → log, monitor (borderline overhead)
    └─ DEGRADED → escalate to Prime for decision
```

---

## Measurement Strategy

### 1. Prompt Construction Time

**What to measure:** Time spent building the prompt (gathering context, constructing prompt object, final serialization).

**When to start:** Just before context gathering begins.  
**When to stop:** After serialization, before sending to model.

**Why it matters:**
- High construction time = too much logic in Relay (should be in Prime)
- Indicator of context bloat (too many sources being merged)
- Target: <100ms for Tier 0/1, <300ms for Tier 3/4

```python
# Pseudocode
start_ms = now_ms()
context = gather_context(budget_plan.allowed_sources)
prompt = build_prompt(context)
serialized = serialize_prompt(prompt)
construction_time_ms = now_ms() - start_ms
```

### 2. Prompt Token Count

**What to measure:** Final token count of the prompt sent to the model.

**When to capture:** After serialization, before dispatch.

**Why it matters:**
- Verify prompt stays within `PromptBudgetPlan.max_context_tokens`
- Track context growth over session age (should be flat, not accumulating)
- Feed to cost calculations

```python
prompt_tokens = len(tokenizer.encode(serialized_prompt))
assert prompt_tokens <= budget_plan.max_context_tokens
```

**Integration with Budget:**
- If `prompt_tokens > budget_plan.max_context_tokens`, escalate to Prime (budget violation)
- Log as DEGRADED automatically if exceeded

### 3. Time-to-First-Token (TTFT)

**What to measure:** Wall-clock time from prompt dispatch to first token arrival from model.

**When to start:** Just after sending prompt to model API.  
**When to stop:** When first token received from model.

**Why it matters:**
- Measures model responsiveness, not Relay overhead
- High TTFT = model is slow or overloaded, not Relay's fault
- Baseline: vendor model alone (no Relay harness)

```python
ttft_start_ms = now_ms()
first_token = await model.send_prompt_and_wait_first_token(prompt)
time_to_first_token_ms = now_ms() - ttft_start_ms
```

**Not included in Relay overhead calculation** (TTFT is external).

### 4. Total Response Time

**What to measure:** Wall-clock time from prompt dispatch to complete response received.

**When to start:** Just after sending prompt.  
**When to stop:** After final token received and parsed.

**Why it matters:**
- Includes model execution + streaming + parsing overhead
- Can be compared to vendor baseline to calculate Relay overhead
- Captures end-user latency impact

```python
response_start_ms = now_ms()
response = await model.send_prompt_and_get_response(prompt)
total_response_time_ms = now_ms() - response_start_ms
```

### 5. Native/Vendor Baseline

**What is it:** Reference measurement from sending the same task directly to the vendor model without Relay harness.

**When to capture:**
- Optionally, as part of offline tuning (not in every dispatch)
- Could be cached baseline per task/tier
- May come from prior empirical runs

**Why it matters:**
- Calculates true Relay overhead: `delta_ms = total_response_time_ms - native_baseline_ms`
- Overhead classification depends on delta (50ms/200ms thresholds)
- Without baseline: fallback to construction_time classification

```python
sample = PromptMetricSample(
    sample_id=f"{lane_id}_{tier}_{timestamp}",
    prompt_tokens=final_token_count,
    construction_time_ms=construction_time,
    total_response_time_ms=response_time,
    time_to_first_token_ms=ttft_or_none,
    native_baseline_ms=baseline_or_none,  # Optional
)
```

---

## Metrics ↔ Budget Interaction

### Budget Bounds Prompt Construction

`PromptBudgetPlan` defines:
- `max_context_tokens` (hard ceiling)
- `allowed_sources` (what can be included)

During construction:
- Only gather context from `allowed_sources`
- Stop gathering if approaching `max_context_tokens`
- Final prompt must be ≤ `max_context_tokens`

### Metrics Measure Budget Adherence

After dispatch, check:
```python
if sample.prompt_tokens > budget.max_context_tokens:
    status = DEGRADED  # Budget violation
    log_error(f"Prompt {sample.prompt_tokens} exceeded budget {budget.max_context_tokens}")
    escalate_to_prime()
```

### Feedback Loop

```
Budget sets token ceiling
    ↓
Relay constructs prompt within ceiling
    ↓
Metrics measure actual tokens + performance
    ↓
Status classification (HEALTHY/WATCH/DEGRADED)
    ↓
Prime reads status, adjusts future budgets or dispatch strategy
```

---

## Status Classification in Prime Decisions

### PromptPerformanceStatus Enum

- **HEALTHY** — Overhead within bounds, no action needed
- **WATCH** — Overhead elevated, monitor closely, may need tuning
- **DEGRADED** — Overhead unacceptable, requires Prime intervention

### Thresholds

| Metric | WATCH | DEGRADED |
|--------|-------|----------|
| Delta vs baseline | ≥ 50ms | ≥ 200ms |
| Construction time | ≥ 100ms | ≥ 300ms |

**Rule:** Delta classification takes precedence. If baseline available, delta determines status (not construction time alone).

### Prime Integration Points

#### 1. HEALTHY Status
Prime needs no action. Continue dispatch as planned.
- Log for trend tracking
- Feed to dashboards
- No escalation

#### 2. WATCH Status
Prime should monitor but can continue.
- Log with WARN level
- Track frequency (how often WATCH is triggered)
- If WATCH persists, escalate to Scott for investigation
- Consider adjusting budget or context strategy for future

Example decision:
```
If status == WATCH and watch_count_in_session > 3:
    Escalate to Scott: "Relay overhead trending high, investigate context bloat"
```

#### 3. DEGRADED Status
Prime must intervene.
- Log with ERROR level
- Escalate to Scott immediately
- Consider reverting to slower but leaner strategy
- Pause autonomous dispatch until issue diagnosed

Example decision:
```
If status == DEGRADED:
    Escalate to Scott: f"Relay overhead critical ({delta_ms}ms), manual review required"
    Pause further autonomous dispatch in this tier
    Suggest fallback: use vendor model directly or reduce context
```

---

## Review Console vs Internal Metrics

### What Goes in Review Console

**User-visible findings that require judgment:**
- Dispatch status transitions (HEALTHY → WATCH → DEGRADED)
- Overhead spikes with explanation
- Budget violations (prompt exceeded max tokens)
- Recommendation: "Reduce context sources" or "Use simpler task"

**Item type:** Make a new `ReviewConsoleItemType.RELAY_OVERHEAD` or similar.

Example Review Console item:
```
Type: RELAY_OVERHEAD
Status: DEGRADED
Severity: HIGH
Summary: "Relay dispatch 2.3x slower than vendor baseline (delta: 240ms vs 100ms target)"
Details:
  - Construction time: 150ms (acceptable)
  - Response time: 340ms vs 100ms baseline
  - Prompt tokens: 4800 / 5000 budget (96% used)
  - Suggested action: reduce context sources or simplify prompt

Action options:
  [ ] Accept overhead, continue
  [ ] Retry with simpler context
  [ ] Fall back to vendor model
```

### What Stays Internal

**Metrics kept for tuning/analysis but not reviewed:**
- Per-sample raw data (ttft, tokens, construction time)
- Trend statistics (p50, p95, p99)
- Correlation analysis (does construction time track with context sources?)
- Cost impact calculations (tokens × price per million)

These feed dashboards, not Review Console. Prime doesn't need to judge every data point.

---

## What Must NOT Appear in Worker Prompts

**Metrics are captured AFTER dispatch, never injected DURING.**

Blocked:
- Prior dispatch metrics (don't tell worker "last dispatch took 250ms")
- Performance overhead stats
- Budget consumption history
- Construction time measurements
- Status classifications

Why:
- Adds tokens to prompt (costs money)
- Confuses worker (metrics are Relay concern, not worker's)
- Metrics belong in session logs/dashboards, not prompts
- Violates *Relay Must Not Become Prompt Drag* principle

**One exception:** Prime may include metrics in Review Console explanation, which is separate from worker prompts.

---

## Required Tests Before Runtime Integration

### Unit Tests (Existing, no changes needed)
- `test_prompt_metrics.py` (41 tests, all passing)
  - Sample creation, immutability
  - Summary aggregation
  - Status classification (delta/construction precedence)
  - Edge cases (missing TTFT, missing baseline)

### Integration Tests (New, to be added when Relay integration starts)

#### 1. Metrics Sample Creation in Dispatch
```python
def test_relay_captures_prompt_metric_sample():
    """Relay dispatch creates PromptMetricSample with all fields."""
    route = route_from_tier(2)
    # [Mock dispatch with instrumentation points]
    sample = captured_sample_from_dispatch(route)
    
    assert sample.prompt_tokens > 0
    assert sample.construction_time_ms > 0
    assert sample.total_response_time_ms > sample.construction_time_ms
    # TTFT and baseline are optional
```

#### 2. Budget Respected in Sample
```python
def test_dispatch_sample_respects_budget():
    """Prompt tokens never exceed PromptBudgetPlan max."""
    route = route_from_tier(3)
    budget = route.prompt_budget
    sample = captured_sample_from_dispatch(route)
    
    assert sample.prompt_tokens <= budget.max_context_tokens
```

#### 3. Status Classification Applied
```python
def test_metric_summary_status_from_dispatch():
    """Post-dispatch summary computes status correctly."""
    samples = [
        PromptMetricSample(
            sample_id="test_1",
            prompt_tokens=2000,
            construction_time_ms=50,
            total_response_time_ms=150,
            time_to_first_token_ms=50,
            native_baseline_ms=100,  # 50ms delta = WATCH
        ),
    ]
    summary = summarize_prompt_metrics(samples)
    assert summary.status == PromptPerformanceStatus.WATCH
```

#### 4. Status Affects Prime Decision
```python
def test_prime_decision_on_degraded_status():
    """Prime escalates when dispatch status is DEGRADED."""
    # Simulate high-overhead dispatch
    summary.status = PromptPerformanceStatus.DEGRADED
    decision = prime_decide_on_dispatch_status(summary, route)
    
    assert decision.escalate_to_scott
    assert decision.pause_autonomous_dispatch
```

#### 5. No Metrics in Worker Prompt
```python
def test_worker_prompt_excludes_metrics():
    """Worker prompt never includes prior dispatch metrics."""
    prior_sample = PromptMetricSample(...)
    prior_summary = summarize_prompt_metrics([prior_sample])
    
    worker_prompt = build_worker_prompt(route, budget, prior_summary)
    
    # Metrics nowhere in the prompt
    assert "construction_time" not in worker_prompt
    assert "response_time" not in worker_prompt
    assert "WATCH" not in worker_prompt  # status not mentioned
```

#### 6. No Regression on Existing Relay Behavior
```python
def test_relay_routing_unchanged_with_metrics():
    """Relay routing unaffected by metric capture."""
    for tier in range(5):
        route_no_metrics = route_from_tier(tier)
        # Metrics are post-dispatch, don't affect routing
        assert route_no_metrics.mode is not None
        assert route_no_metrics.council_plan is not None
        assert route_no_metrics.prompt_budget is not None
```

---

## Integration Checklist (Future PR)

### Code Changes
- [ ] Relay dispatch adds instrumentation points (time measurements)
- [ ] PromptMetricSample created post-dispatch with all fields
- [ ] Baseline comparison optional (may be None)
- [ ] Status classification applied to summary
- [ ] Prime reads status, applies decision logic
- [ ] Review Console optionally receives RELAY_OVERHEAD items

### Tests
- [ ] 6 integration tests above all pass
- [ ] Existing Relay, Budget, Intention tests still pass
- [ ] No metrics injected into worker prompts
- [ ] Baseline comparison works when available

### Docs
- [ ] Update `context.md` with metrics section
- [ ] Link this brief from README or MISSION.md
- [ ] Add metrics to PromptBudgetPlan interaction diagrams

### Future Work (Not in integration PR)
- [ ] Establish vendor baseline for each tier/task pattern
- [ ] Build metrics dashboards (Grafana or similar)
- [ ] Set up alerts for DEGRADED status transitions
- [ ] Tuning loop: adjust budgets based on real metrics
- [ ] Cost tracking: tokens × price per million

---

## What Is NOT in This Brief

Explicitly out of scope:

- **Relay.py runtime changes** — dispatch instrumentation happens here (future)
- **Worker harness changes** — captures samples, calls summarize_prompt_metrics()
- **Metrics storage** — where summaries are written (time-series DB, TBD)
- **Dashboards** — visualization of metrics (future, Grafana)
- **Alerts** — automation on DEGRADED status (future)
- **Baseline tuning** — empirical establishment of vendor baselines (future)

Pure planning. Ready to implement when Relay instrumentation is designed.

---

## Summary

**Metrics measure, Prime decides, Relay improves.**

1. **Measure:** Capture construction time, token count, TTFT, response time, delta vs baseline
2. **Classify:** HEALTHY/WATCH/DEGRADED based on thresholds
3. **Decide:** Prime acts on status (escalate on DEGRADED, monitor on WATCH)
4. **Improve:** Feedback loop to budget tuning and context strategy

**Clear boundaries:**
- Budget: Sets ceiling before dispatch
- Metrics: Measures performance after dispatch
- Prime: Uses both to decide next moves

**No prompt bloat:** Metrics live outside prompts, in session logs and dashboards.

**Next steps after integration:**
1. Establish vendor baselines per tier
2. Build monitoring dashboards
3. Set alerts for performance regressions
4. Tune budgets and context strategies based on real data
