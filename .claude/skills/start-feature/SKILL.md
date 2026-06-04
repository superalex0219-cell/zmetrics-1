# Skill: start-feature

Start a new feature with proper scaffolding: git branch, scoped context, implementation checklist.

## Usage

```
/start-feature <feature-name> [layer]
```

Examples:
```
/start-feature blast-event-crud backend
/start-feature artifact-upload backend
/start-feature report-pdf-export backend
/start-feature flutter-auth mobile
/start-feature depth-estimation worker
```

## What this skill does

1. **Reads context** — loads `CLAUDE.md`, `docs/domain_model.md`, the relevant `.claude/rules/{layer}.md`, and the latest handoff in `docs/handoffs/`

2. **Creates a git branch** — `feat/{feature-name}`

3. **Prints a scoped implementation checklist** covering:
   - What entities/tables are affected
   - Which services need to be created or extended
   - Which routers/endpoints need to be added
   - Which Pydantic schemas are needed
   - Whether a migration is required
   - What tests to write
   - What AuditLog entries are required (if applicable)

4. **Reminds the scope boundary** — lists what NOT to touch in this session

## Instructions

When this skill is invoked:

1. Read `CLAUDE.md` and `docs/domain_model.md`
2. Read the relevant rule file for the layer (e.g., `.claude/rules/backend.md`)
3. Read the most recent file in `docs/handoffs/` if one exists
4. Determine what the feature touches based on the domain model
5. Print the checklist in this format:

```
## Feature: {feature-name}
### Layer: {layer}
### Branch: feat/{feature-name}

### Scope
What this session will implement:
- [ ] item 1
- [ ] item 2

### Out of scope (do not touch)
- list of things not to implement

### Files to create or modify
- path/to/file.py — what changes

### Migration needed?
Yes/No — reason

### Tests to write
- test name: what it verifies

### Safety checks
- [ ] AuditLog entries required for: (list)
- [ ] Recommendation safety constraints apply: Yes/No
```

6. Ask: "Does this scope look correct before I start?"
