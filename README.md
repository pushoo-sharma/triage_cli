# AI Message Triage Paid Trial

This is a paid trial for an ongoing AI automation role. The project is intentionally small and sanitized. It is meant to test how you read existing code, improve a partially built workflow, add safety, and propose useful product ideas without receiving overly detailed instructions.

## Time Box

- Maximum billable time: 4 hours unless approved in writing first.
- Do not start work until the Upwork contract is active.
- Use your own paid AI/coding-agent tooling. Do not request Tri Star credentials, API keys, production data, or account access.

## Goal

Improve this small AI-style inbound message triage workflow.

The current workflow:

- classifies inbound property-management messages
- drafts a basic response
- routes risky messages to human review
- logs basic processing details

It is intentionally underbuilt. Your job is to make one focused, high-value improvement and prove it works.

## Required Deliverable

Submit your completed work through the active Upwork workroom using whatever Upwork-supported delivery method is available, with:

1. A short README note explaining what you changed and why.
2. Tests and the exact command to run them.
3. Logging/error-handling/validation notes.
4. A short list of 3 product improvements you would build next.
5. A clear statement of which files/functions you wrote personally vs adapted/generated with AI help.

## What To Build

Pick one meaningful improvement. Examples:

- Improve classification accuracy and confidence scoring.
- Add a safer human-review gate for legally sensitive, maintenance emergency, or money-related messages.
- Add structured extraction, such as property, unit, urgency, callback number, and requested action.
- Add a better response-drafting layer that never fabricates facts and explains why a human review is needed.
- Add an evaluation/report command that shows classification accuracy on the sample dataset.

Do not build a giant system. A small, well-tested improvement with good judgment beats a large fragile rewrite.

## Baseline Commands

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
# Run triage on the sample set (JSON array or JSONL; both work)
python -m triage.runner data/sample_messages.json
# Report route accuracy vs. `expected_route` in the file (exit 1 if any labeled row mismatches)
python -m triage.runner eval data/sample_messages.json
```

## What changed in this branch

1. **Classification and confidence** — Rule-based signals (legal, fair housing, maintenance including crisis phrases, money) are scored and combined with a **priority order** (legal before fair housing before maintenance emergency before non-emergency maintenance before money, then general leasing). `confidence` is a **calibrated** value derived from cue strength instead of a single fixed number per branch.
2. **Human-review gate** — `review_triggers` lists stable codes (`legal`, `fair_housing`, `maintenance_emergency`, `maintenance`, `payment`, `invalid_sender`). `warnings` mirror prior names where applicable for compatibility. Money-related terms include `rent`, `balance`, `late fee`, and similar. **Invalid senders** still fail closed with no outbound draft.
3. **Structured extraction** — Each result includes `extraction` (`property_hint`, `unit`, `urgency`, `callback_number`, `requested_action`) from heuristics in `triage.extraction` (no invented street addresses).
4. **Response drafting** — `triage.drafting` builds **auto** replies with a generic acknowledgment, optional **verbatim** topic line when a subject word also appears in the body, and a **safety footer**. **Human review** routes get a holding message that **does not state account facts**, explains why a person must review, and may append “detected for staff” lines only when extraction found something.
5. **Evaluation** — `triage.evaluate.evaluate_dataset` and `python -m triage.runner eval <path>` print per-row match info and overall accuracy; **exit code 0** when all labeled rows match, **1** otherwise (useful for CI).

**Tests:** `pytest -q` (20 tests) including sample JSON gold routes, extraction, drafting, eval, and CLI.

**Logging / validation:** `invalid_sender` is still logged with `message_id` when present. Triage is deterministic and uses only the message dict (no network).

**Next product ideas (3):** (1) Per-portfolio policy YAML to tune terms and human-review rules without code changes. (2) Two-person approval queue for `human_review` with SLA timers by `maintenance_emergency`. (3) Train a small classifier on labeled exports while keeping this rule engine as a safety baseline.

**Authorship note for submission:** Core orchestration, scoring, extraction, drafting, evaluation, tests, and README updates were implemented for this task with AI assistance; the original trial skeleton lived in `core.py` / `runner.py` as provided.

## Evaluation Rubric



We will score:



- Code-reading and restraint: works with the existing code instead of rewriting everything.
- Product judgment: chooses a useful improvement for a real operations workflow.
- Safety: avoids fabricated facts, protects sensitive cases, and makes human-review boundaries clear.
- Tests: meaningful tests for normal cases and edge cases.
- Observability: useful logging or evaluation output.
- Communication: concise setup notes and clear tradeoffs.
- AI-agent fluency: uses AI tools effectively but verifies the result.



## Security Rules



- Use only the fake data in this project.
- Do not ask for logins, credentials, Yardi access, tenant records, or production code.
- Do not include secrets or real personal data in your submission.
- If you need more data, create additional fake examples.