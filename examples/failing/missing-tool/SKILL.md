---
name: missing-tool
description: Intentionally fail fixture readiness because a declared binary is unavailable.
license: MIT-0
metadata:
  openclaw:
    requires:
      bins: [fictional-log-cli]
---

# Intentionally missing prerequisite

Read the supplied JSON event log and report error counts. The fictional-log-cli
binary is deliberately absent from the supplied fixture environment. This is
a readiness prediction failure, and the mock workflow must not start.
