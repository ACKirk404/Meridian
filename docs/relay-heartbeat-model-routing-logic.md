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
5. Existing user account/session routes are preferred before paid/direct API routes when they can satisfy the job safely.
6. Direct provider APIs are preferred for high-trust work when account/session routes are unavailable, unsuitable, or insufficiently controllable.
7. Aggregator routes are useful but lower-trust unless separately proven.
8. DeepSeek direct is a candidate primary route, not automatically trusted.
9. Auto routing stays disabled until Relay logic, metadata, and proof are implemented.

## Top-To-Bottom Relay Flow

| Step | Relay Question | Logic |
|---|---|---|
| 1 | What is Prime trying to do? | Read Prime intent: plan, build, review, verify, summarize, research, route, voice, or explain. |
| 2 | What project and surface is active? | Read active project, right-panel mode, selected session/harness/settings surface, and user-visible gate. |
| 3 | What is the risk tier? | Ask Aegis/Risk: Tier 0-4, human gate required, proof required, account/public/destructive sensitivity. |
| 4 | What context shape is needed? | Choose focused packet, reuse session, summarize-and-reset, large context, or no model. |
| 5 | What role is needed? | Choose role: orchestrator, builder, reviewer, verifier, researcher, release operator, voice, or classifier. |
| 6 | Should this reuse a session or start a new one? | Reuse only when context is healthy and the reasoning mode still matches. Start new when context is filling, polluted, stale, or the work type shifts. |
| 7 | What model class fits? | Match role/risk/context to model family: highest reasoning, coding, fast cheap, independent review, voice, or fallback. |
| 8 | What access route should be tried first? | Prefer existing account/session routes, then direct APIs, then aggregator routes if risk allows. |
| 9 | What vendor route is safest? | Prefer direct provider API for Tier 3+ when account/session route cannot satisfy control/proof needs. Use aggregator only when risk allows and fallback/coverage matters. |
| 10 | What does the budget allow? | Check account quota, API cost posture, token budget, context pressure, and prompt payload size. |
| 11 | Is there a trust block? | Block routes with unknown trust, failed/expired review, prompt-drag degradation, route mismatch, or missing metadata. |
| 12 | Is dual-lane needed? | Tier 3 requires independent dual-model lanes; Tier 2 uses dual lane when meaningful work or review warrants it. |
| 13 | What should Prime see? | Return selected route, reason, risk notes, alternatives rejected, and proof requirements. |
| 14 | What should Bifrost show? | Show model/vendor, account/API/aggregator route, trust state, cost pressure, payload size, and warning state. |

## Risk Tier Routing Defaults

| Tier | Default Route Logic | Notes |
|---|---|---|
| Tier 0 | No model call. Deterministic local logic only. | Formatting, local checks, known state. |
| Tier 1 | Fast/cheap single lane allowed. Account/session route first; aggregator allowed if metadata is clear. | Low-risk drafting, summarization, classification. |
| Tier 2 | One primary lane plus independent review lane when meaningful work warrants it. Account/session route first; aggregator allowed for review/exploration, not authority. | Meaningful but reversible work. |
| Tier 3 | Independent dual-model lanes required. Prefer account/session routes first, then direct APIs if proof/control requires them. Aggregator cannot be authoritative. | Code changes, complex planning, provider-sensitive decisions. |
| Tier 4 | Human gate required plus independent model review for preparation. Prefer account/session routes where controllable, direct provider APIs for audit/proof; no autonomous execution. | Public, financial, destructive, account-risking, policy-sensitive. |

## Access Route Precedence

Relay should not jump to raw APIs when an existing user account or session route can do the job safely. The preferred route order is:

| Priority | Route Class | When To Use | When To Skip |
|---|---|---|---|
| 1 | Existing user account/session | The user is already logged in, the vendor session has the right tools/context, and Relay can capture enough metadata/proof. | Skip if session context is bloated, stale, polluted, wrong role, wrong project, missing proof metadata, or cannot be steered safely. |
| 2 | Local CLI-backed route | Codex/Claude CLI or similar account-backed local route can execute with known working directory and recoverable transcript. | Skip if CLI missing, unauthenticated, wrong cwd, wrong session identity, or cannot satisfy risk/proof gates. |
| 3 | Direct provider API | Need pinned model id, clean prompt packet, auditability, direct endpoint, structured telemetry, or stronger trust for Tier 3+. | Skip if account/session route is safer and sufficiently observable, or if API credentials/quota are unavailable. |
| 4 | Aggregator API | Need fallback, model availability, low-risk comparison, or exploratory routing. | Skip for authoritative Tier 3+, high-risk work, unknown data policy, model identity uncertainty, or unbounded cost. |

The route chosen must be visible as `route_class: account_session | local_cli | direct_api | aggregator_api`.

## Session Lifecycle Routing

Relay must decide whether to reuse a session, start a new session, summarize/reset, or transfer work. This is part of routing, not cleanup.

| Signal | Relay Decision | Reason |
|---|---|---|
| Context window filling or prompt payload over budget | Summarize important state and start a new session. | Prevent prompt drag and context collapse. |
| Session context polluted by unrelated work | Start a new focused session. | Avoid contaminating reasoning and model output. |
| Reasoning type shifts, such as planning to coding or coding to review | Start or switch to a role-appropriate session/model. | Different work needs different tools, instructions, and model strengths. |
| Project changes | Use project-specific orchestrator/session context; do not reuse cross-project context silently. | Prevent project bleed. |
| User moves from User Session mode to Settings mode | Preserve user session; use Settings configuration surface, not the old prompt context. | Keep configuration separate from project work. |
| User moves to Harness mode | Preserve previous user session; use selected harness logic list. | Harness logic updates are not general project chat. |
| Long-running session with healthy context and same role | Reuse session. | Preserve continuity when it is still useful. |
| Session hits tool/auth/cwd mismatch | Start corrected session or block with setup warning. | Avoid sending work to a broken or wrong environment. |
| Review finds defect in build output | Start repair or reviewer-specific lane, not necessarily the original builder session. | Use the right role for the next action. |
| Tier 3+ decision requires independence | Start independent second lane with different vendor/model family. | Reduce shared blind spots. |

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

Use DeepSeek direct when cost-efficient reasoning, Q-mode flatness, and direct API validation are desired. DeepSeek direct must remain visibly distinct from DeepSeek through OpenRouter. The dispatch ID for direct API calls is `deepseek-chat`; `v4-pro` and `v4-flash` are marketing/capability variants expressed as metadata, not dispatch keys.

| Model (Dispatch ID) | Primary Uses | Relay Logic | Risks / Gates |
|---|---|---|---|
| `deepseek-chat` | Direct DeepSeek API dispatch ID; supports both standard and extended-thinking modes. Variants: `v4-pro` (high-reasoning) and `v4-flash` (fast/cheap). | Use for cost-efficient reasoning, comparison lanes, and Q-mode checks. Promote to Tier 2+ only after external validation; candidate trust until proven. | Candidate trust. Do not grant autonomous code authority without proof. Watch prompt-drag on extended-thinking. |
| `deepseek-reasoner` | Extended-thinking variant for reasoning-intensive work. | Candidate for Tier 1-2 reasoning/review when extended thinking is explicitly required. | Candidate trust until validation. Cost and latency higher than standard. |

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
| Fast triage / heartbeat summary | Anthropic `claude-haiku-4-5` or DeepSeek `deepseek-chat` (v4-flash variant) | None or OpenRouter low-risk route | Fast, low-cost, bounded context. |
| Cost-sensitive reasoning | DeepSeek `deepseek-chat` (v4-pro variant) | Claude/OpenAI reviewer if action matters | Candidate direct route with proof before authority. |
| Voice/Spark interaction | OpenAI realtime/audio family | Later voice provider fallback | OpenAI has first-class audio/realtime model families. |
| Low-risk external fallback | Curated OpenRouter route | Direct provider when available | Aggregator useful for uptime/coverage, not authority. |

