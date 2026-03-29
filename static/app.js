let currentJobId = null;

// DOM Elements
const form = document.getElementById('content-form');
const generateBtn = document.getElementById('generate-btn');
const genSpinner = document.getElementById('gen-spinner');
const genError = document.getElementById('gen-error');

const placeholder = document.getElementById('placeholder-area');
const resultsArea = document.getElementById('results-area');

const compScore = document.getElementById('comp-score');
const compStatus = document.getElementById('comp-status');
const findingsContainer = document.getElementById('findings-container');

const tabsContainer = document.getElementById('channel-tabs');
const draftsContent = document.getElementById('drafts-content');

const radioDecision = document.getElementsByName('decision');
const feedbackGroup = document.getElementById('feedback-group');
const workflowRunBtn = document.getElementById('workflow-run-btn');

const finalResults = document.getElementById('final-results');
const publishBatches = document.getElementById('publish-batches');
const impactContainer = document.getElementById('impact-container');

// Form Submit -> Generate Drafts
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError();
    setLoading(true);

    const spec = document.getElementById('spec').value;
    const audience = document.getElementById('audience').value;
    const thresh = parseFloat(document.getElementById('compliance').value);

    // Get checked checkboxes
    const channels = Array.from(document.querySelectorAll('input[name="channels"]:checked')).map(cb => cb.value);
    const languages = Array.from(document.querySelectorAll('input[name="languages"]:checked')).map(cb => cb.value);

    if (channels.length === 0 || languages.length === 0) {
        showError("Please select at least one channel and one language.");
        setLoading(false);
        return;
    }

    try {
        const res = await fetch('/api/preview', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                spec, audience, channels, languages, compliance_threshold: thresh
            })
        });

        if (!res.ok) throw new Error("Server error computing drafts");
        const data = await res.json();
        
        currentJobId = data.job_id;
        renderPreview(data);
        showToast("Drafts & Compliance Report generated successfully");

    } catch (err) {
        showError(err.message);
    } finally {
        setLoading(false);
    }
});

function renderPreview(data) {
    placeholder.style.display = 'none';
    resultsArea.style.display = 'block';
    finalResults.style.display = 'none';

    // 1. Compliance
    const rep = data.compliance_report;
    compScore.innerText = rep.overall_score.toFixed(3);
    compStatus.innerText = rep.passed ? 'PASSED' : 'FAILED';
    compStatus.className = 'badge ' + (rep.passed ? 'pass' : 'fail');

    findingsContainer.innerHTML = '';
    if (rep.findings.length === 0) {
        findingsContainer.innerHTML = '<div class="finding-item low"><div class="finding-title">No issues found</div><div class="finding-desc">The content adheres to all guardrails.</div></div>';
    } else {
        rep.findings.forEach(f => {
            findingsContainer.innerHTML += `
                <div class="finding-item ${f.severity}">
                    <div class="finding-title">[${f.severity.toUpperCase()}] ${f.rule_id}</div>
                    <div class="finding-desc">${f.message}</div>
                    ${f.suggested_fix ? `<div class="finding-desc" style="margin-top:4px; color:#38bdf8;">Fix: ${f.suggested_fix}</div>` : ''}
                </div>
            `;
        });
    }

    // 2. Drafts
    tabsContainer.innerHTML = '';
    draftsContent.innerHTML = '';
    
    // Group by channel
    const byChannel = {};
    data.drafted_assets.forEach(a => {
        if(!byChannel[a.channel]) byChannel[a.channel] = [];
        byChannel[a.channel].push(a);
    });

    let first = true;
    for (const [ch, assets] of Object.entries(byChannel)) {
        // Tab
        const btn = document.createElement('button');
        btn.className = `tab-btn ${first ? 'active' : ''}`;
        btn.innerText = ch.toUpperCase();
        btn.onclick = () => showTab(ch);
        tabsContainer.appendChild(btn);

        // Content
        const contentDiv = document.createElement('div');
        contentDiv.id = `tab-content-${ch}`;
        contentDiv.style.display = first ? 'block' : 'none';
        
        assets.forEach(a => {
            const rawBody = a.metadata?.simulation ? a.body : a.body;
            let renderedHtml;
            try {
                renderedHtml = typeof marked !== 'undefined' ? marked.parse(rawBody) : `<pre>${rawBody}</pre>`;
            } catch (e) {
                renderedHtml = `<pre>${rawBody}</pre>`;
            }

            contentDiv.innerHTML += `
                <div class="draft-box">
                    <h4>${a.variant_id}: ${a.title}</h4>
                    <div class="md-content">${renderedHtml}</div>
                </div>
            `;
        });
        draftsContent.appendChild(contentDiv);
        first = false;
    }
}

