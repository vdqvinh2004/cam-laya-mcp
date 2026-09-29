# Milestone 2: Command safety hardening

**Status:** Implemented.

## Goal

Catch common destructive shell forms before model inference or daemon availability can affect a risk decision. Reduce false alarms for command text that is only being printed.

## User scenarios

1. A coding agent proposes a destructive command with long flags, Git global options, a wrapper, a pipe, a separator, or a nested shell invocation. The hook requires human review using the client's supported mechanism.
2. An MCP client asks for a risk decision while the model is disabled or unavailable. The same hard-risk reason still requires human review.
3. A user prints an example command such as `echo 'rm -rf /tmp/data'`. The command rule does not treat that text as executed shell code.

## Acceptance

- One shared `hard_risk` path covers hooks, direct policy decisions, and unavailable-runtime fallback.
- Detect forced recursive removal, force pushes, Git commands that discard local work, `find -delete`, shell input from a pipe, infrastructure deletion, privileged changes, and secret paths.
- Inspect common shell separators, environment wrappers, command substitutions, and `sh -c` scripts.
- Keep model confidence unable to override a hard rule; preserve client-specific deny or ask behavior.
- Add runnable regression cases for blocked commands and ordinary quoted examples. Full test suite and `git diff --check` pass.

## Limit

This is a conservative static check. It cannot inspect commands assembled at runtime or inside external scripts; it is not a shell sandbox.