## Account-First Fallback Decision Tree

Before using a paid API or aggregator route, Relay evaluates the account/session option through this decision tree:

**Step 1: Is an account/session route available and authenticated?**
- Yes → Proceed to Step 2
- No → Skip to API/aggregator fallback options

**Step 2: Does the session have the right project scope, role, and tools?**
- Yes → Proceed to Step 3
- No → Start project-specific or role-matched session (wrong scope must be corrected, not bypassed)

**Step 3: Is context health clean and under budget?**
- Yes → Proceed to Step 4
- No → Summarize/reset and reuse (if same project) or start new session; do not use bloated session

**Step 4: Can Relay steer the session and capture proof?**
- Yes → Use account/session route
- No → Direct API if proof/audit is required; aggregator if fallback is acceptable

**If account/session is rejected at any step:**

*Special case — wrong project, wrong role, or wrong tools (Step 2 rejection):*
- Do NOT proceed to direct API or aggregator; these are scope/control violations that require correction
- Start project-specific or role-matched session, or block if no corrected session is available

*All other rejections (Steps 1, 3, 4):*
1. Relay explicitly records the rejection reason (not silent fallback)
2. Relay proceeds to direct API if tier/trust allows
3. Relay proceeds to aggregator only if tier and fallback policy allow
4. Relay blocks if no route passes validation

This ordering preserves user session state, avoids API cost when unnecessary, and maintains continuity.

## Explicit API Fallback Conditions

Relay may fall through to API routes only when account/session is unavailable, unsuitable, or forbidden. Fallback is never silent.

| Condition | Tier 1-2 Allowed | Tier 3+ Allowed | Fallback Action | Show to Prime |
|---|---|---|---|---|
| Account session missing/expired | ✓ (if proof ok) | ✓ (start/re-auth session, or direct API if proof/audit explicit) | Start/re-auth session or direct API | "Session unavailable, attempting re-auth or direct API" |
| Session context full | ✓ (summarize first) | ✓ (with new session) | Start new session or API | "Context full, summarizing or using API" |
| Session wrong project | ✗ | ✗ | Start project-specific session | "Wrong project session, starting fresh" |
| Session wrong role | ✓ (if low-tier) | ✗ | Start role-matched session | "Role mismatch, starting new session" |
| Session stale/polluted | ✓ (if low-tier) | ✗ | Start fresh session | "Context stale, starting clean" |
| Session auth broken/wrong cwd | ✗ | ✗ | Block with setup error | "Session setup error, cannot proceed" |
| No credential/API key present | ✗ | ✗ | Block with setup guidance | "API credentials missing, cannot proceed" |
| API quota exhausted | ✗ (try aggregator) | ✗ (block) | Aggregator if risk allows; else block | "API quota exhausted, no fallback available" |
| Account cost exhausted | ✗ | ✗ | Block or escalate to user | "Account balance exhausted, awaiting approval" |
| API rate limited | ✓ (retry with backoff) | ✓ (retry with backoff) | Retry; escalate if repeated | "Rate limited, retrying after delay" |
| Aggregator default choice broken | ✗ | ✗ | Use explicit model allowlist; block if none match | "OpenRouter default unavailable, no safe fallback" |

**Key principle:** Fallback is named, shown to Prime, and subject to tier/cost/trust validation. Silent fallback is forbidden.

## Vendor-Specific Fallback Roles

Each vendor has distinct fallback authority and blocking conditions:

### Anthropic Direct Fallback Role
- **Fallback from:** Account/session, expensive routes
- **Fallback to:** Claude Sonnet if Opus exhausted or premium-cost blocked by budget
- **Fallback to:** Claude Haiku for fast triage only if upstream route unavailable
- **Block if:** Exact model id unknown for Tier 2+; cannot capture structured proof
- **Promotion:** Sonnet → Opus requires cost approval; Haiku → Sonnet requires context proof

