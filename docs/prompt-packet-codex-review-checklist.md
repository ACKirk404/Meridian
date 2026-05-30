# Prompt Packet Codex Review Checklist

**Status:** Code review checklist for Prompt Packet implementation  
**Purpose:** Concrete checklist for Codex to use when reviewing a Prompt Packet domain model  
**Reference:** `docs/prompt-packet-implementation-checklist.md`

---

## Files Expected

### Required Files
- `meridian_core/prompt_packet.py` — Domain model with PromptPacket class and PromptPacketError
- `tests/test_prompt_packet.py` — Comprehensive unit tests for all validations

### Optional Files (defer to end)
- `meridian_core/__init__.py` — Export additions (should be last step, not blocking review)

### Files NOT to Touch
- `meridian_core/prompt_budget.py` — Locked, no changes
- `meridian_core/prompt_metrics.py` — Locked, no changes
- `meridian_core/relay.py` — No integration yet
- `docs/FileMap.md` — Build 1 owns this
- `docs/prompt-packet-*.md` — Design and checklist are planning docs, not reviewed

---

## Required Tests (13 Test Cases)

Verify all test groups exist and test names are clear:

### Group 1: Creation and Immutability
- [ ] `test_prompt_packet_creation` — Can instantiate valid PromptPacket
- [ ] `test_prompt_packet_immutable` — Frozen, raises on mutation attempt

### Group 2: Budget Compliance
- [ ] `test_budget_compliance_pass` — prompt_tokens ≤ max_context_tokens passes
- [ ] `test_budget_compliance_fail` — prompt_tokens > max_context_tokens fails

### Group 3: Source Compliance
- [ ] `test_source_compliance_pass` — All sources in lineage are in allowed_sources
- [ ] `test_source_compliance_fail` — Unknown source in lineage fails

### Group 4: Serialization Integrity
- [ ] `test_serialization_non_empty` — Empty prompt rejected
- [ ] `test_serialization_is_string` — Type validation for serialized_prompt

### Group 5: Lineage Integrity
- [ ] `test_lineage_totals_match` — sum(source_lineage.values()) ≤ prompt_tokens passes
- [ ] `test_lineage_totals_exceed` — sum > tokens fails

### Group 6: Construction Time Sanity
- [ ] `test_construction_time_valid` — 0 ≤ construction_time_ms < 30000 passes
- [ ] `test_construction_time_negative` — Negative time fails
- [ ] `test_construction_time_unrealistic` — construction_time_ms ≥ 30000 fails

### Group 7: No Mutations Across Instances
- [ ] `test_source_lineage_isolated` — Mutating source_lineage dict doesn't affect next packet

---

## Immutability Checks

- [ ] **Frozen dataclass**: `@dataclass(frozen=True)` decorator present
- [ ] **No setattr in __post_init__**: If validation needs to set fields, use `object.__setattr__(self, field, value)`
- [ ] **Tuple for allowed_sources**: `allowed_sources: tuple[str, ...]` not list
- [ ] **Dict copy for lineage**: source_lineage stored as new dict (no reference to original)
- [ ] **created_at immutable**: Uses `default_factory` or field(init=False, default_factory=...)
- [ ] **is_valid and validation_errors immutable**: Set in __post_init__, not mutable

---

## Budget Validation Checks

- [ ] **Budget rule enforced**: `prompt_tokens <= max_context_tokens`
- [ ] **Captured in is_valid flag**: Not thrown as exception
- [ ] **Captured in validation_errors**: Descriptive message added to errors list
- [ ] **Receives rules, doesn't import Budget**: No circular dependency on PromptBudgetPlan
- [ ] **Budget fields are individual**: max_context_tokens and allowed_sources as separate fields, not a Budget object

---

## Source Lineage Validation Checks

- [ ] **Source lineage is dict**: `source_lineage: dict[str, int]` (tracks tokens per source)
- [ ] **All sources checked**: Every key in source_lineage must be in allowed_sources
- [ ] **Captured in is_valid flag**: Not thrown as exception
- [ ] **Captured in validation_errors**: Descriptive message for unknown sources
- [ ] **Lineage totals match tokens**: `sum(source_lineage.values()) <= prompt_tokens`
- [ ] **Dict is not shared**: Each packet gets its own copy of lineage dict (no reference leakage)

---

## No Prompt Metadata Leakage

### Fields that MUST NOT be in `serialized_prompt`
- [ ] `packet_id` — Internal correlation ID only
- [ ] `construction_time_ms` — Relay metric, not worker concern
- [ ] `source_lineage` — Internal accounting
- [ ] `max_context_tokens` — Validation boundary, not worker data
- [ ] `allowed_sources` — Used to build packet, not for worker
- [ ] `tier` — Routing/tracing metadata
- [ ] `lane_role` — Routing/tracing metadata
- [ ] `is_valid` — Validation state (invalid packets never sent)
- [ ] `validation_errors` — If invalid, packet doesn't reach worker
- [ ] `created_at` — Timestamp for logging

### Only `serialized_prompt` goes to worker
- [ ] **Extraction method exists**: Clear way to get just the prompt string
- [ ] **No metadata in prompt**: serialized_prompt is pure prompt text, nothing else
- [ ] **Comments clarify intent**: Docstring explains why metadata stays internal

