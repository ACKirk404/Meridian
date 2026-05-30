# Cockpit UI Architecture

Meridian's interface should feel like a cockpit: Prime-centered, instrumented, alive, and operational.

This document captures the current UI direction without implementing UI yet.

## Core Inversion

Polaris was worker-card centric.

Meridian should be Prime-centric.

The main screen is not a wall of worker sessions. It is Prime's command surface, with worker/session machinery available behind queues, tabs, drilldowns, and harness views.

## Main Surfaces

### Top Navigation

Persistent controls:

- Settings
- Projects
- Reset
- Close
- Cross Check
- Backlog
- Skills
- Harness
- Search
- Mission Objectives / Compass

The Mission Objectives / Compass control should call up the current Compass-derived objective view at any time.

### Main Cockpit Screen

The main cockpit screen can use tabs to conserve space:

- Orchestrator Queue
- Review Console

These are two prompt windows in the same cockpit surface.

### Orchestrator Queue

The Orchestrator Queue is where Scott and Prime communicate.

It contains:

- Prime conversation
- progress intention
- judgment requests
- outcomes
- explanations Prime chooses to say conversationally

### Review Console

The Review Console is the promptable review/gating surface.

It contains:

- automatic cross-check findings
- plan reviews
- proof and evidence
- artifacts
- comparisons
- approval gates
- system findings Prime wants visible

It is not a passive log. Scott can respond directly to the item Prime placed there.

## Wake And Boot Experience

Prime's conversational wake belongs in the Orchestrator Queue:

```text
Good morning, Scott.
Allow me to check today's mission file.
```

NASA-style readiness calls belong in system instrumentation or the Review Console if shown as text:

```text
Bifrost Go.
Beacon Go.
Echo Go.
Relay Go.
```

The preferred experience is audio-first:

- the system speaks each Go call
- the corresponding cockpit indicator lights up
- the text does not crowd the Prime conversation

## Bottom / Edge Instrumentation

Instrument panels should show compact, high-value state:

- active risk tier
- dual-lane cognition mode
- mission file loaded
- Beacon health
- Relay route
- Aegis proof status
- Compass/project bearing
- Meridian build number
- harness maturity summary

System details should be available but not dominate the main conversation.

## Session Machinery

Builder, Reviewer, and Verifier remain important roles, but they do not need permanent full panels.

They can appear as:

- compact lane indicators
- drilldown items
- Review Console items
- harness views
- session detail panel when Scott explicitly opens one

Prime owns routine builder/reviewer/verifier loops.

## Visual Direction

Current preferred mockup direction:

- cinematic cockpit/window layout
- dark navy/black glass
- cyan/teal instrumentation
- amber warnings
- restrained violet accents
- dense but readable
- premium command center, not playful dashboard

## Open UI Questions

- Is `Mission Objectives` the button label, or should the visible label be `Compass`?
- Should Review Console open as a tab, drawer, or full alternate main surface?
- Should the wake audio be optional by mode: full wake, fast wake, skip?
- Where should the active risk tier control live: top nav, bottom instrumentation, or Prime panel header?
- How much system health should be shown before it becomes noise?
