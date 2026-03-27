# Enterprise Content Lifecycle Agent (Multi-Agent)

This project builds an agentic system that automates the full lifecycle of enterprise content:
creation, compliance guardrails + audit reporting, localization, multi-channel packaging, and publish scheduling (demo).

## What you get

- **Multi-agent pipeline** (draft → compliance → human approval gate → localization → packaging → publish calendar)
- **Compliance guardrails** (required disclaimers + forbidden term checks + tone heuristics)
- **Audit trail** (`runs/<job_id>/workflow_run.json`) with timestamps, scores, and decisions
- **Measured impact model** (back-of-envelope time saved + rework reduction with explicit assumptions)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys:**
   Copy `.env.example` to `.env` and add your Hugging Face API key.
   ```bash
   cp .env.example .env
   ```

3. **Run the Enterprise Web App (FastAPI + HTML/CSS/JS):**
   ```bash
   python src/server.py
   ```
   *Then open `http://localhost:8000` in your browser.*

4. **Run the CLI workflow:**
   ```bash
   python src/cli.py --auto-approve --spec "Launch a product update page and social posts with compliance guardrails"
   ```

## Demo workflow (what to show on video)

1. Generate **Draft + Compliance Report** in the UI
2. Review compliance findings (tone + forbidden terms + disclaimers)
3. Approve (human-in-the-loop gate)
4. Click **Run Full Workflow**
5. Show **Publish Calendar** payloads + localized variants

## Project Structure

- `src/engine.py`: core multi-agent workflow implementation featuring **Hugging Face** integration.
- `src/server.py`: FastAPI backend exposing the workflow.
- `src/cli.py`: CLI runner + optional manual gate.
- `static/`: Premium glassmorphism Web UI (`index.html`, `style.css`, `app.js`).
- `runs/<job_id>/`: workflow artifacts (audit + generated payloads).
- `bonus_demos/`: Alternative projects & PDFs.

## Architecture (roles & communication)

See `docs/enterprise_content_architecture.md` for the diagram and step-by-step logic.

## Impact Model (back-of-envelope)

The workflow computes:

- **Estimated manual time vs automated time**
- **Rework reduction estimate** based on compliance pass/fail

Assumptions are embedded in the code (and also shown in the UI):

- Manual baseline per asset: `6.75 hours`
- Draft/packaging/localization savings targets: `~40%`, `~55%`, `~20%` respectively
- Rework reduction: higher when compliance passes

For hackathon submission, we explicitly treat localization/compliance as “guardrail + structured workflow” so you can defend the math with predictable pipeline overhead reductions.

