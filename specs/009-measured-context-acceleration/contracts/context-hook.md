# Context Hook Contract (planned)

## Codex event boundary

Official [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks) describes `UserPromptSubmit` input with `prompt` and accepts JSON output:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Possible files: src/example.py (name and task terms match)."
  }
}
```

The content is extra developer context. It must be neutral evidence for the agent to verify, never an instruction to ignore user requirements or edit a path. The installed client must pass a disposable live receipt trial before this contract is relied on.

## Input and output rules

- Read only the current prompt and local repository. Do not log either raw value.
- Return `{}` or no output for explicit-target, low-confidence, unavailable, timed-out, or unsupported cases.
- Return at most three safe tracked paths, one short reason each, and no more than 800 characters total. Do not include source text, secret names, commands, or an external URL.
- Never return a blocking decision from this event. The existing `PreToolUse` safety guard retains its separate deny/review behavior.
- Runtime and lookup errors fail open for context; diagnostic counters may record outcome and duration without raw values.

## Installation ownership

During evaluation, the prompt hook is registered only when `context_hint = true` is explicitly set and setup is rerun. The existing owned-hook manifest controls updates and removal. Guard-only setup and model enable/disable remain independent. A later default change requires all milestone gates and a trusted-profile trial.

## Client support

Codex is the only planned delivery client. Claude Code and OpenCode receive no context hook or support claim until their documented event, payload, response, and live behavior are independently checked.
