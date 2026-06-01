# Relay Heartbeat Model Routing Logic

**Status:** Draft routing logic
**Date:** 2026-06-01
**Owner harness:** Relay
**Consumes:** Heartbeat attention, Prime intent, Aegis risk/proof gates, Model Harness metadata

## Purpose

When the heartbeat sends Prime's attention to Relay, Relay answers:

- What model should Prime talk to?
- What vendor or route should Prime use?
- What are the risks of using that model or route?
- What evidence is needed before Relay can promote, demote, or block a route?

This document is the first model/vendor routing list for Meridian. It is not runtime code and does not grant Auto routing yet.

## Routing Principles

1. Prime owns the decision intention.
2. Relay owns model/vendor route selection.
3. Aegis owns proof and risk gates.
4. Bifrost displays the routing state; it does not choose.
5. Direct provider APIs are preferred for high-trust work.
6. Aggregator routes are useful but lower-trust unless separately proven.
7. DeepSeek direct is a candidate primary route, not automatically trusted.
8. Auto routing stays disabled until Relay logic, metadata, and proof are implemented.

## Top-To-Bottom Relay Flow

| Step | Relay Question | Logic |
|---|---|---|
| 1 | What is Prime trying to do? | Read Prime intent: plan, build, review, verify, summarize, research, route, voice, or explain. |
| 2 | What project and surface is active? | Read active project, right-panel mode, selected session/harness/settings surface, and user-visible gate. |
| 3 | What is the risk tier? | Ask Aegis/Risk: Tier 0-4, human gate required, proof required, account/public/destructive sensitivity. |
| 4 | What context shape is needed? | Choose focused packet, reuse session, summarize-and-reset, large context, or no model. |
| 5 | What role is needed? | Choose role: orchestrator, builder, reviewer, verifier, researcher, release operator, voice, or classifier. |
| 6 | What model class fits? | Match role/risk/context to model family: highest reasoning, coding, fast cheap, independent review, voice, or fallback. |
| 7 | What vendor route is safest? | Prefer direct provider API for Tier 3+. Use aggregator only when risk allows and fallback/coverage matters. |
| 8 | What does the budget allow? | Check cost posture, quota, token budget, context pressure, and prompt payload size. |
| 9 | Is there a trust block? | Block routes with unknown trust, failed/expired review, prompt-drag degradation, route mismatch, or missing metadata. |
| 10 | Is dual-lane needed? | For meaningful build/review or high-risk work, select independent lanes and compare outputs. |
| 11 | What should Prime see? | Return selected route, reason, risk notes, alternatives rejected, and proof requirements. |
| 12 | What should Bifrost show? | Show model/vendor, direct vs aggregator, trust state, cost pressure, payload size, and warning state. |

## Risk Tier Routing Defaults

| Tier | Default Route Logic | Notes |
|---|---|---|
| Tier 0 | No model call. Deterministic local logic only. | Formatting, local checks, known state. |
| Tier 1 | Fast/cheap single lane allowed. Aggregator allowed if metadata is clear. | Low-risk drafting, summarization, classification. |
| Tier 2 | One primary lane plus optional independent review lane. Aggregator allowed for review/exploration, not authority. | Meaningful but reversible work. |
| Tier 3 | Direct provider only. Stronger model, proof, and review required. | Code changes, complex planning, provider-sensitive decisions. |
| Tier 4 | Human gate required. Direct provider only for preparation/review, not autonomous execution. | Public, financial, destructive, account-risking, policy-sensitive. |

## Vendor And Model Set

### Anthropic Direct

Use Anthropic direct routes when high-quality reasoning, long-context work, agentic coding, and human-readable collaboration matter.

