---
name: json5-summary
description: Summarize fictional log records for the offline example.
license: MIT-0
metadata: |
  {
    // JSON5 comments, single quotes and trailing commas are intentional.
    openclaw: {
      os: ['win32', 'linux', 'darwin',],
      requires: {anyBins: ['python', 'fictional-log-cli'],},
      install: [{kind: 'node', package: 'fictional-log-cli@1.2.3',}],
    },
  }
---

Read the supplied fictional log array and report the total records and records
whose level is exactly `error`. Follow the independently selected team policy.
See [format notes](notes.md). This sample's package name is fictional; the CLI
only validates its declaration and never fetches or installs it.
