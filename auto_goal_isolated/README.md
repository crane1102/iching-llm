# Auto-Goal Safety Harness

This package is an **opt-in, isolated safety harness** for experimenting with auto-goal classification and lifecycle behavior around an independent application. It does not integrate with Hermes internals, read historical sessions, create continuations, write queues/locks/pending events, or change prompts.

## Guarantees

- Explicit text and metadata only; no implicit history.
- Conservative rejection of stale/internal state markers.
- Candidate-only classification; simulation is in-memory and bounded.
- Fail-open behavior: component, storage, or audit failures abandon the current decision without blocking ordinary application use.
- Bounded redacted audit output, symlink protection, and no background workers.

## Use

```python
from auto_goal_isolated import classify
result = classify("plan, implement, test, and verify", {"session_id": "demo-001"})
```

This is a test harness, not a replacement for a native goal manager. Keep production auto-goal disabled until independent users verify it.