| Model | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `claude-opus-4-8` | Highest-complexity reasoning, long-horizon architecture, difficult code review, strategic planning. | Prefer for Tier 3-4 preparation, complex harness design, independent deep review, and long-context synthesis. | Premium cost and slower latency. Use when value justifies cost. Human gate still required at Tier 4. |
| `claude-sonnet-4-6` | General builder/reviewer lane, strong coding, balanced speed/intelligence. | Default Anthropic workhorse for build/review when direct Claude route is available. | Still requires proof for code changes; may not be cheapest. |
| `claude-haiku-4-5` | Fast classification, short summaries, extraction, lightweight review, heartbeat triage. | Use for low-risk fast lane or preprocessing where near-frontier intelligence is enough. | Not default for high-risk planning or complex code authority. |

### OpenAI Direct

Use OpenAI direct routes when Codex/coding strength, professional reasoning, structured outputs, voice/audio, or OpenAI tool compatibility matter.

| Model / Family | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `GPT-5.3-Codex` | Agentic coding, codebase changes, refactors, debugging, security/correctness repair. | Prefer for Codex-style build/review lanes and repository work when direct OpenAI route is available. | Requires code proof and Aegis review for meaningful changes. |
| `GPT-5.2` / `GPT-5.2 pro` | Professional reasoning, planning, synthesis, difficult non-code work. | Use for high-quality planning/reasoning lane or independent comparison against Claude. | Cost/latency pressure. Verify exact API id through model registry before enabling. |
| `GPT-5.3 Chat` / latest Chat family | Conversational planning, user-facing explanation, general reasoning. | Use for Prime-facing conversational lane when OpenAI direct is selected. | Do not treat Chat route as code-authority without proof. |
| `gpt-realtime-*` / `gpt-audio-*` families | Voice input/output, spoken interaction with Spark/Prime. | Candidate for first-class speech/voice once voice layer is wired. | Voice privacy, mic permissions, cost, and transcript handling need gates. |
| Embedding models | Atlas/Echo retrieval support. | Use for retrieval/indexing when Atlas/Echo needs embeddings. | Not a reasoning route; do not use as Prime response model. |

### DeepSeek Direct

Use DeepSeek direct when cost-efficient reasoning, Q-mode flatness, and direct API validation are desired. DeepSeek direct must remain visibly distinct from DeepSeek through OpenRouter.

| Model | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `deepseek-v4-pro` | High-reasoning direct DeepSeek lane, comparison lane, cost-aware reasoning, structured outputs. | Candidate for Tier 1-2 reasoning/review; promote only after validation. | Candidate trust until external validation. Do not grant autonomous code authority without proof. |
| `deepseek-v4-flash` | Fast/cheap direct DeepSeek lane, Q-mode checks, classification, bounded summaries. | Use for low-risk fast lane and heartbeat/Q-mode checks if prompt payload stays flat. | Watch prompt-drag. Candidate trust until validation. |
| `deepseek-chat` | Compatibility alias only. | Do not choose for new routes; maps to non-thinking `deepseek-v4-flash`. | Deprecated on 2026-07-24. |
| `deepseek-reasoner` | Compatibility alias only. | Do not choose for new routes; maps to thinking `deepseek-v4-flash`. | Deprecated on 2026-07-24. |

### OpenRouter Aggregator

Use OpenRouter as an aggregator route for coverage, fallback, model comparison, and low-risk exploration. It is not the same trust class as a direct provider API.

| Route / Model Set | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `openrouter/auto` | Low-risk exploratory routing when Relay wants a quick external choice. | Tier 1 only until Meridian can audit selected model, provider, cost, and data policy. | Auto chooses outside Meridian. Must show selected model and cost. Not for authoritative work. |
| Curated OpenRouter allowlist | Independent review, fallback when direct provider unavailable, access to provider/model variants. | Use only from an explicit allowlist generated from OpenRouter's model catalog. | Aggregator trust: provider fallback, data retention, model identity, and endpoint mismatch risk. |
| OpenRouter provider preferences | Force or deny providers, disable fallbacks, require supported parameters, deny data collection where available. | Relay must set provider preferences for any nontrivial OpenRouter route. | Defaults may route differently than expected; show actual provider/model used. |

## Initial Preferred Routing Logic

