# SKILL.md — User Notification Management

## Purpose
Standardizes how AI agents communicate with the system administrator via Telegram notifications. Use this skill when you need to alert the human operator about a blocker, an error, or the completion of a major task.

## Prerequisites
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ADMIN_CHANNEL_ID` environment variables configured in `.env`.
- Python script at `scripts/notify.py`.

## Command Reference

### Send Notification

```bash
python $PROJECT_ROOT/scripts/notify.py "Title" "Message content" [priority]
```
*(If `$PROJECT_ROOT` is not set, use the absolute or relative path to `scripts/notify.py`)*

### Priority Levels
- `low`: Routine status updates.
- `default`: Standard work item transitions.
- `high`: Critical errors, quota exhaustion, or items requiring manual approval.

## Common Patterns

### Resource Request
When blocked by quota or needing funding approval:

```bash
python scripts/notify.py "RESOURCE REQUEST" "Gemini API quota is exhausted. Please refill." high
```

### Task Completion
When finishing an automated workflow:

```bash
python scripts/notify.py "TASK COMPLETE" "The onboarding workflow has finished successfully." default
```