### OpenAI Direct Fallback Role
- **Fallback from:** Account/session, non-coding routes needing reasoning
- **Fallback to:** GPT-5.2 if Codex unavailable; Chat if reasoning-only needed
- **Fallback to:** Aggregator only for exploratory/review work, never authority
- **Block if:** Exact model id unknown; API credentials missing; structured outputs required but unavailable
- **Promotion:** Chat → Reasoning/Codex requires code proof and Aegis gate clearance

### DeepSeek Direct Fallback Role
- **Fallback from:** Cost-sensitive routes; OpenAI/Anthropic unavailable
- **Fallback to:** Flash if Pro exhausted; block if no quota remains
- **Block if:** External review validation not passed; candidate trust not yet established
- **Promotion:** Flash → Pro requires proof of quality; Pro → authority requires external validation pass
- **No fallback:** DeepSeek cannot be fallback to other vendors; other vendors can use DeepSeek as fallback if candidate trust holds

### OpenRouter Aggregator Fallback Role
- **Fallback from:** Direct API unavailable; uptime/coverage needed
- **Fallback to:** Curated allowlist only; no open `openrouter/auto`
- **Block if:** Tier 3+ requires authority; tier 2+ requires proof/model identity; unknown provider would be selected
- **Block if:** Data retention policy unknown; cost unbounded
- **Limitation:** Cannot be authoritative for code, complex planning, or review work

## Dual-Model and External Review Requirements

Tier 3+ work requires architectural independence to reduce shared blind spots and vendor bias.

### When Dual-Lane Is Mandatory
- **Tier 3:** All code changes, complex planning, architecture review, provider-sensitive decisions
  - Lane 1: Preferred vendor (Claude, OpenAI, or DeepSeek depending on work type)
  - Lane 2: Independent vendor (different model family)
  - Both lanes must use account/session or direct API; aggregator cannot be either lane
  - Both lanes produce proof; decision is made when lanes agree or explicit tie-break applies

- **Tier 4:** Human gate required; dual-lane for preparation/review only, no autonomous execution
  - Lane 1: Highest-reasoning (Opus, GPT-5.2 pro, or domain-expert route)
  - Lane 2: Independent domain expert or human reviewer
  - Both lanes produce evidence; human gate makes final decision

### When Dual-Lane Is Optional (Tier 2)
- Single lane is acceptable if:
  - Work is reversible (documentation, exploration, low-risk changes)
  - Proof requirement is clear and achievable in one lane
  - Budget and latency allow single lane
- Dual lane is recommended if:
  - Work is meaningful enough to warrant independent confirmation
  - Cost allows parallel lanes
  - Risk register requires external validation (e.g., DeepSeek candidate trust)

### When External Codex Review Is Required
Relay must trigger external Codex review (separate session, different model family) when:
- Any Tier 3+ code route is first used and has no prior validation proof
- A provider moves from candidate to production trust (external validation pass)
- A route's proof type changes (e.g., code review vs. code authority)
- Tier 4 work requires independent expert confirmation before execution
- A model's output quality noticeably degrades (prompt-drag, reasoning failure)

External review is asynchronous and blocks execution/promotion until review completes.

## Session Lifecycle Decisions

Detailed decision points for session reuse, summarization, reset, transfer, and archival.

### Reuse Current Session
**Conditions:**
- Same project scope as original session
- Same reasoning mode/role (planning, building, reviewing)
- Context health: under 70% of capacity, clean
- No cross-session or cross-project contamination
- User expects continuity
- No tool/auth/cwd mismatch

**Action:** Reuse with proof that context remains sound

### Start New Session
**Triggers:**
- Project changed (→ project-scoped session)
- Reasoning mode shifted (planning → coding → review; use role-appropriate session)
- Context reaching 70%+ capacity (→ summarize current, start new)
- Context contaminated by unrelated work (→ clean new session)
- Session stale (>30 min idle on live work, >24h idle on background)
- Tool/auth/cwd state is broken or wrong (→ new session with correct setup)
- Tier 3+ requires independence (→ new session, different vendor/model)
- User explicitly requests context reset

