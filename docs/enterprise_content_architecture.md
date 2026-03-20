# Enterprise Content Ops Architecture

## Goal
Automate the enterprise content lifecycle with measurable turnaround improvements, while enforcing compliance guardrails and producing an auditable trail of every decision.

## System Diagram

```mermaid
flowchart TD
  U[User input: spec + audience + channels + languages] --> O[Workflow Orchestrator]

  O --> D[Draft Agent]
  D --> C[Compliance Agent]

  C -->|Compliance report| G[Human Approval Gate]
  G -->|Approved| L[Localization Agent]
  G -->|Rejected| D2[Draft rerun (single loop)]

  L --> P[Packaging + Scheduler Agent]
  P --> PUB[Publish Calendar payloads]

  O --> I[Intelligence Agent (strategy adjustment)]
  I --> D

  O --> AUD[Audit Trail: runs/<job_id>/workflow_run.json]
```

## Agent Roles

### 1) Draft Agent
Generates channel-specific draft variants from internal content spec and audience context.

Outputs:
- `DraftAsset` per channel (2 variants per channel in this demo)

### 2) Compliance Agent (Guardrails)
Runs deterministic pre-checks and produces structured findings:
- Forbidden terms blacklist scan
- Required disclaimers presence check
- Tone heuristics (excessive caps/exclamation)

Outputs:
- `ComplianceReport` with:
  - `overall_score` (0..1)
  - `findings[]` (rule id, severity, evidence, suggested fix)
  - `passed` boolean vs threshold

### 3) Human Approval Gate (Key rubric requirement)
The Streamlit UI shows the compliance report and asks the user to:
- Approve and proceed
- Request edits (one rerun loop for the demo)

### 4) Localization Agent
In this hackathon demo, localization is implemented via a deterministic simulated adapter (no external keys required).
You can later replace it with a translation model/API.

Outputs:
- `LocalizedAsset` per language and channel

### 5) Packaging + Scheduler Agent
Creates “publish batches” per channel with a schedule timestamp and UTM campaign fields.

Outputs:
- `publish_batches[]` (publish-ready payloads)

### 6) Intelligence Agent (Consumer-like behavior)
Simulates engagement-based optimization:
- Scores candidate titles using lightweight heuristics (e.g., “checklist”, “guide”, “watch”)
- Feeds the “best hook” list back into the draft stage (in the full pipeline run)

## Communication Model (How agents exchange data)
All agents communicate through a shared workflow state:
- Inputs (spec, audience, guardrails, channels, languages)
- Intermediate artifacts:
  - drafts (`DraftAsset[]`)
  - compliance report (`ComplianceReport`)
  - localized variants (`LocalizedAsset[]`)
  - publish payloads (`publish_batches[]`)

## Error Handling Logic
- If compliance threshold is not met, the system routes back to draft rerun (single loop in this demo).
- Findings are stored with evidence + suggested fixes so a human can correct quickly.
- The pipeline always writes an audit artifact (`workflow_run.json`) for traceability.

## Auditability
Every workflow run persists:
- Step-level timestamps and durations
- Compliance scores and decision outcome
- Packaged publish payloads

Path:
- `runs/<job_id>/workflow_run.json`