---

## No Relay Integration Yet

- [ ] **No relay imports**: prompt_packet.py doesn't import relay module
- [ ] **No Relay references**: No references to RelayRoute, RelayLane, dispatch, etc.
- [ ] **No circular dependency**: Relay can import PromptPacket, but not vice versa
- [ ] **Integration planned for Phase 2**: Comments/docstrings can note future dispatch integration
- [ ] **No worker sending logic**: Packet creation is standalone, not integrated with routing yet

---

## No Package Export Yet

- [ ] **meridian_core/__init__.py unchanged**: No PromptPacket or PromptPacketError added yet
- [ ] **Build 3 checklist note honored**: "optional, defer to end"
- [ ] **Export deferred**: Can be added in a separate PR once implementation is validated
- [ ] **Tests import directly**: Tests import from `meridian_core.prompt_packet` directly, not from root

---

## Validation Rules — In Order

Verify all 5 rules are implemented and checked in this order:

1. **Budget compliance**: `prompt_tokens <= max_context_tokens`
2. **Source compliance**: All keys in `source_lineage` are in `allowed_sources`
3. **Serialization integrity**: `serialized_prompt` is non-empty string
4. **Construction time sanity**: `0 <= construction_time_ms < 30000`
5. **Lineage integrity**: `sum(source_lineage.values()) <= prompt_tokens`

- [ ] All 5 rules present in __post_init__
- [ ] Rules checked in order (order matters for error message clarity)
- [ ] Each failure adds descriptive message to validation_errors
- [ ] is_valid flag set correctly (True if no errors, False if any error)

---

## Error Handling

- [ ] **is_valid flag, not exceptions**: Validation errors are captured in flags, not raised
- [ ] **validation_errors is tuple**: Immutable list of error messages
- [ ] **Descriptive messages**: Error messages are specific (e.g., "budget exceeded by X tokens")
- [ ] **No exception on invalid packet**: Can create invalid packets, but they're marked invalid
- [ ] **Exceptions only for programming errors**: Type mismatches, missing required fields (these are bugs, not validation)

---

## Code Quality Checks

- [ ] **Single class, single error type**: PromptPacket (domain) + PromptPacketError (exception)
- [ ] **__post_init__ logic is clear**: Validation is readable, not overly nested
- [ ] **No magic numbers in code**: Time bounds (30000) can be constants or well-commented
- [ ] **Field names match checklist**: packet_id, serialized_prompt, prompt_tokens, max_context_tokens, allowed_sources, construction_time_ms, source_lineage, tier, lane_role, is_valid, validation_errors, created_at
- [ ] **Type hints complete**: All fields have clear types
- [ ] **Docstrings present**: Class and __post_init__ explain purpose and constraints

---

## Codex Review Questions

Answer these before approval:

1. **Frozen dataclass vs named tuple?**
   - Recommendation: Frozen dataclass (matches PromptBudgetPlan pattern)
   - Verify: Is this choice consistent with codebase style?

2. **Where should PromptPacket live — new module or nested?**
   - Recommendation: New module `meridian_core/prompt_packet.py` (separation of concerns)
   - Verify: Does this module structure match codebase conventions?

3. **Should validation errors be exceptions or flags?**
   - Recommendation: Flags (is_valid, validation_errors) — allows Prime to see all errors at once
   - Verify: Does this design allow downstream (Relay/Prime) to handle gracefully?

4. **Source lineage as dict or frozenset?**
   - Recommendation: Dict (tracks tokens per source for tuning, more useful than just presence/absence)
   - Verify: Is token-per-source tracking valuable for metrics and tuning?

5. **When should Packet be created — during dispatch or before?**
   - Currently: Standalone (can be created anywhere)
   - Future: Integration in relay dispatch (Phase 2)
   - Verify: Is standalone creation sufficient for now?

6. **Should Packet store PromptBudgetPlan object or just the values?**
   - Recommendation: Just the values (max_context_tokens, allowed_sources as fields)
   - Verify: Does this prevent circular reference and keep Packet simple?

---

## Test Coverage

- [ ] **13 test cases present**: All groups represented
- [ ] **Coverage ≥ 80%**: Code coverage meets project minimum
- [ ] **No skipped tests**: All tests run and pass
- [ ] **Edge cases covered**: Empty lineage, zero tokens, exact boundary values
- [ ] **Integration path clear**: Tests don't need relay/metrics yet, just standalone PromptPacket

---

## Sign-Off Checklist

When all checks above pass:

- [ ] All 13 tests pass (644+ total tests including existing suite)
- [ ] No new warnings or errors
- [ ] No circular dependencies introduced
- [ ] Immutability verified (frozen dataclass works as expected)
- [ ] Validation rules work correctly
- [ ] No metadata leakage to prompts
- [ ] Code ready for Phase 2 (Relay dispatch integration)
- [ ] Ready to proceed to next build task

---

## Next Steps

Once review passes:
1. Answer the 6 Codex review questions (confirm or provide alternatives)
2. Approve for Phase 2: Relay dispatch integration (future build lane)
3. Plan and execute Prompt Packet + Relay integration when ready

Ready for Codex review.
