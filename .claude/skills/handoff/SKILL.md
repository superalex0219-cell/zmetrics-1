# Skill: handoff

Write a structured handoff document for the current session so the next session (or device) can continue without losing context.

## Usage

```
/handoff [title]
```

Examples:
```
/handoff
/handoff "backend auth integration"
/handoff "worker depth estimation step"
```

## What this skill does

Generates a handoff file at:
```
docs/handoffs/YYYY-MM-DD-{title-or-auto}.md
```

Then offers to commit it: `git add docs/handoffs/ && git commit -m "docs: add handoff {title}"`

## Instructions

When this skill is invoked:

1. Run `git status` to see what changed this session
2. Run `git diff --stat HEAD` to summarize file changes
3. Ask the user (or infer from context):
   - What was the goal of this session?
   - What was completed?
   - What was NOT completed or is blocked?
   - What should the next session start with?

4. Write the handoff file with this structure:

```markdown
# Handoff: {title}

**Date:** {YYYY-MM-DD}
**Session goal:** {one sentence}
**Status:** completed | partial | blocked

## What was done

- list of completed items with file paths

## Files changed

{paste of git diff --stat output}

## What was NOT done / is blocked

- item: reason

## Known issues or tech debt introduced

- issue: description (acceptable for now because...)

## Next session: start here

1. Read: @CLAUDE.md, @docs/domain_model.md, @{relevant rule file}
2. First task: {specific actionable next step}
3. Then: {second step}

## Commands to verify current state

\`\`\`powershell
# Start services
docker compose -f infra\docker-compose.yml up -d

# Run tests
docker compose -f infra\docker-compose.yml exec backend pytest -v

# Check migration status
docker compose -f infra\docker-compose.yml exec backend alembic current
\`\`\`
```

5. After writing the file, print:
```
Handoff written to: docs/handoffs/{filename}

Commit command:
  git add docs/handoffs/
  git commit -m "docs: add handoff {title}"

Share this file at the start of the next session:
  @docs/handoffs/{filename}
```
