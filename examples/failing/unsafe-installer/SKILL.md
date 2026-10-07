---
name: unsafe-installer
description: Deliberately invalid installer declaration for the offline example.
license: MIT-0
metadata:
  openclaw:
    install:
      - kind: node
        package: fictional-log-cli;echo-unexpected
---

Summarize fictional logs. The installer target intentionally violates this
tool's portable profile. Candidate commands and installers are never executed.
