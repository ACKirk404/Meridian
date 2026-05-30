# Planning Harness Council Brief

## Purpose

Meridian's Planning Harness is Prime's automated planning engine. It turns an objective into Council-owned questions, researched answers, and a Chairman recommendation before workers are dispatched.

This carries forward the useful part of Matt Pocock's `grill-with-docs` skill from `mattpocock/skills` (`skills/engineering/grill-with-docs`): plans should interrogate the repo's own context before asking the human. It also carries forward Polaris's Builder Kernel improvement: the system must recommend actions, evidence, and decision-journal material, not merely ask questions.

## Meridian Rule

Prime should ask and answer every planning question through the lens of the Council:

- **Analyst:** What evidence or existing docs constrain this?
- **Devil's Advocate:** What assumption would make this fail?
- **Pragmatist:** What is the next useful planning action?
- **Contrarian:** What if the obvious implementation path is too rigid?
- **Expansionist:** What upside is missing from the current framing?
- **Chairman:** Which voice matters most, and what should Prime present or do?

## Grill-With-Docs Is A Prime Planning Primitive

`grill-with-docs` is not a side technique. It is the interrogation layer of Prime's Planning Harness.

Prime should use it whenever an objective is fuzzy, strategically important, architecture-shaping, or likely to create durable vocabulary. The point is not to slow the user down. The point is to prevent false clarity.

In Meridian, `grill-with-docs` becomes:

```text
Council questions -> repo/docs research -> recommended answers -> unresolved judgment only
```

This means Prime does not dump a wall of questions onto Scott. Prime should:

- Ask the Council-owned question.
- Search local context, FileMap, Obsidian, code, and prior decisions.
- Provide the recommended answer.
- Mark whether the answer is inferred, documented, or requires Scott.
- Capture new terms in `context.md`.
- Capture durable decisions as ADR candidates.

## Question, Research, Recommendation

The Planning Harness has three duties:

1. **Question:** generate the Council-owned questions appropriate to the risk tier.
2. **Research:** answer what can be answered from FileMap, context, Obsidian, prior decisions, and project notes.
3. **Recommend:** produce a Chairman recommendation with evidence needed and escalation status.

The default behavior is not "ask Scott." The default behavior is:

```text
research first -> recommend next -> ask Scott only for unresolved judgment
```

This matches the important `grill-with-docs` rule: for each question, provide the recommended answer, and if a question can be answered by exploring the codebase, explore the codebase instead.

## Current Slice

`meridian_core/planning.py` now defines:

- `PlanningContext`
- `PlanningAnswer`
- `PlanningQuestion`
- `PlanningRecommendation`
- `PlanningBrief`
- `build_planning_brief()`

The slice is deterministic and domain-only. It does not call models, scrape docs, query Obsidian, or dispatch workers yet.

## Polaris Carry-Forward

`grill-with-docs` taught three important lessons:

- Interrogate plans before implementation.
- Challenge fuzzy terms against the repo's shared language.
- Update `CONTEXT.md` and ADRs as decisions crystallize.

Polaris's Builder Kernel added three Meridian-critical lessons:

- A planning engine should infer intent and risk from the request.
- It should recommend actions with reasons and evidence expectations.
- It should draft decision-journal material so adaptive behavior remains auditable.

Meridian keeps those lessons but shifts the shape into Prime:

- Council voices own the questions.
- Research notes answer questions before escalation.
- Chairman recommendation chooses the next planning action.
- `terms_to_capture` and `adr_candidates` feed future Echo/Atlas memory.

## Next Slices

- Wire FileMap injection summaries into `PlanningContext.research_notes`.
- Add `prime_plan` CLI command to print PlanningBrief output.
- Add Review Console routing for high-risk unresolved Council questions.
- Add decision-journal output when a recommendation becomes an action.