function showTab(channel) {
    document.querySelectorAll('.tab-btn').forEach(b => {
        if(b.innerText.toLowerCase() === channel.toLowerCase()) b.classList.add('active');
        else b.classList.remove('active');
    });
    const children = draftsContent.children;
    for(let i=0; i<children.length; i++){
        if(children[i].id === `tab-content-${channel}`) children[i].style.display = 'block';
        else children[i].style.display = 'none';
    }
}

// Toggle feedback textarea
for (let i = 0; i < radioDecision.length; i++) {
    radioDecision[i].addEventListener('change', function() {
        if (this.value === 'Request edits') {
            feedbackGroup.style.display = 'block';
        } else {
            feedbackGroup.style.display = 'none';
        }
    });
}

// Workflow Run
workflowRunBtn.addEventListener('click', async () => {
    if (!currentJobId) return;
    
    const decision = document.querySelector('input[name="decision"]:checked').value;
    const feedback = document.getElementById('human-feedback').value;

    if (decision === 'Request edits' && !feedback.trim()) {
        showToast("Please provide edit notes", "error");
        return;
    }

    const runSpinner = document.getElementById('run-spinner');
    runSpinner.classList.remove('hidden');
    workflowRunBtn.disabled = true;

    try {
        const res = await fetch('/api/approve', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                job_id: currentJobId,
                decision: decision,
                human_feedback: feedback
            })
        });
        const data = await res.json();
        
        if (data.updated) {
            // Edits requested, preview redrawn
            currentJobId = data.job_id;
            renderPreview(data);
            showToast("Drafts regenerated based on feedback");
        } else {
            // Full workflow finished
            showToast("Publish workflow executed successfully!");
            renderFinalResults(data);
        }

    } catch (err) {
        showToast(err.message, "error");
    } finally {
        runSpinner.classList.add('hidden');
        workflowRunBtn.disabled = false;
    }
});

function renderFinalResults(runData) {
    document.getElementById('action-area').style.display = 'none';
    finalResults.style.display = 'block';

    // Batches
    publishBatches.innerHTML = '';
    if (runData.packaged && runData.packaged.publish_batches) {
        runData.packaged.publish_batches.forEach(b => {
             publishBatches.innerHTML += `
             <div class="draft-box">
                <div style="display:flex; justify-content:space-between; margin-bottom: 10px;">
                    <span class="badge pass">${b.channel.toUpperCase()} (${b.language.toUpperCase()})</span>
                    <span style="color:var(--text-muted); font-size:0.8rem;">${b.scheduled_at}</span>
                </div>
                <div style="font-weight:600; margin-bottom:8px;">${b.title}</div>
                <pre style="font-size:0.8rem; color:var(--text-muted);">${b.body.substring(0, 100)}...</pre>
             </div>
             `;
        });
    }

    // Impact
    if (runData.estimated_impact) {
        const imp = runData.estimated_impact;
        const totalSavings = imp.weighted_automated_hours.toFixed(1);
        impactContainer.innerHTML = `
            <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--panel-border); border-radius: 8px; padding: 20px;">
                <div style="display:flex; justify-content:space-between; margin-bottom: 15px; border-bottom: 1px solid var(--panel-border); padding-bottom: 10px;">
                    <span>Assets Generated:</span>
                    <span style="font-weight:bold">${imp.assets_generated}</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom: 15px;">
                    <span>Manual Time:</span>
                    <span style="color:var(--danger)">${imp.baseline_manual_hours.toFixed(1)} hrs</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom: 15px;">
                    <span>Automated Time:</span>
                    <span style="color:var(--success); font-weight:bold">${totalSavings} hrs</span>
                </div>
                 <div style="display:flex; justify-content:space-between; margin-bottom: 15px;">
                    <span>Compliance Rework Reduction:</span>
                    <span style="color:var(--primary); font-weight:bold">${(imp.compliance_rework_reduction_pct * 100).toFixed(0)}%</span>
                </div>
            </div>
        `;
    }
}

// Utils
function setLoading(isLoad) {
    if (isLoad) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = `<span class="spinner" id="gen-spinner"></span> Initiating AI Pipeline...`;
    } else {
        generateBtn.disabled = false;
        generateBtn.innerHTML = `<span class="spinner hidden" id="gen-spinner"></span> Generate Drafts & Report`;
    }
}

function showError(msg) {
    genError.innerText = msg;
    genError.classList.remove('hidden');
}

function hideError() {
    genError.classList.add('hidden');
}

function showToast(msg, type="success") {
    const t = document.createElement('div');
    t.className = 'toast';
    t.innerHTML = `<span style="color: ${type === 'success' ? 'var(--success)' : 'var(--danger)'}">•</span> ${msg}`;
    document.getElementById('toast-container').appendChild(t);
    setTimeout(() => t.remove(), 4000);
}
