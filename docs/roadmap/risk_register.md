# Risk Register

| ID | Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- |
| R-001 | Nested repos hide source-of-truth state | High | Use a single top-level Git repo | closed |
| R-002 | Formal runs mix dirty worktrees and ad-hoc configs | High | Enforce manifest, registry, and clean-tree validation | open |
| R-003 | Figures drift from underlying runs | High | Gate paper usage on promoted runs and figure registry checks | open |
| R-004 | Dataset schema changes silently break evaluators | Medium | Freeze schema docs and validate required columns | open |
