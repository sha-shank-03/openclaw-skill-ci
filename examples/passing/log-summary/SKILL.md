---
name: log-summary
description: Read a supplied JSON event log and report error counts with the source path.
license: MIT-0
metadata:
  openclaw:
    os: [win32, linux, darwin]
---

# Log summary

When a user supplies a JSON log file, read the named file with the available
`read` tool. Expect an array of records, each with a string `level`.
Return a JSON object containing `error_count`, `records`, and `sources`.
Count a record as an error only when its level is exactly `error`.
If reading or parsing fails, report that failure and do not invent a summary.

The accompanying skill-ci.json is a project-owned CI declaration. It does not
configure OpenClaw's runtime permissions. CI runs a scripted mock workflow;
these Markdown instructions are never interpreted by a model in that test.
