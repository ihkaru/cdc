# ADR Skill - CDC Edition

Use this skill to capture, draft, and review Architecture Decision Records (ADRs) as executable specifications for the CDC repo.

## Workflow

### Phase 0: Scan
- Read existing ADRs in `docs/adr/`.
- Check the current tech stack (FastAPI, Elysia, Vue/Quasar).
- Identify related code patterns in `rpa/src/worker/` or `dashboard/server/routes/`.

### Phase 1: Capture Intent
- Use Socratic questioning to understand the decision space.
- Focus on one question at a time.
- End with an intent summary for human approval.

### Phase 2: Draft ADR
- Use the structure: Status, Context, Decision, Consequences, Implementation Plan, Verification.
- **Critical**: Every ADR must have a specific **Implementation Plan** (files to change) and **Verification** (testable criteria).

### Phase 3: Review
- Validate: Could another agent implement this from the ADR alone?
- Are the verification criteria testable?

## Templates
Templates are located in `docs/adr/templates/` (to be created if needed).