| Situation | Preferred Route | Backup / Independent Lane | Reason |
|---|---|---|---|
| Prime planning with high ambiguity | Anthropic `claude-opus-4-8` | OpenAI `GPT-5.2 pro` or `GPT-5.2` | Highest reasoning and synthesis. |
| Routine project planning | Anthropic `claude-sonnet-4-6` | OpenAI latest Chat/Reasoning route | Balanced intelligence/cost. |
| Repository coding/build lane | OpenAI `GPT-5.3-Codex` | Anthropic `claude-sonnet-4-6` | Codex route for code, Claude for independent reasoning/review. |
| Deep code review / architecture review | Anthropic `claude-opus-4-8` | OpenAI `GPT-5.3-Codex` | Different model families reduce shared blind spots. |
| Fast triage / heartbeat summary | Anthropic `claude-haiku-4-5` or DeepSeek `deepseek-v4-flash` | None or OpenRouter low-risk route | Fast, low-cost, bounded context. |
| Cost-sensitive reasoning | DeepSeek `deepseek-v4-pro` | Claude/OpenAI reviewer if action matters | Candidate direct route with proof before authority. |
| Voice/Spark interaction | OpenAI realtime/audio family | Later voice provider fallback | OpenAI has first-class audio/realtime model families. |
| Low-risk external fallback | Curated OpenRouter route | Direct provider when available | Aggregator useful for uptime/coverage, not authority. |

## Route Risk Register

| Risk | Applies To | Relay Behavior |
|---|---|---|
| Unknown exact model id | Any vendor | Query provider model registry before enabling route. |
| Aggregator route mismatch | OpenRouter | Show actual model/provider; cap authority; prefer direct for Tier 3+. |
| Cost surprise | Opus/pro/auto routes | Require cost posture, warn on premium route, expose Balance surface. |
| Prompt drag | All model calls, especially Q-mode | Require prompt payload snapshot and growth delta. |
| Data retention / provider policy | OpenRouter and some direct routes | Prefer direct/ZDR/deny-data-collection where available; surface policy state. |
| Missing CLI/API key/login | Local Codex/Claude and direct APIs | Show setup guidance; do not silently fall back to another route. |
| Unvalidated DeepSeek route | DeepSeek direct or aggregator | Candidate trust; external validation required before high-risk authority. |
| Model identity drift | OpenRouter / aliases | Prefer pinned model IDs or registry snapshots for high-risk work. |
| Voice privacy | Realtime/audio routes | Visible mic state, permission check, transcript policy. |

## Relay Output Shape

Every Relay decision should return a structured explanation:

```text
route_id
heartbeat_id
project
surface_mode
intent
risk_tier
role
selected_vendor
selected_model
route_kind: direct | aggregator | local_cli
reason
alternatives_rejected
cost_posture
trust_state
proof_required
human_gate_required
prompt_payload_budget
telemetry_required
```

## Promotion Rules

A model/vendor route can move from candidate to trusted only when:

1. Provider/model id is current and verified from the provider registry.
2. Endpoint route is known: direct or aggregator.
3. Allowed task types are explicit.
4. Risk-tier cap is explicit.
5. Prompt payload telemetry exists.
6. Cost posture is known or marked unknown.
7. Aegis has a proof policy for the route.
8. External review passes where required.

## Immediate Product Implications

- Relay harness panel should show logic items, not a chat prompt.
- Models surface should show these model/vendor route options and trust states.
- Balance surface should show cost, quota, payload, and trust pressure.
- Filter surface should control what context Relay includes.
- Auto mode remains disabled until this logic has runtime metadata and proof.

## Source Anchors

- Anthropic Claude model overview: https://platform.claude.com/docs/en/about-claude/models/overview
- OpenAI model list: https://developers.openai.com/api/docs/models/all
- DeepSeek API quick start and model ids: https://api-docs.deepseek.com/
- OpenRouter model catalog API: https://openrouter.ai/docs/api/api-reference/models/get-models
- OpenRouter Auto Router: https://openrouter.ai/docs/guides/routing/routers/auto-router
- OpenRouter provider routing: https://openrouter.ai/docs/features/provider-routing
