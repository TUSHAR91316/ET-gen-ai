import json
import os
import random
import re
import time
import uuid
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# Enable logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("enterprise_ops")

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

hf_token = os.environ.get("HUGGINGFACE_API_KEY")
hf_client = InferenceClient(token=hf_token) if InferenceClient and hf_token and hf_token != "your_api_key_here" else None

def generate_text_with_llm(prompt: str, max_new_tokens: int = 300) -> Optional[str]:
    if not hf_client:
        return None
    try:
        logger.info("Calling Hugging Face Inference API...")
        # Using a fast instruction-tuned model
        response = hf_client.text_generation(
            prompt,
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            max_new_tokens=max_new_tokens,
            temperature=0.7,
            return_full_text=False
        )
        return response.strip()
    except Exception as e:
        logger.error(f"Hugging Face API call failed: {e}")
        return None


CHANNELS_DEFAULT: List[str] = ["blog", "linkedin", "email"]
DEFAULT_LANGUAGES: List[str] = ["hi", "ta"]


DEFAULT_GUARDRAILS: Dict[str, Any] = {
    "brand_name": "ET Markets",
    "required_disclaimers": [
        "This content is for informational purposes only.",
        "Not financial advice. Please consult a qualified professional.",
        "Past performance is not indicative of future results.",
    ],
    "forbidden_terms": [
        "guaranteed",
        "100% sure",
        "no risk",
        "guaranteed returns",
        "certain profit",
        "guaranteed profit",
    ],
    "tone_constraints": {
        "avoid_excessive_caps": True,
        "max_exclamation": 3,
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"


def _jsonable(x: Any) -> Any:
    """
    Make objects safely JSON-serializable for audit logs.
    """
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, (list, tuple)):
        return [_jsonable(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if hasattr(x, "__dict__"):
        return _jsonable(x.__dict__)
    return str(x)


@dataclass
class ContentRequest:
    spec: str
    audience: str
    channels: List[str]
    languages: List[str]
    guardrails: Dict[str, Any] = field(default_factory=lambda: DEFAULT_GUARDRAILS.copy())
    job_id: str = field(default_factory=_job_id)
    strategy_objective: str = "Improve turnaround time and content consistency"
    human_auto_approval: bool = False


@dataclass
class DraftAsset:
    channel: str
    variant_id: str
    title: str
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceFinding:
    rule_id: str
    severity: str  # "low" | "med" | "high"
    message: str
    evidence: str = ""
    suggested_fix: str = ""


@dataclass
class ComplianceReport:
    overall_score: float  # 0..1, higher is better
    findings: List[ComplianceFinding]
    passed: bool
    threshold: float


@dataclass
class LocalizedAsset:
    original_variant_id: str
    channel: str
    language: str
    title: str
    body: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PackagedAsset:
    localized_assets: List[LocalizedAsset]
    publish_batches: List[Dict[str, Any]]


@dataclass
class WorkflowStep:
    name: str
    started_at: str
    finished_at: str
    duration_ms: int
    agent: str
    summary: str
    raw_output: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRun:
    job_id: str
    request: ContentRequest
    run_started_at: str
    run_finished_at: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    compliance: Optional[ComplianceReport] = None
    approval_decision: Optional[Dict[str, Any]] = None
    intelligence: Optional[Dict[str, Any]] = None
    packaged: Optional[PackagedAsset] = None
    estimated_impact: Optional[Dict[str, Any]] = None

    def to_json(self) -> Dict[str, Any]:
        return _jsonable(asdict(self))


class DraftAgent:
    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def draft(self, request: ContentRequest, strategy: Dict[str, Any]) -> List[DraftAsset]:
        # Multi-variant drafting so the intelligence agent can pick best hooks.
        channel_variants: Dict[str, List[Dict[str, str]]] = {}
        base = request.spec.strip()
        if not base:
            raise ValueError("`spec` must not be empty.")

        hooks = strategy.get("hooks", []) or [
            "What to watch next",
            "The hidden risk",
            "A practical checklist",
        ]

        # Simple, deterministic templates (safe for hackathon demo).
        for channel in request.channels:
            # Create 2 variants per channel.
            vars_for_channel: List[Dict[str, str]] = []
            for i in range(2):
                variant_id = f"{channel}_v{i+1}"
                hook = hooks[(i + len(channel)) % max(1, len(hooks))]
                title = self._title_for_channel(channel, hook)
                body = self._body_for_channel(channel, base, request.audience, i, request.guardrails)
                vars_for_channel.append(
                    {
                        "variant_id": variant_id,
                        "title": title,
                        "body": body,
                    }
                )
            channel_variants[channel] = vars_for_channel

        drafted: List[DraftAsset] = []
        for channel, variants in channel_variants.items():
            for v in variants:
                drafted.append(
                    DraftAsset(
                        channel=channel,
                        variant_id=v["variant_id"],
                        title=v["title"],
                        body=v["body"],
                        metadata={"brand": self.brand_name, "audience": request.audience},
                    )
                )
        return drafted

    def _title_for_channel(self, channel: str, hook: str) -> str:
        if channel == "blog":
            return f"{hook}: A {self.brand_name} guide for {self.brand_name.split()[0]} investors"
        if channel == "linkedin":
            return f"{hook} | Practical takeaways for enterprise content teams"
        if channel == "email":
            return f"{hook} — Quick read for {self.brand_name} audiences"
        return f"{hook} — {self.brand_name}"

    def _body_for_channel(
        self,
        channel: str,
        spec: str,
        audience: str,
        variant_idx: int,
        guardrails: Dict[str, Any],
    ) -> str:
        required = guardrails.get("required_disclaimers", [])
        disclaimers = " ".join(required)
        
        # 1. Try real LLM generation
        prompt = f"Write a professional {channel} post for {audience} about: {spec}. Include the disclaimer at the end: {disclaimers}."
        if variant_idx == 0:
            prompt += " Tone should be calmer and decision-oriented."
        else:
            prompt += " Tone should include a short checklist and a clear next action."
            
        generated_body = generate_text_with_llm(f"[INST] {prompt} [/INST]")
        
        if generated_body:
            return generated_body

        # 2. Fallback to simulated generation
        logger.info(f"Falling back to simulated draft for {channel}")
        if channel == "blog":
            lead = f"Summary for {audience}: {spec}"
            bullets = [
                "Step 1: Convert internal inputs into structured drafts.",
                "Step 2: Run compliance guardrails before anything ships.",
                "Step 3: Localize with consistent terminology.",
                "Step 4: Package per channel and track outcomes.",
            ]
            extra = "Variant note: keep the tone calmer and more decision-oriented." if variant_idx == 0 else "Variant note: add a short checklist and a clear next action."
            return "\n".join(
                [
                    lead,
                    "",
                    extra,
                    "",
                    "\n".join([f"- {b}" for b in bullets]),
                    "",
                    f"Required disclaimer: {disclaimers}",
                ]
            )

        if channel == "linkedin":
            short = "• " + "\n• ".join(
                [
                    "Draft once, adapt per channel.",
                    "Compliance as a first-class stage.",
                    "Localization that preserves meaning.",
                    "Publish with an audit trail.",
                ]
            )
            closing = "If you want faster cycle time without losing trust, start with guardrails + approvals."
            return "\n".join(
                [
                    f"Enterprise content teams: {spec}",
                    "",
                    short,
                    "",
                    closing,
                    "",
                    f"Required disclaimer: {disclaimers}",
                ]
            )

        if channel == "email":
            greeting = f"Hi {audience.split()[0] if audience.split() else 'there'},"
            lines = [
                greeting,
                "",
                f"Here’s a concise workflow for: {spec}",
                "",
                f"1) Draft → 2) Compliance review → 3) Localization → 4) Multi-channel packaging",
                "",
                "Reply with your brand/legal rules and we’ll generate channel-specific versions.",
                "",
                f"Required disclaimer: {disclaimers}",
                "",
                "Regards,",
                f"{self.brand_name} Automation Team",
            ]
            return "\n".join(lines)

        return f"{spec}\n\nRequired disclaimer: {disclaimers}"


class ComplianceAgent:
    def __init__(self, guardrails: Dict[str, Any]):
        self.guardrails = guardrails

    def check(self, assets: List[DraftAsset], threshold: float = 0.85) -> ComplianceReport:
        findings: List[ComplianceFinding] = []
        required = self.guardrails.get("required_disclaimers", [])
        forbidden = self.guardrails.get("forbidden_terms", [])
        tone = self.guardrails.get("tone_constraints", {})

        for asset in assets:
            text = f"{asset.title}\n{asset.body}"
            lower = text.lower()

            # Forbidden terms check.
            for term in forbidden:
                if term.lower() in lower:
                    findings.append(
                        ComplianceFinding(
                            rule_id="forbidden_term",
                            severity="high",
                            message=f"Forbidden term detected: `{term}`",
                            evidence=self._extract_evidence(text, term),
                            suggested_fix=f"Remove or rephrase `{term}` to a non-absolute claim.",
                        )
                    )

            # Required disclaimers check.
            missing = [d for d in required if d not in text]
            if missing:
                # Not every draft needs every disclaimer, but rubric says guardrails must hold.
                # We'll mark missing disclaimers as medium/high depending on count.
                severity = "high" if len(missing) >= 2 else "med"
                findings.append(
                    ComplianceFinding(
                        rule_id="required_disclaimer",
                        severity=severity,
                        message=f"Missing required disclaimer(s): {len(missing)}",
                        evidence=f"Missing: {missing}",
                        suggested_fix="Append the required disclaimers section before publishing.",
                    )
                )

            # Tone checks.
            if tone.get("avoid_excessive_caps"):
                caps_count = sum(1 for w in re.findall(r"[A-Z]{3,}", text))
                if caps_count >= 3:
                    findings.append(
                        ComplianceFinding(
                            rule_id="tone_caps",
                            severity="low",
                            message="Excessive uppercase detected (tone may be too aggressive).",
                            evidence="Multiple all-caps words found.",
                            suggested_fix="Lowercase non-acronym uppercase words; keep emphasis with one sentence-level highlight.",
                        )
                    )

            max_exclamations = int(tone.get("max_exclamation", 3))
            excls = text.count("!")
            if excls > max_exclamations:
                findings.append(
                    ComplianceFinding(
                        rule_id="tone_exclamation",
                        severity="med",
                        message=f"Too many exclamation marks: {excls}",
                        evidence=f"Found {excls} exclamation marks.",
                        suggested_fix="Reduce excitement punctuation; use one exclamation maximum.",
                    )
                )
                
            # LLM Vibe Check
            if hf_client:
                prompt = f"Analyze this text for enterprise brand safety. Is it professional? Answer YES or NO.\nText: {text}"
                vibe = generate_text_with_llm(f"[INST] {prompt} [/INST]", max_new_tokens=10)
                if vibe and "no" in vibe.lower():
                    findings.append(
                        ComplianceFinding(
                            rule_id="llm_vibe_check",
                            severity="med",
                            message="AI detected potential brand safety or tone issues.",
                            evidence="AI Confidence Flag",
                            suggested_fix="Review the text for overly aggressive, unprofessional, or off-brand messaging.",
                        )
                    )

        # Compute overall score: start at 1.0 and penalize by severity.
        score = 1.0
        penalties = {"low": 0.05, "med": 0.12, "high": 0.25}
        for f in findings:
            score -= penalties.get(f.severity, 0.1)

        score = max(0.0, min(1.0, score))
        passed = score >= threshold and all(f.severity != "high" for f in findings)
        return ComplianceReport(
            overall_score=round(score, 3),
            findings=findings,
            passed=passed,
            threshold=threshold,
        )

    def _extract_evidence(self, text: str, term: str) -> str:
        # Return a small snippet around the match.
        idx = text.lower().find(term.lower())
        if idx < 0:
            return ""
        start = max(0, idx - 40)
        end = min(len(text), idx + len(term) + 40)
        return text[start:end].replace("\n", " ")


class LocalizationAgent:
    """
    For demo reliability (no API keys), this agent uses a simulated translation adapter.
    If you add an LLM translation API key later, you can replace the adapter logic.
    """

    def __init__(self, languages: List[str]):
        self.languages = languages
        self.simulated_prefix = {
            "hi": "[HI simulated]",
            "ta": "[TA simulated]",
            "en": "[EN]",
        }

    def localize(self, assets: List[DraftAsset], target_languages: List[str]) -> List[LocalizedAsset]:
        localized: List[LocalizedAsset] = []

        for asset in assets:
            for lang in target_languages:
                prefix = self.simulated_prefix.get(lang, f"[{lang} simulated]")
                title = f"{prefix} {asset.title}"
                body = self._translate_body_simulated(asset.body, lang)
                localized.append(
                    LocalizedAsset(
                        original_variant_id=asset.variant_id,
                        channel=asset.channel,
                        language=lang,
                        title=title,
                        body=body,
                        metadata={"simulation": True},
                    )
                )
        return localized

    def _translate_body_simulated(self, body: str, lang: str) -> str:
        # Replace some headings/phrasing to look "localized" for the demo.
        # Keep it ASCII for portability.
        replacements = {
            "hi": {
                "Summary": "Saransh",
                "Required disclaimer": "Aavashyak disclaimer",
                "Step": "Kadam",
                "Regards,": "Shubhkamnayein,",
            },
            "ta": {
                "Summary": "Surukkam",
                "Required disclaimer": "Avashiya vilakkam",
                "Step": "Padikkattu",
                "Regards,": "Valthukkal,",
            },
        }
        rep = replacements.get(lang, {})
        out = body
        for k, v in rep.items():
            out = out.replace(k, v)
        return out


class PackagingAgent:
    def __init__(self, guardrails: Dict[str, Any]):
        self.guardrails = guardrails

    def package(self, localized_assets: List[LocalizedAsset], channels: List[str]) -> PackagedAsset:
        # In a real system, packaging is per channel requirements.
        # For demo: create publish "batches" containing the best localized variants.
        publish_batches: List[Dict[str, Any]] = []

        for channel in channels:
            lang_variants = [a for a in localized_assets if a.channel == channel]
            # Choose one language per channel in a deterministic way: first language in list.
            if not lang_variants:
                continue
            # group by language
            langs = sorted({a.language for a in lang_variants})
            chosen_lang = langs[0]
            chosen = [a for a in lang_variants if a.language == chosen_lang]
            # choose first (there can be multiple original variants)
            chosen = chosen[:1]

            for a in chosen:
                publish_batches.append(
                    {
                        "channel": channel,
                        "language": a.language,
                        "title": a.title,
                        "body": a.body,
                        "utm_campaign": "content_ops_demo",
                        "scheduled_at": self._schedule_time_utc_offset_hours(2),
                    }
                )

        return PackagedAsset(localized_assets=localized_assets, publish_batches=publish_batches)

    def _schedule_time_utc_offset_hours(self, hours: int) -> str:
        # Return iso time in UTC.
        dt = datetime.now(timezone.utc).replace(microsecond=0)  # stable format
        dt2 = dt.timestamp() + hours * 3600
        return datetime.fromtimestamp(dt2, tz=timezone.utc).isoformat().replace("+00:00", "Z")


class IntelligenceAgent:
    """
    Simulates a feedback loop using heuristic engagement scoring.
    """

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def optimize_strategy(self, request: ContentRequest, drafted: List[DraftAsset]) -> Dict[str, Any]:
        # Choose best hook/title among candidates per channel by a simple scoring heuristic.
        # This is the "content intelligence" demo.
        best_by_channel: Dict[str, Dict[str, Any]] = {}
        for channel in request.channels:
            candidates = [d for d in drafted if d.channel == channel]
            if not candidates:
                continue
            scored: List[Tuple[DraftAsset, float]] = []
            for d in candidates:
                scored.append((d, self._score_title(d.title, d.body)))
            scored.sort(key=lambda x: x[1], reverse=True)
            best, best_score = scored[0]
            best_by_channel[channel] = {
                "best_variant_id": best.variant_id,
                "best_title": best.title,
                "estimated_engagement_score": round(best_score, 3),
            }

        # Provide a "hook list" used by DraftAgent on re-draft (not repeated here).
        hooks = [v["best_title"].split("|")[0].strip() for v in best_by_channel.values() if v.get("best_title")]
        if not hooks:
            hooks = ["What to watch next", "The hidden risk", "A practical checklist"]
        return {"best_by_channel": best_by_channel, "hooks": hooks}

    def _score_title(self, title: str, body: str) -> float:
        t = (title + " " + body).lower()
        score = 0.0
        # Engagement heuristics
        for kw, w in [
            ("watch", 0.25),
            ("checklist", 0.22),
            ("practical", 0.18),
            ("guide", 0.16),
            ("enterprise", 0.1),
        ]:
            if kw in t:
                score += w
        # slight randomness for demo variety
        score += self.rng.uniform(0, 0.15)
        return score


def ensure_required_disclaimers_present(body: str, guardrails: Dict[str, Any]) -> str:
    required = guardrails.get("required_disclaimers", [])
    missing = [d for d in required if d not in body]
    if not missing:
        return body
    return body + "\n\n" + " ".join([f"Required disclaimer: {d}" for d in missing])


def _default_strategy() -> Dict[str, Any]:
    return {"hooks": ["What to watch next", "The hidden risk", "A practical checklist"]}


class ContentOpsWorkflow:
    def __init__(self, output_dir: str = "runs"):
        self.output_dir = output_dir

    def draft_assets(self, request: ContentRequest, strategy: Optional[Dict[str, Any]] = None) -> Tuple[List[DraftAsset], Dict[str, Any]]:
        """
        Draft content assets only (no compliance gate).
        Useful for previewing in UIs with human approval gates.
        """
        draft_agent = DraftAgent(brand_name=request.guardrails.get("brand_name", "ET"))
        _strategy = strategy or _default_strategy()
        drafted_assets = draft_agent.draft(request, strategy=_strategy)
        return drafted_assets, _strategy

    def compliance_check(
        self,
        request: ContentRequest,
        drafted_assets: List[DraftAsset],
        compliance_threshold: float = 0.85,
    ) -> ComplianceReport:
        """
        Run compliance guardrails on drafted assets only.
        """
        # Enforce disclaimers before checking (guardrail requirement).
        for a in drafted_assets:
            a.body = ensure_required_disclaimers_present(a.body, request.guardrails)
        compliance_agent = ComplianceAgent(request.guardrails)
        return compliance_agent.check(drafted_assets, threshold=compliance_threshold)

    def preview_draft_and_compliance(
        self,
        request: ContentRequest,
        compliance_threshold: float = 0.85,
    ) -> Tuple[List[DraftAsset], ComplianceReport, Dict[str, Any]]:
        drafted_assets, strategy = self.draft_assets(request)
        report = self.compliance_check(request, drafted_assets, compliance_threshold=compliance_threshold)
        return drafted_assets, report, strategy

    def run(
        self,
        request: ContentRequest,
        approval_callback: Optional[
            Callable[[Dict[str, Any], ComplianceReport], Dict[str, Any]]
        ] = None,
        compliance_threshold: float = 0.85,
        auto_approve: bool = False,
    ) -> WorkflowRun:
        run = WorkflowRun(
            job_id=request.job_id,
            request=request,
            run_started_at=_utc_now_iso(),
        )
        os.makedirs(self.output_dir, exist_ok=True)
        run_dir = os.path.join(self.output_dir, request.job_id)
        os.makedirs(run_dir, exist_ok=True)

        def record_step(step: WorkflowStep) -> None:
            run.steps.append(step)
            run.audit_log.append(
                {
                    "timestamp": step.started_at,
                    "agent": step.agent,
                    "step": step.name,
                    "duration_ms": step.duration_ms,
                    "summary": step.summary,
                    "raw_output": step.raw_output,
                }
            )

        # --- Draft ---
        draft_agent = DraftAgent(brand_name=request.guardrails.get("brand_name", "ET"))
        t0 = time.time()
        drafted_assets: List[DraftAsset] = []
        step_started = _utc_now_iso()
        strategy = _default_strategy()
        drafted_assets = draft_agent.draft(request, strategy=strategy)
        step_finished = _utc_now_iso()
        record_step(
            WorkflowStep(
                name="draft",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((time.time() - t0) * 1000),
                agent="DraftAgent",
                summary=f"Drafted {len(drafted_assets)} assets across {len(request.channels)} channels.",
                raw_output={"strategy": strategy, "assets": [asdict(a) for a in drafted_assets]},
            )
        )

        # --- Compliance ---
        # Ensure disclaimers are present pre-check (agent guardrail enforcement).
        for a in drafted_assets:
            a.body = ensure_required_disclaimers_present(a.body, request.guardrails)

        compliance_agent = ComplianceAgent(request.guardrails)
        t1 = time.time()
        step_started = _utc_now_iso()
        compliance_report = compliance_agent.check(drafted_assets, threshold=compliance_threshold)
        step_finished = _utc_now_iso()
        run.compliance = compliance_report
        record_step(
            WorkflowStep(
                name="compliance_check",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((time.time() - t1) * 1000),
                agent="ComplianceAgent",
                summary=(
                    f"Compliance score={compliance_report.overall_score} passed={compliance_report.passed} "
                    f"(threshold={compliance_report.threshold}). Findings={len(compliance_report.findings)}"
                ),
                raw_output={
                    "report": _jsonable(asdict(compliance_report)),
                },
            )
        )

        # Human-in-the-loop gate
        stage_mode = "auto" if (auto_approve or request.human_auto_approval) else "manual"
        if stage_mode == "auto":
            approval_decision = {"approved": bool(compliance_report.passed), "mode": "auto"}
        else:
            if approval_callback is None:
                # Fallback: reject if not passed, else approve.
                approval_decision = {"approved": bool(compliance_report.passed), "mode": "fallback"}
            else:
                approval_decision = approval_callback(
                    {"draft_assets": [asdict(a) for a in drafted_assets]},
                    compliance_report,
                )

        run.approval_decision = approval_decision
        record_step(
            WorkflowStep(
                name="approval_gate",
                started_at=_utc_now_iso(),
                finished_at=_utc_now_iso(),
                duration_ms=1,
                agent="HumanGate",
                summary=f"Human decision: {approval_decision.get('approved')} (mode={approval_decision.get('mode')}).",
                raw_output={"decision": approval_decision},
            )
        )

        if not approval_decision.get("approved", False):
            # Reroute logic: ask for feedback and re-draft once.
            human_feedback = approval_decision.get("human_feedback", "").strip()
            if human_feedback:
                request2 = ContentRequest(
                    spec=request.spec + "\n\nHUMAN_FEEDBACK: " + human_feedback,
                    audience=request.audience,
                    channels=request.channels,
                    languages=request.languages,
                    guardrails=request.guardrails,
                    job_id=request.job_id,
                    strategy_objective=request.strategy_objective,
                    human_auto_approval=True,
                )
                # Run a one-time re-draft and re-check compliance.
                return self.run(
                    request2,
                    approval_callback=None,
                    compliance_threshold=compliance_threshold,
                    auto_approve=True,
                )

            # If no feedback provided, fail the run gracefully.
            run.run_finished_at = _utc_now_iso()
            self._write_run_json(run_dir, run)
            return run

        # --- Intelligence (content strategy adjustment) ---
        t2 = time.time()
        step_started = _utc_now_iso()
        intelligence = IntelligenceAgent().optimize_strategy(request, drafted_assets)
        step_finished = _utc_now_iso()
        run.intelligence = intelligence
        record_step(
            WorkflowStep(
                name="content_intelligence",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((time.time() - t2) * 1000),
                agent="IntelligenceAgent",
                summary="Simulated engagement optimization by selecting best hooks per channel.",
                raw_output=_jsonable(intelligence),
            )
        )

        # --- Localization ---
        t3 = time.time()
        step_started = _utc_now_iso()
        localizer = LocalizationAgent(languages=request.languages)
        localized_assets = localizer.localize(drafted_assets, request.languages)
        step_finished = _utc_now_iso()
        record_step(
            WorkflowStep(
                name="localization",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((time.time() - t3) * 1000),
                agent="LocalizationAgent",
                summary=f"Localized to languages={request.languages}. Produced {len(localized_assets)} variants.",
                raw_output={"localized_assets": [asdict(a) for a in localized_assets]},
            )
        )

        # --- Packaging + Scheduler ---
        t4 = time.time()
        step_started = _utc_now_iso()
        packager = PackagingAgent(request.guardrails)
        packaged = packager.package(localized_assets, request.channels)
        step_finished = _utc_now_iso()
        run.packaged = packaged
        record_step(
            WorkflowStep(
                name="packaging",
                started_at=step_started,
                finished_at=step_finished,
                duration_ms=int((time.time() - t4) * 1000),
                agent="PackagingAgent",
                summary=f"Prepared publish batches={len(packaged.publish_batches)} for channels={request.channels}.",
                raw_output={"publish_batches": packaged.publish_batches},
            )
        )

        # --- Estimated impact ---
        estimated_impact = self._estimate_impact(request, run.compliance)
        run.estimated_impact = estimated_impact
        record_step(
            WorkflowStep(
                name="impact_model",
                started_at=_utc_now_iso(),
                finished_at=_utc_now_iso(),
                duration_ms=1,
                agent="ImpactModel",
                summary="Computed time saved and rework reduction estimates (assumptions stated).",
                raw_output=_jsonable(estimated_impact),
            )
        )

        run.run_finished_at = _utc_now_iso()
        self._write_run_json(run_dir, run)
        self._write_artifacts(run_dir, drafted_assets, localized_assets, packaged)
        return run

    def _estimate_impact(self, request: ContentRequest, compliance: Optional[ComplianceReport]) -> Dict[str, Any]:
        # Baseline assumptions: per asset manual lifecycle (hours).
        # You can tweak these in the README depending on your pitch.
        manual_hours_per_asset = 6.75
        assets_count = len(request.channels) * 2  # DraftAgent creates 2 variants/channel.

        # Automation effect targets:
        draft_time_saved = 0.40
        compliance_rework_reduction = 0.30
        localization_time_saved = 0.55
        packaging_time_saved = 0.20

        compliance_score = compliance.overall_score if compliance else 0.5
        compliance_multiplier = min(1.0, 0.6 + compliance_score * 0.4)  # higher score => more savings

        # Weighted time savings estimate
        automated_hours_per_asset = manual_hours_per_asset * (1 - draft_time_saved) * (1 - compliance_rework_reduction * compliance_multiplier)
        automated_hours_per_asset *= (1 - localization_time_saved)
        automated_hours_per_asset *= (1 - packaging_time_saved)

        estimated_manual_total = manual_hours_per_asset * assets_count
        estimated_automated_total = automated_hours_per_asset * assets_count
        time_saved_hours = max(0.0, estimated_manual_total - estimated_automated_total)

        # Rework estimate from compliance pass/fail.
        rework_reduction = 0.2 + (0.2 if compliance and compliance.passed else 0.0)

        return {
            "assumptions": {
                "manual_hours_per_asset": manual_hours_per_asset,
                "assets_count": assets_count,
                "draft_time_saved": draft_time_saved,
                "compliance_rework_reduction": compliance_rework_reduction,
                "localization_time_saved": localization_time_saved,
                "packaging_time_saved": packaging_time_saved,
            },
            "estimated_manual_total_hours": round(estimated_manual_total, 2),
            "estimated_automated_total_hours": round(estimated_automated_total, 2),
            "time_saved_hours": round(time_saved_hours, 2),
            "estimated_rework_reduction": round(rework_reduction, 2),
            "compliance_score": compliance.overall_score if compliance else None,
        }

    def _write_run_json(self, run_dir: str, run: WorkflowRun) -> None:
        path = os.path.join(run_dir, "workflow_run.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run.to_json(), f, indent=2)

    def _write_artifacts(
        self,
        run_dir: str,
        drafted_assets: List[DraftAsset],
        localized_assets: List[LocalizedAsset],
        packaged: PackagedAsset,
    ) -> None:
        # Drafts
        os.makedirs(os.path.join(run_dir, "drafts"), exist_ok=True)
        for a in drafted_assets:
            path = os.path.join(run_dir, "drafts", f"{a.channel}_{a.variant_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(a), f, indent=2, ensure_ascii=False)

        # Localized
        os.makedirs(os.path.join(run_dir, "localized"), exist_ok=True)
        for a in localized_assets:
            path = os.path.join(run_dir, "localized", f"{a.channel}_{a.language}_{a.original_variant_id}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(a), f, indent=2, ensure_ascii=False)

        # Packaging/publish payloads
        os.makedirs(os.path.join(run_dir, "packaged"), exist_ok=True)
        with open(os.path.join(run_dir, "packaged", "publish_batches.json"), "w", encoding="utf-8") as f:
            json.dump(packaged.publish_batches, f, indent=2, ensure_ascii=False)


def default_request_from_minimal(spec: str) -> ContentRequest:
    return ContentRequest(
        spec=spec,
        audience="enterprise content managers and brand/legal teams",
        channels=CHANNELS_DEFAULT,
        languages=DEFAULT_LANGUAGES,
    )