**Action:** Summarize critical state if useful, then start new clean session

### Summarize and Reset
**When to summarize:**
- Context is full but continuity is valuable
- Need to preserve decisions/architecture without carrying full transcript
- Transitioning from one long work session to the next phase

**Summary includes:**
- Current project and work type
- Architecture/design decisions made
- Key proofs or test results
- Explicit list of what to NOT re-include (unrelated explorations, dead-end attempts)

**New session starts with:**
- Summary as context
- Fresh role-appropriate instructions
- Clean working directory
- New proof/test expectations

### Transfer Between Sessions
**When:**
- Work started in wrong session (wrong project, wrong role, wrong vendor)
- Continuing work requires different model family
- Tier 3 needs to move from single lane to dual lanes

**Transfer includes:**
- Complete prompt/context from source session
- Proof/test status and decisions made
- Explicit note that this is continuation, not restart

### Archive Session
**When:**
- Session completes successfully (work is done, approved, merged, released)
- Session is superseded (replaced by new session for same work)
- Session is abandoned (user chose different approach)

**Archive captures:**
- Final state and proof/test results
- Key decisions and rationale
- Telemetry: tokens used, latency, cost, model, trust state

## Cost, Token, and Account Exhaustion Routing Changes

Relay adjusts route decisions in real time based on exhaustion pressure.

### Cost Pressure Routing

| Pressure Level | Relay Behavior | Route Adjustment | Show to Prime |
|---|---|---|---|
| Normal (0-70%) | Standard routing logic applies | Account/session first, normal vendor preference | Balance available |
| Caution (70-90%) | Warn before premium routes | Prefer Haiku, DeepSeek Flash, or OpenRouter curated list | "Cost pressure: 70%" |
| High (90-100%) | Block premium routes | Force Haiku, DeepSeek Flash, or ask for approval | "High cost pressure: requesting approval" |
| Exhausted (100%+) | Block all routes except free tiers | Aggregator only if risk allows; else block | "Cost exhausted, no fallback available" |

### Token Budget Routing

| Pressure Level | Relay Behavior | Route Adjustment | Show to Prime |
|---|---|---|---|
| Normal (<70% context window) | Standard routing | Use longest-context models if needed | Tokens available |
| Filling (70-85%) | Warn before context-heavy work | Prefer fast models (Haiku, Flash) or summarize | "Context 70%: recommend summarize" |
| Near full (85-95%) | Block multi-turn work | Only single-shot responses allowed | "Context 85%: must reset" |
| Full (95%+) | Block all routes | Force session reset | "Context full, session must reset" |

### Account Exhaustion Routing

| Condition | Relay Behavior | Route Adjustment | Show to Prime |
|---|---|---|---|
| Account authenticated, healthy | Standard routing | Account/session first | Account ready |
| Account quota warning (80%+) | Warn, but proceed | May skip aggregator if uncertain | "Account quota: 80%" |
| Account quota exhausted | Block account routes | Force direct API or aggregator | "Account quota exhausted" |
| Account payment failed | Block account routes immediately | Direct API only if available; else block | "Account billing failed, using API" |
| MFA/auth lapsed | Block account routes; require re-auth | Wait for user to refresh login | "Account re-auth required" |

### Rate Limit Handling

| Scenario | Relay Behavior | Route Adjustment | Show to Prime |
|---|---|---|---|
| Rate limit encountered (429) | Retry with exponential backoff | Delay 1s, 4s, 16s, escalate | "Rate limited, retrying" |
| Persistent rate limit | If account available, switch to session | Reduce API call frequency | "Rate limit, using session instead" |
| All vendors rate limited | Block; do not cascade | Wait and show blocker | "All routes rate limited, awaiting reset" |

## Critical Blockers: What Must Block Rather Than Guess

Relay must **block** (not fallback, not guess, not proceed silently) when:

