# Slide Deck Script (Enterprise Content Lifecycle Agent)

### Slide 1: Problem (0:00 - 0:20)
Enterprise content teams spend too much time on iterative drafting, compliance review, rework, localization, and formatting for multiple channels.
The result is slow cycle time and inconsistent outputs.

### Slide 2: Solution Overview (0:20 - 0:40)
We built a multi-agent workflow that automates the full lifecycle:
Draft → Compliance guardrails + audit report → Human approval gate → Localization → Packaging + publish calendar.

### Slide 3: Demo Flow (0:40 - 1:40)
1. Enter a content spec in the UI.
2. Click “Generate Draft + Compliance Report”.
3. Review compliance score and findings (forbidden terms, required disclaimers, tone heuristics).
4. Approve in the UI (human-in-the-loop).
5. Click “Run Full Workflow”.

### Slide 4: Outputs (1:40 - 2:20)
We generate localized, channel-specific publish payloads:
- blog version
- LinkedIn version
- email version
Each payload includes required disclaimers and scheduling metadata.

### Slide 5: Impact Model (2:20 - 3:00)
Back-of-envelope:
- Manual baseline: ~`6.75 hours/asset`
- Guardrails reduce rework, faster localization, and standardized packaging.
Estimated time saved: ~`~60%` of cycle time (assumptions stated).

