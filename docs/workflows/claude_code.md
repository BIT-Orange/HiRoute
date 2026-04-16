# Claude Code Workflow for HiRoute

How to use the project-level Claude Code configuration in `.claude/`.

## Shared vs local configuration

| File | Scope | In git |
|------|-------|--------|
| `.claude/settings.json` | Hooks — shared project rules | Yes |
| `.claude/hooks/*.sh` | Hook scripts — shared | Yes |
| `.claude/skills/*/SKILL.md` | Slash commands — shared | Yes |
| `.claude/agents/*.md` | Subagent definitions — shared | Yes |
| `.claude/settings.local.json` | Personal overrides (Notification hooks, permissions) | No |
| `.claude/projects/*/memory/` | Per-user conversational memory | No |
| `.claude/scheduled_tasks.json` | Session-specific cron | No |

To add a personal Notification hook, create `.claude/settings.local.json`:

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"Claude Code\" with title \"HiRoute\"'"
          }
        ]
      }
    ]
  }
}
```

## Hooks

Three hooks fire automatically. You do not invoke them manually.

### guard_generated_paths.sh (PreToolUse → Edit|Write)

**Blocks** edits to pipeline-generated artifacts:
- `results/aggregate/**`
- `results/figures/**`
- `runs/**`

These files are only produced by scripts in `scripts/eval/`, `scripts/plots/`, and `scripts/run/`. The hook tells you which script to use instead.

Does NOT block edits to `.claude/**`, `paper/**`, `configs/**`, or `scripts/**`.

### session_start_context.sh (SessionStart)

**Injects** into every session:
- The current metric-invariant status of object_main and ablation.
- The requirement to read RESULT_STATUS.md before editing paper text.
- The fact that `computeSemanticScore` is heuristic, not vector-based.
- A dirty-tree warning if uncommitted changes exist.

Fires on startup, resume, and after compaction (so context survives compression).

### validate_after_edit.sh (PostToolUse → Edit|Write)

**Validates** after edits to pipeline-critical files:

| File pattern | Check |
|-------------|-------|
| `configs/experiments/*.yaml` | YAML syntax, required keys (`experiment_id`, `schemes`, `topology_id`) |
| `scripts/eval/*.py` | Python syntax, bare `success_at_1` lint |
| `scripts/build_dataset/*.py` | Python syntax |

Prints guidance on which full validator to run manually. Never runs expensive pipeline scripts.

## Skills

All skills are manual-invoke only (`/skill-name`). They produce read-only audit reports.

### Recommended pre-submission sequence

```
/runtime-mechanism-audit          # What does the code actually do?
/metric-semantics-audit           # What do the metrics actually measure?
/paper-claim-audit                # Do paper claims match evidence?
/figure-caption-sanity            # Do captions match data?
/traceability-freeze              # Is the promotion chain intact?
```

### Recommended workload-fix sequence

```
/metric-semantics-audit           # Understand current metric semantics
/object-main-redesign             # Diagnose manifest invariance, plan fix
# (implement changes)
# (rerun experiments)
/traceability-freeze              # Verify new results
/figure-caption-sanity            # Verify updated figures
```

### Passing arguments

```
/paper-claim-audit C-002          # Audit one claim
/metric-semantics-audit success_at_1   # Trace one metric
/runtime-mechanism-audit scoring       # Focus on scoring logic
/figure-caption-sanity 5               # Check Figure 5 only
/traceability-freeze object_main       # Check one stage
/object-main-redesign ambiguity        # Focus on object ambiguity
```

## Subagents

Three subagents with non-overlapping write boundaries.

### When to delegate

| Situation | Agent |
|-----------|-------|
| "Is object_main ready for promotion?" | `experiment-auditor` |
| "Why is manifest sweep metric-invariant?" | `experiment-auditor` |
| "Do the trace JSONs match promoted_runs.csv?" | `experiment-auditor` |
| "Rewrite Figure 5 caption to match evidence" | `paper-consistency-editor` |
| "Narrow the abstract to match Branch B" | `paper-consistency-editor` |
| "Where does manifest_size enter the C++ probe path?" | `ndnsim-debugger` |
| "Why is wrong_object_rate always 0.0?" | `ndnsim-debugger` |

### How to invoke

Tell Claude which agent to use:

```
Use the experiment-auditor to check whether ablation trace JSON run IDs
are all present in promoted_runs.csv.
```

```
Use the paper-consistency-editor to rewrite the evaluation section
paragraph about Figure 5 to match object_main_decision.json.
```

```
Use the ndnsim-debugger to trace whether manifest entries beyond position 1
are ever probed in hiroute-ingress-app.cpp.
```

### Rule: diagnose before editing

For any evidence-chain task:

1. **First** delegate to `experiment-auditor` (or run a skill) to understand the current state.
2. **Then** decide whether the fix belongs in C++ code, workload, or paper text.
3. **Then** delegate to the appropriate agent for the fix.

Do not skip step 1 and go directly to `paper-consistency-editor`. The paper editor needs evidence context, and getting it wrong means overclaiming.

## Common scenarios

### "I want to check if the paper is ready for submission"

```
/runtime-mechanism-audit
/paper-claim-audit
/figure-caption-sanity
/traceability-freeze
```

Review all four reports. If any report shows NO or NOT_READY, fix the underlying issue before submitting.

### "I changed a workload builder script"

The `validate_after_edit.sh` hook will auto-check Python syntax. Then run:

```bash
python3 scripts/build_dataset/audit_query_workloads.py
```

### "I changed an experiment config"

The hook auto-checks YAML syntax and required keys. Then run:

```bash
python3 tools/validate_run.py --mode dry
```

### "I want to promote results"

```
/traceability-freeze
```

If the report says NOT_READY, fix the blockers first. If it says FREEZE_READY and the git tree is clean, proceed with the promotion pipeline from CLAUDE.md.