| Blocker | Why Block | Recovery Path |
|---|---|---|
| **Risk tier unknown** | Cannot choose correct route without risk level | Ask Aegis for tier; block until answered |
| **Route class unknown** | No route type satisfies the risk tier | Audit available routes; block until explicit |
| **Exact model ID unknown (Tier 2+)** | Model identity cannot drift or alias silently | Query provider registry; pin exact ID before route |
| **Aegis gate unknown or missing** | Cannot validate proof/security policy | Ask Aegis for gate; block until gate answer received |
| **Proof requirement unknown** | Output cannot be validated or trusted | Define proof type explicitly before routing |
| **Context health unknown (session reuse)** | Cannot assess prompt-drag risk | Check context size, contamination, staleness; block until healthy |
| **Tier 3 cannot get independent lanes** | Shared blind spots persist; no waiver exists | Block unless explicit waiver from coordinator |
| **Session auth/cwd broken** | Cannot execute work in broken environment | Fix auth/setup; block until environment is correct |
| **API credentials/quota missing** | Cannot authenticate or pay for route | Show setup guidance; block until credentials available |
| **Account cost exhausted with no fallback** | Would incur surprise cost or be payment failure | Block and escalate to user for approval |
| **Provider identity cannot be shown (Aggregator)** | User cannot see what route was actually used | Require explicit model ID before using aggregator |
| **Relay cannot explain the selection** | Selection is arbitrary or unjustifiable | Force Relay to articulate reasoning; block if none |
| **Silent fallback would reduce trust (Tier 2+)** | High-risk work downgrades to weaker route | Show fallback explicitly; ask user to approve or block |
| **DeepSeek route, candidate trust, Tier 3+ work** | Unvalidated provider for high-risk work | Block unless external validation passed |
| **OpenRouter auto-route for Tier 2+ work** | Unknown underlying provider/model selected | Force curated allowlist; block if no match |
| **Dual-lane required, only one trusted route available** | Cannot achieve independence | Block and escalate for vendor/model expansion |
| **Voice/realtime work without mic permission** | Cannot execute without explicit user consent | Block and request mic permissions |
| **Data leaving boundary with unknown policy** | Sensitive data to unknown provider policy | Block until provider policy confirmed or data excluded |

## Route Risk Register

| Risk | Applies To | Relay Behavior |
|---|---|---|
| Unknown exact model id | Any vendor | Query provider model registry before enabling route. |
| Aggregator route mismatch | OpenRouter | Show actual model/provider; cap authority; prefer direct for Tier 3+. |
| Cost surprise | Opus/pro/auto routes | Require cost posture, warn on premium route, expose Balance surface. |
| Prompt drag | All model calls, especially Q-mode | Require prompt payload snapshot and growth delta. |
| Data retention / provider policy | OpenRouter and some direct routes | Prefer direct/ZDR/deny-data-collection where available; surface policy state. |
| Missing CLI/API key/login | Local Codex/Claude and direct APIs | Show setup guidance; do not silently fall back to another route. |
| Account/session route unavailable | Account-backed routes | Fall through to next route class only if risk allows and fallback is shown to Prime/user. |
| Context nearly full | All session routes | Summarize and start new role-appropriate session. |
| Reasoning-mode mismatch | Reused sessions | Start or switch session/model for the new role. |
| Cross-project context bleed | Reused sessions | Block reuse and start project-specific session. |
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
route_class: account_session | local_cli | direct_api | aggregator_api
session_action: reuse | start_new | summarize_and_reset | transfer | no_session
reason
alternatives_rejected
cost_posture
trust_state
proof_required
human_gate_required
prompt_payload_budget
telemetry_required
```

Runtime checkpoint: `meridian_core/relay.py` now carries the first typed
`RelayRouteAudit` slice for these answers. It records route kind/class,
account-session-first precedence, session lifecycle action, trust state,
alternatives rejected, fallback blockers, proof requirements, and telemetry
requirements. It remains deterministic metadata only: it does not enable Auto
routing, wire vendors, or add routing audit text to model payloads.

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
