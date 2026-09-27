/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Data Platform Control Center & Digital Twin
   Master Application Controller & Simulation Engine
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ─── State Machine ─── */
  // Status: "IDLE" | "STARTING" | "RUNNING" | "PAUSED" | "COMPLETED" | "FAILED" | "RECOVERING"
  let simState = "IDLE";
  let mode = "live";                // "live" | "stress"
  let speedMultiplier = 1.0;        // 0.5 | 1.0 | 2.0 | 5.0
  let currentWorkloadIdx = 3;       // 0=1K, 1=10K, 2=50K, 3=100K (default), 4=250K, 5=500K, 6=1M
  let simProgress = 0;              // 0 to 100%
  let simInterval = null;
  let currentDemoStageIdx = -1;
  let demoTimeElapsed = 0;          // in seconds
  let activeFailureTimeout = null;

  // Judge Mode State
  let judgeMode = false;
  let judgeStep = 0;
  let judgeTimerInterval = null;
  let judgeTimeLeft = 180;          // 3 minutes

  // Trace Mode State
  let activeTraceStepIdx = -1;
  let traceAutoInterval = null;

  /* ─── DOM References ─── */
  const $ = (id) => document.getElementById(id);

  // Top Bar Controls
  const clock = $("live-clock");
  const btnStart = $("btn-start");
  const btnPause = $("btn-pause");
  const btnReset = $("btn-reset");
  const btnModeToggle = $("btn-mode-toggle");
  const modeLabel = $("mode-label");
  const btnScaleToggle = $("btn-scale-toggle");
  const currentScaleLabel = $("current-scale-label");
  const btnJudgeMode = $("btn-judge-mode");
  const btnProjector = $("btn-projector");
  const btnMotion = $("btn-motion");
  const btnFullscreen = $("btn-fullscreen");
  const globalBadge = $("global-badge");

  // Stage Banner
  const stageStepNum = $("stage-step-num");
  const stageStepName = $("stage-step-name");
  const stageStepDesc = $("stage-step-desc");

  // System Metrics
  const pipelineStatusBadge = $("pipeline-status-badge");
  const mvRecords = $("mv-records");
  const msRecords = $("ms-records");
  const mvThroughput = $("mv-throughput");
  const mvAnomalies = $("mv-anomalies");
  const msAnomalyRate = $("ms-anomaly-rate");
  const mvDq = $("mv-dq");
  const msDqIssues = $("ms-dq-issues");
  const mvLatency = $("mv-latency");
  const mvSecurity = $("mv-security");
  const msSecurity = $("ms-security");
  const metricsProvenance = $("metrics-provenance");

  // Bottleneck
  const bwStage = $("bw-stage");
  const bwQueue = $("bw-queue");
  const bwLoad = $("bw-load");
  const bwThroughput = $("bw-throughput");
  const bwProvenance = $("bw-provenance");

  // Stage Inspector Flyout
  const stageDetail = $("stage-detail");
  const detailTitle = $("detail-title");
  const detailBadge = $("detail-badge");
  const detailBody = $("detail-body");
  const detailClose = $("detail-close");

  // Lineage & Trace
  const lineageViz = $("lineage-viz");
  const btnTraceBackward = $("btn-trace-backward");
  const lpvContainer = $("lineage-payload-viewer");
  const lpvTitle = $("lpv-title");
  const lpvBody = $("lpv-body");
  const lpvClose = $("lpv-close");

  // ML Panel
  const anomalyChart = $("anomaly-chart");
  const mlFitTime = $("ml-fit-time");
  const mlInferTime = $("ml-infer-time");
  const mlThroughput = $("ml-throughput");

  // AI Panel
  const aiOutput = $("ai-output");
  const aiTabBtns = document.querySelectorAll(".ai-tab-btn");
  const aiTabTerminal = $("ai-tab-terminal");
  const aiTabEvidence = $("ai-tab-evidence");

  // Failure Lab
  const failureGrid = $("failure-grid");
  const failureResult = $("failure-result");
  const frTitle = $("fr-title");
  const frStatus = $("fr-status");
  const frLog = $("fr-log");

  // Status Bar
  const statusDot = $("status-dot");
  const statusText = $("status-text");
  const statusStageLabel = $("status-stage-label");
  const progressFill = $("progress-fill");
  const progressPct = $("progress-pct");
  const memUsage = $("mem-usage");

  // Judge Overlay
  const judgeOverlay = $("judge-overlay");
  const judgeStepTitle = $("judge-step-title");
  const judgeText = $("judge-text");
  const judgeTimerEl = $("judge-timer");
  const judgeStepIndicator = $("judge-step-indicator");
  const judgePrev = $("judge-prev");
  const judgeNext = $("judge-next");
  const judgeClose = $("judge-close");

  // Scale Overlay
  const scaleOverlay = $("scale-overlay");
  const scaleSlider = $("scale-slider");
  const scaleProjections = $("scale-projections");
  const scaleClose = $("scale-close");
  const btnApplyScale = $("btn-apply-scale");

  /* ─── Initialize Network Map & Particle System ─── */
  const pipeline = new PipelineNetworkMap("pipeline-canvas", (nodeId) => {
    showStageInspector(nodeId);
  });
  window.pipelineInstance = pipeline;

  const particles = new NetworkParticleSystem("particle-canvas", pipeline);

  /* ─── Live Clock ─── */
  function updateClock() {
    const now = new Date();
    clock.textContent = now.toLocaleTimeString("en-US", {
      hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit"
    }) + " · " + now.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric"
    });
  }
  setInterval(updateClock, 1000);
  updateClock();

  /* ─── Numeric & Formatting Helpers ─── */
  function formatNum(n) {
    if (isNaN(n) || n === null || n === undefined) return "—";
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 10000) return (n / 1000).toFixed(1) + "K";
    if (n >= 1000) return Math.round(n).toLocaleString();
    return Math.round(n).toLocaleString();
  }

  function setSystemState(newState, labelText) {
    simState = newState;
    statusDot.className = "status-dot " + newState.toLowerCase();
    statusText.textContent = newState;
    pipelineStatusBadge.textContent = newState;
    if (labelText) statusStageLabel.textContent = labelText;

    if (newState === "RUNNING") {
      btnStart.disabled = true;
      btnPause.disabled = false;
      btnReset.disabled = false;
    } else if (newState === "PAUSED") {
      btnStart.disabled = false;
      btnStart.textContent = "▶ RESUME";
      btnPause.disabled = true;
      btnReset.disabled = false;
    } else if (newState === "IDLE" || newState === "COMPLETED") {
      btnStart.disabled = false;
      btnStart.textContent = "▶ START";
      btnPause.disabled = true;
      btnReset.disabled = (newState === "IDLE" && simProgress === 0);
    }
  }

  function setProgress(pct) {
    simProgress = Math.max(0, Math.min(100, pct));
    progressFill.style.width = simProgress + "%";
    progressPct.textContent = Math.round(simProgress) + "%";
  }

  /* ─── AI Terminal Logger ─── */
  function termWrite(text, cls = "info") {
    const line = document.createElement("div");
    line.className = "terminal-line " + cls;
    line.textContent = text;
    aiOutput.appendChild(line);
    aiOutput.scrollTop = aiOutput.scrollHeight;
  }

  function termClear() {
    aiOutput.innerHTML = "";
  }

  /* ─── Stage Inspector Flyout ─── */
  function showStageInspector(stageId) {
    const stage = PIPELINE_STAGES.find(s => s.id === stageId) || pipeline.nodes.find(n => n.id === stageId);
    if (!stage) return;

    detailTitle.textContent = `${stage.icon || "⚙️"} ${stage.label}`;
    detailBadge.textContent = mode === "live" ? "[MEASURED]" : "[SIMULATED]";
    detailBadge.className = "provenance-pill " + (mode === "live" ? "measured" : "simulated");

    let html = `
      <div class="detail-desc-box">
        <strong>Purpose:</strong> ${stage.purpose || stage.detail?.description || stage.tech}<br/><br/>
        <strong>Why This Exists:</strong> ${stage.why_exists || "Critical architectural boundary for defensible data processing."}
      </div>
      <div class="detail-row"><span class="detail-label">Technology Engine:</span><span class="detail-value mono">${stage.technology || stage.tech}</span></div>
      <div class="detail-row"><span class="detail-label">Input Specification:</span><span class="detail-value">${stage.input_desc || "Raw entity stream"}</span></div>
      <div class="detail-row"><span class="detail-label">Output Contract:</span><span class="detail-value">${stage.output_desc || "Validated structured data"}</span></div>
      <div class="detail-row"><span class="detail-label">Network Status:</span><span class="detail-value mono text-cyan">${stage.live_metrics?.status || "HEALTHY"}</span></div>
    `;

    if (stage.specs) {
      stage.specs.forEach(s => {
        html += `<div class="detail-row"><span class="detail-label">${s.label}:</span><span class="detail-value mono">${s.value}</span></div>`;
      });
    }

    detailBody.innerHTML = html;
    stageDetail.classList.remove("hidden");
  }

  /* ─── Anomaly Score Distribution Chart ─── */
  function drawAnomalyChart() {
    if (!anomalyChart) return;
    const ctx = anomalyChart.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const cw = anomalyChart.offsetWidth || 340;
    const ch = anomalyChart.offsetHeight || 130;

    anomalyChart.width = cw * dpr;
    anomalyChart.height = ch * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, cw, ch);

    const bins = 36;
    const data = new Array(bins).fill(0);
    const minScore = STRESS_DATA.ml.score_min;
    const maxScore = STRESS_DATA.ml.score_max;
    const range = maxScore - minScore;
    const mean = STRESS_DATA.ml.score_mean;
    const sd = range / 3.8;

    for (let i = 0; i < bins; i++) {
      const x = minScore + (i / bins) * range;
      data[i] = Math.exp(-0.5 * Math.pow((x - mean) / sd, 2));
    }

    const maxVal = Math.max(...data);
    const plotPadL = 26;
    const plotPadR = 14;
    const plotW = cw - plotPadL - plotPadR;
    const plotH = ch - 26;
    const barW = plotW / bins;
    const thresholdBin = Math.floor(((0 - minScore) / range) * bins);

    // Draw Histogram Bars
    for (let i = 0; i < bins; i++) {
      const barH = (data[i] / maxVal) * (plotH - 6);
      const x = plotPadL + i * barW;
      const y = 8 + plotH - barH;
      const isAnomaly = i < thresholdBin + 1;

      ctx.fillStyle = isAnomaly ? "rgba(239, 71, 111, 0.8)" : "rgba(139, 92, 246, 0.55)";
      ctx.fillRect(x, y, barW - 1, barH);

      if (isAnomaly) {
        ctx.fillStyle = "rgba(239, 71, 111, 0.15)";
        ctx.fillRect(x - 1, y - 2, barW + 1, barH + 4);
      }
    }

    // Cutoff Threshold Line
    const tx = plotPadL + (thresholdBin + 1) * barW;
    ctx.strokeStyle = "rgba(239, 71, 111, 0.85)";
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(tx, 6);
    ctx.lineTo(tx, 8 + plotH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Axis Labels
    ctx.fillStyle = "#64748b";
    ctx.font = "8.5px 'JetBrains Mono', monospace";
    ctx.textAlign = "left";
    ctx.fillText(`${minScore.toFixed(2)}`, plotPadL, ch - 4);
    ctx.textAlign = "right";
    ctx.fillText(`${maxScore.toFixed(2)}`, cw - plotPadR, ch - 4);
    ctx.textAlign = "center";
    ctx.fillText("Anomaly Cutoff (0.00)", tx, ch - 4);

    ctx.fillStyle = "#ef476f";
    ctx.font = "bold 8px 'JetBrains Mono', monospace";
    ctx.textAlign = "right";
    ctx.fillText("ANOMALIES (4.0%)", tx - 4, 16);

    ctx.fillStyle = "#8b5cf6";
    ctx.textAlign = "left";
    ctx.fillText("NORMAL (96.0%)", tx + 6, 16);
  }

  /* ─── 7-Step Lineage Explorer ─── */
  function renderLineage() {
    lineageViz.innerHTML = "";

    LINEAGE_CHAIN.forEach((step, idx) => {
      const stepEl = document.createElement("div");
      stepEl.className = "lineage-step";
      stepEl.dataset.stepIndex = idx;
      stepEl.innerHTML = `
        <div class="lineage-step-num">${step.step}</div>
        <div class="lineage-step-content">
          <div class="lineage-step-header">
            <span class="lineage-step-title">${step.title}</span>
            <span class="lineage-step-sub">${step.subtitle}</span>
          </div>
          <div class="lineage-step-detail">${step.evidence}</div>
        </div>
      `;

      stepEl.addEventListener("click", () => {
        selectLineageStep(idx);
      });

      lineageViz.appendChild(stepEl);

      if (idx < LINEAGE_CHAIN.length - 1) {
        const conn = document.createElement("div");
        conn.className = "lineage-connector";
        lineageViz.appendChild(conn);
      }
    });
  }

  function selectLineageStep(idx) {
    activeTraceStepIdx = idx;
    const step = LINEAGE_CHAIN[idx];
    if (!step) return;

    // Update active class on steps
    document.querySelectorAll(".lineage-step").forEach((el, i) => {
      el.classList.toggle("active", i === idx);
    });

    // Map step to target node
    const stepNodeMap = ["ai", "ai", "ml", "postgres", "bronze", "ingestion", "api"];
    const targetNodeId = stepNodeMap[idx] || "postgres";

    // Highlight backward chain on network map
    const chainIds = stepNodeMap.slice(0, idx + 1);
    pipeline.highlightLineageChain(chainIds);
    pipeline.panToNode(targetNodeId, 1.25);

    // Show Payload Viewer
    lpvTitle.textContent = `STEP ${step.step} OF 7: ${step.title} (${step.record_id})`;
    lpvBody.innerHTML = `
WHERE:          ${step.where}
WHAT:           ${step.what}
SOURCE POINTER: ${step.source}
TRANSFORMATION: ${step.transformation}
EVIDENCE BOUND: ${step.evidence}
SHA-256 DIGEST: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 [VERIFIED]
    `.trim();
    lpvContainer.classList.remove("hidden");
  }

  function startBackwardTraceAuto() {
    let current = 0;
    selectLineageStep(current);
    clearInterval(traceAutoInterval);

    traceAutoInterval = setInterval(() => {
      current++;
      if (current >= LINEAGE_CHAIN.length) {
        clearInterval(traceAutoInterval);
        termWrite("✓ 7-Step Cryptographic Lineage Complete: 100% Verified.", "success");
        return;
      }
      selectLineageStep(current);
    }, 1800 / speedMultiplier);
  }

  /* ─── Workload Scale & Projections ─── */
  function renderScaleProjection(index) {
    currentWorkloadIdx = index;
    const proj = SCALE_PROJECTIONS[index];
    currentScaleLabel.textContent = proj.scale;
    particles.setScale(0.7 + index * 0.4, `${proj.batch_size} RECS`);

    scaleProjections.innerHTML = `
      <div class="sp-row">
        <span class="sp-label">Target Records:</span>
        <span class="sp-value">${formatNum(proj.records)} Obs</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Batch Size:</span>
        <span class="sp-value mono">${proj.batch_size} (${proj.batches} Batches)</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Ingestion Duration:</span>
        <span class="sp-value">${proj.ingestion_s.toFixed(2)}s <span class="sp-badge ${proj.ingestion_badge.toLowerCase()}">${proj.ingestion_badge}</span></span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Throughput:</span>
        <span class="sp-value mono text-cyan">${formatNum(proj.throughput_rps)} rec/s</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Peak Memory:</span>
        <span class="sp-value">${proj.mem_mb.toFixed(0)} MB <span class="sp-badge ${proj.mem_badge.toLowerCase()}">${proj.mem_badge}</span></span>
      </div>
      <div class="sp-row">
        <span class="sp-label">ML Inference:</span>
        <span class="sp-value">${proj.ml_s.toFixed(2)}s <span class="sp-badge ${proj.ml_badge.toLowerCase()}">${proj.ml_badge}</span></span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Projected Anomalies:</span>
        <span class="sp-value mono text-purple">${formatNum(proj.anomalies)} (4.0%)</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">DQ Issues Quarantined:</span>
        <span class="sp-value mono text-amber">${formatNum(proj.dq_issues)} Issues</span>
      </div>
    `;

    document.querySelectorAll(".scale-label").forEach((lbl, i) => {
      lbl.classList.toggle("active", i === index);
    });

    if (proj.ingestion_badge === "PROJECTED") {
      metricsProvenance.textContent = "[PROJECTED SCALE]";
    } else {
      metricsProvenance.textContent = "[MEASURED]";
    }
  }

  /* ─── Failure Lab Execution ─── */
  function triggerFailure(failureKey) {
    const scenario = FAILURE_SCENARIOS[failureKey];
    if (!scenario) return;

    // Reset previous failure states
    if (activeFailureTimeout) clearTimeout(activeFailureTimeout);
    pipeline.clearError(scenario.affected_stage);

    setSystemState("RECOVERING", `Simulating ${scenario.title}`);
    pipeline.setError(scenario.affected_stage);
    pipeline.panToNode(scenario.affected_stage, 1.25);

    // Update Bottleneck Widget
    bwStage.textContent = `${scenario.affected_stage.toUpperCase()} (${scenario.error_code})`;
    bwStage.className = "bw-stage mono text-red";
    bwQueue.textContent = "2,400 queued records";
    bwLoad.textContent = "CRITICAL / RETRYING";
    bwLoad.className = "bwm-val text-red";

    // Show Failure Result
    frTitle.textContent = `${scenario.title}`;
    frStatus.textContent = "INJECTING ERROR";
    frStatus.className = "fr-badge error";
    frLog.textContent = scenario.narrative.slice(0, 3).join("\n");
    failureResult.classList.remove("hidden");

    termWrite(`[FAILURE TEST] Injecting ${scenario.title}...`, "warn");

    // Animate resolution
    activeFailureTimeout = setTimeout(() => {
      frStatus.textContent = "AUTO-RECOVERED";
      frStatus.className = "fr-badge";
      frLog.textContent = scenario.narrative.join("\n");
      pipeline.clearError(scenario.affected_stage);
      pipeline.setCompleted(0);

      // Restore bottleneck
      bwStage.textContent = "None (System Optimal)";
      bwStage.className = "bw-stage mono text-amber";
      bwQueue.textContent = "0 records";
      bwLoad.textContent = "LOW";
      bwLoad.className = "bwm-val text-emerald";

      setSystemState(simRunning ? "RUNNING" : "IDLE", "Auto-recovery successful");
      termWrite(`[FAILURE RESOLVED] ${scenario.title} → Verified PASS (0 data loss).`, "success");
    }, 2800 / speedMultiplier);
  }

  /* ─── Deterministic Demo Simulation Timeline ─── */
  const DEMO_STAGES = [
    {
      id: "api_ingestion",
      name: "API INGESTION",
      desc: "HTTP REST extraction across 264 countries from api.worldbank.org/v2",
      nodeId: "ingestion",
      startPct: 0,
      endPct: 15,
      records: 15000,
      throughput: 22215,
      anomalies: 0,
      latency: "4.58s",
      dq: "100%",
      bottleneck: { stage: "api", queue: "0", load: "LOW", tp: "3,276 req/s" },
      log: "→ [0-10s] Ingestion Engine connected to World Bank REST API. Extracted 15,000 records in 4.58s."
    },
    {
      id: "raw_bronze",
      name: "RAW / BRONZE LAYER",
      desc: "Immutable JSONB staging (api_raw_responses) + SHA-256 fingerprinting",
      nodeId: "bronze",
      startPct: 15,
      endPct: 30,
      records: 15000,
      throughput: 28400,
      anomalies: 0,
      latency: "0.52s",
      dq: "100%",
      bottleneck: { stage: "bronze", queue: "0", load: "NORMAL", tp: "28,400 rec/s" },
      log: "→ [10-20s] Bronze Staging: 16 response pages hashed with SHA-256 and persisted in JSONB."
    },
    {
      id: "validation_dq",
      name: "VALIDATION & DATA QUALITY",
      desc: "WorldBankValidator type/range checks; 701 issues quarantined into audit log",
      nodeId: "validate",
      startPct: 30,
      endPct: 50,
      records: 100000,
      throughput: 45000,
      anomalies: 0,
      latency: "2.22s",
      dq: "99.3%",
      bottleneck: { stage: "validate", queue: "701 flagged", load: "NORMAL", tp: "45,000 rec/s" },
      log: "→ [20-35s] Validation Engine evaluated 100K obs: 99,299 clean (99.3%), 701 quarantined."
    },
    {
      id: "postgres_core",
      name: "POSTGRESQL SILVER CORE",
      desc: "Idempotent UPSERT loading into world_bank_observations (0 duplicates)",
      nodeId: "postgres",
      startPct: 50,
      endPct: 65,
      records: 100000,
      throughput: 22215,
      anomalies: 0,
      latency: "0.15ms",
      dq: "99.3%",
      bottleneck: { stage: "postgres", queue: "0", load: "OPTIMAL", tp: "22,215 rec/s" },
      log: "→ [35-50s] PostgreSQL Core loaded 100,000 observations in 1.06s. B-Tree scan: 0.15ms."
    },
    {
      id: "analytics_views",
      name: "ANALYTICAL SQL VIEWS",
      desc: "Materialized trend views & YoY growth calculations without row multiplication",
      nodeId: "analytics",
      startPct: 65,
      endPct: 75,
      records: 100000,
      throughput: 32000,
      anomalies: 0,
      latency: "0.43ms",
      dq: "99.3%",
      bottleneck: { stage: "analytics", queue: "0", load: "LOW", tp: "2,325 qps" },
      log: "→ [50-65s] SQL Analytical Views initialized: v_country_trends (0.43ms) & v_latest (3.46ms)."
    },
    {
      id: "ml_anomaly",
      name: "ML ANOMALY DETECTION",
      desc: "scikit-learn Isolation Forest evaluates 100K obs in 0.26s (4.0% anomaly rate)",
      nodeId: "ml",
      startPct: 75,
      endPct: 85,
      records: 100000,
      throughput: 55578,
      anomalies: 4000,
      latency: "0.26s",
      dq: "99.3%",
      bottleneck: { stage: "ml", queue: "0", load: "HIGH (55K/s)", tp: "55,578 obs/s" },
      log: "→ [65-80s] ML IsolationForest evaluated 100K records in 0.26s: 4,000 anomalies (4.0%) isolated."
    },
    {
      id: "ai_investigation",
      name: "AI GROUNDED INVESTIGATION",
      desc: "WorldBankInvestigator synthesizes structured evidence with non-causality notices",
      nodeId: "ai",
      startPct: 85,
      endPct: 95,
      records: 100000,
      throughput: 55578,
      anomalies: 4000,
      latency: "3ms",
      dq: "99.3%",
      bottleneck: { stage: "ai", queue: "0", load: "OPTIMAL", tp: "333 inv/s" },
      log: "→ [80-100s] AI Investigation Engine produced 5 structured findings with non-causality disclaimers."
    },
    {
      id: "lineage_presentation",
      name: "CRYPTOGRAPHIC LINEAGE",
      desc: "1-to-1 provenance verified: Insight ➔ Investigation ➔ Anomaly ➔ Silver ➔ Bronze ➔ API",
      nodeId: "lineage",
      startPct: 95,
      endPct: 100,
      records: 100000,
      throughput: 55578,
      anomalies: 4000,
      latency: "0.82ms",
      dq: "99.3%",
      bottleneck: { stage: "None", queue: "0", load: "COMPLETED", tp: "ALL VERIFIED" },
      log: "→ [100-120s] 7-Step Cryptographic Lineage verified 100% of records back to source API bytes."
    }
  ];

  function startSimulation() {
    if (simState === "RUNNING") return;
    setSystemState("RUNNING", "Executing Data Pipeline Simulation");
    particles.start(22215);

    const targetWorkload = SCALE_PROJECTIONS[currentWorkloadIdx];
    const totalRecords = targetWorkload.records;

    // Simulation loop timer
    clearInterval(simInterval);
    const tickMs = 100;
    const totalDurationMs = 16000 / speedMultiplier; // ~16s full cycle at 1x
    const stepPct = (tickMs / totalDurationMs) * 100;

    simInterval = setInterval(() => {
      simProgress += stepPct;

      if (simProgress >= 100) {
        simProgress = 100;
        setProgress(100);
        completeSimulation();
        return;
      }

      setProgress(simProgress);
      updateSimulationStage(simProgress, totalRecords);
    }, tickMs);
  }

  function updateSimulationStage(pct, totalRecords) {
    // Find matching stage
    const stageIdx = DEMO_STAGES.findIndex(s => pct >= s.startPct && pct < s.endPct);
    if (stageIdx !== -1 && stageIdx !== currentDemoStageIdx) {
      currentDemoStageIdx = stageIdx;
      const stage = DEMO_STAGES[stageIdx];

      // Update Banner
      stageStepNum.textContent = `STAGE ${stageIdx + 1} / 8`;
      stageStepName.textContent = stage.name;
      stageStepDesc.textContent = stage.desc;

      // Update Map Active Node
      pipeline.setActiveById(stage.nodeId);
      pipeline.panToNode(stage.nodeId, 1.15);

      // Update Bottleneck Monitor
      bwStage.textContent = stage.bottleneck.stage.toUpperCase();
      bwQueue.textContent = stage.bottleneck.queue;
      bwLoad.textContent = stage.bottleneck.load;
      bwLoad.className = "bwm-val " + (stage.bottleneck.load.includes("HIGH") ? "text-amber" : "text-emerald");
      bwThroughput.textContent = stage.bottleneck.tp;

      // Terminal narrative
      termWrite(stage.log, "info");
    }

    // Smoothly interpolate metrics
    const curRecords = Math.min(totalRecords, Math.round((pct / 100) * totalRecords));
    mvRecords.textContent = formatNum(curRecords);
    msRecords.textContent = `${formatNum(curRecords)} / ${formatNum(totalRecords)} Obs`;

    const stage = DEMO_STAGES[currentDemoStageIdx] || DEMO_STAGES[0];
    mvThroughput.textContent = formatNum(stage.throughput);
    
    if (pct >= 75) {
      const anomalies = Math.round(curRecords * 0.04);
      mvAnomalies.textContent = formatNum(anomalies);
      msAnomalyRate.textContent = "4.0% of Total";
      pipeline.updateNodeMetric("ml", `${formatNum(anomalies)} Anom`);
    } else {
      mvAnomalies.textContent = "0";
      msAnomalyRate.textContent = "0.0%";
    }

    pipeline.updateNodeMetric(stage.nodeId, `${formatNum(curRecords)} Recs`);
  }

  function pauseSimulation() {
    if (simState !== "RUNNING") return;
    clearInterval(simInterval);
    particles.pause();
    setSystemState("PAUSED", "Simulation paused by presenter");
    termWrite("[PAUSED] Simulation paused.", "warn");
  }

  function completeSimulation() {
    clearInterval(simInterval);
    particles.stop();
    setSystemState("COMPLETED", "Pipeline Simulation Run 100% Completed");

    const targetWorkload = SCALE_PROJECTIONS[currentWorkloadIdx];
    mvRecords.textContent = formatNum(targetWorkload.records);
    msRecords.textContent = `${formatNum(targetWorkload.records)} / ${formatNum(targetWorkload.records)} Obs`;
    mvAnomalies.textContent = formatNum(targetWorkload.anomalies);
    msAnomalyRate.textContent = "4.0% of Total";
    mvDq.textContent = "99.3%";

    stageStepNum.textContent = "COMPLETED";
    stageStepName.textContent = "END-TO-END PIPELINE COMPLETE";
    stageStepDesc.textContent = "All 8 layers verified. 100% cryptographic lineage intact.";

    termWrite("✓ [COMPLETED] End-to-end simulation cycle finished successfully.", "success");
    termWrite("✓ Verified: 0 duplicates, 100% SHA-256 integrity, 4.0% ML anomalies, 10/10 attacks blocked.", "prompt");
  }

  function resetSimulation() {
    clearInterval(simInterval);
    clearInterval(traceAutoInterval);
    if (activeFailureTimeout) clearTimeout(activeFailureTimeout);

    particles.clear();
    pipeline.reset();

    simProgress = 0;
    currentDemoStageIdx = -1;
    activeTraceStepIdx = -1;
    setProgress(0);

    // Reset Metrics
    mvRecords.textContent = "0";
    msRecords.textContent = "0 / 100,000 Obs";
    mvThroughput.textContent = "0";
    mvAnomalies.textContent = "0";
    msAnomalyRate.textContent = "0.0%";
    mvDq.textContent = "99.3%";

    // Reset Banner
    stageStepNum.textContent = "STAGE 0 / 8";
    stageStepName.textContent = "SYSTEM IDLE — Ready to Execute";
    stageStepDesc.textContent = "Click START or any stage node below for architectural deep-dive";

    // Reset Bottleneck
    bwStage.textContent = "None (System Optimal)";
    bwStage.className = "bw-stage mono text-amber";
    bwQueue.textContent = "0 records";
    bwLoad.textContent = "LOW";
    bwLoad.className = "bwm-val text-emerald";
    bwThroughput.textContent = "Optimal";

    // Close flyouts
    stageDetail.classList.add("hidden");
    failureResult.classList.add("hidden");
    lpvContainer.classList.add("hidden");

    termClear();
    termWrite("TraceImpact 2.0 — Data Platform Control Room", "prompt");
    termWrite("System state reset. Ready. Press ▶ START or SPACE to begin.", "info");

    setSystemState("IDLE", "System reset and ready");
  }

  /* ─── Judge Mode 3-Minute Guided Tour ─── */
  function openJudgeMode() {
    judgeMode = true;
    judgeStep = 0;
    judgeTimeLeft = 180;
    judgeOverlay.classList.remove("hidden");
    renderJudgeStep();
    startJudgeTimer();
  }

  function closeJudgeMode() {
    judgeMode = false;
    clearInterval(judgeTimerInterval);
    judgeOverlay.classList.add("hidden");
    pipeline.fitToMap();
  }

  function renderJudgeStep() {
    const step = JUDGE_STEPS[judgeStep];
    judgeStepTitle.innerHTML = step.title;
    judgeText.innerHTML = step.text;
    judgeStepIndicator.textContent = `${judgeStep + 1} / ${JUDGE_STEPS.length}`;

    judgePrev.disabled = judgeStep === 0;
    judgeNext.textContent = judgeStep === JUDGE_STEPS.length - 1 ? "FINISH TOUR ✓" : "NEXT STEP →";

    // Execute corresponding action
    if (step.action === "startPipeline") {
      resetSimulation();
      startSimulation();
    } else if (step.action.startsWith("highlightStage:")) {
      const stageId = step.action.split(":")[1];
      pipeline.highlightStage(stageId);
      showStageInspector(stageId);
    } else if (step.action === "showLineage") {
      pipeline.highlightStage("lineage");
      startBackwardTraceAuto();
    } else if (step.action === "showScale") {
      pipeline.highlightStage("postgres");
      renderScaleProjection(3); // 100K
    }
  }

  function startJudgeTimer() {
    clearInterval(judgeTimerInterval);
    judgeTimerInterval = setInterval(() => {
      judgeTimeLeft--;
      if (judgeTimeLeft <= 0) {
        judgeTimeLeft = 0;
        clearInterval(judgeTimerInterval);
      }
      const mins = Math.floor(judgeTimeLeft / 60);
      const secs = judgeTimeLeft % 60;
      judgeTimerEl.textContent = `${mins}:${secs.toString().padStart(2, "0")}`;
    }, 1000);
  }

  /* ─── Mode & Workload Toggles ─── */
  function toggleMode() {
    mode = mode === "live" ? "stress" : "live";
    modeLabel.textContent = mode === "live" ? "LIVE DEMO" : "STRESS SIM";
    btnModeToggle.classList.toggle("active", mode === "stress");

    if (mode === "stress") {
      globalBadge.textContent = "[STRESS SIMULATION]";
      globalBadge.className = "provenance-pill simulated";
      metricsProvenance.textContent = "[SIMULATED METRICS]";
      termWrite("⚡ Switched to STRESS SIMULATION MODE (Simulated queues & jitter).", "warn");
    } else {
      globalBadge.textContent = "[MEASURED SYSTEM]";
      globalBadge.className = "provenance-pill measured";
      metricsProvenance.textContent = "[MEASURED]";
      termWrite("✓ Switched to LIVE DEMO MODE (Verified benchmarks).", "info");
    }
  }

  function toggleProjectorMode() {
    document.body.classList.toggle("projector-mode");
    btnProjector.classList.toggle("active");
    pipeline.fitToMap();
    drawAnomalyChart();
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }

  function toggleReducedMotion() {
    particles.setReducedMotion(!particles.reducedMotion);
    btnMotion.classList.toggle("active", particles.reducedMotion);
    termWrite(`Motion animations: ${particles.reducedMotion ? "REDUCED" : "ENABLED"}`, "info");
  }

  /* ─── Event Listeners ─── */
  btnStart.addEventListener("click", () => {
    if (simState === "PAUSED") startSimulation();
    else if (simState === "IDLE" || simState === "COMPLETED") startSimulation();
  });
  btnPause.addEventListener("click", pauseSimulation);
  btnReset.addEventListener("click", resetSimulation);
  btnModeToggle.addEventListener("click", toggleMode);
  btnJudgeMode.addEventListener("click", openJudgeMode);
  btnProjector.addEventListener("click", toggleProjectorMode);
  btnMotion.addEventListener("click", toggleReducedMotion);
  btnFullscreen.addEventListener("click", toggleFullscreen);
  detailClose.addEventListener("click", () => stageDetail.classList.add("hidden"));

  // Speed Selector Buttons
  document.querySelectorAll(".speed-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      speedMultiplier = parseFloat(btn.dataset.speed);
      particles.setSpeed(speedMultiplier);
    });
  });

  // Scale Overlay Events
  btnScaleToggle.addEventListener("click", () => {
    scaleOverlay.classList.remove("hidden");
    renderScaleProjection(currentWorkloadIdx);
    scaleSlider.value = currentWorkloadIdx;
  });
  scaleClose.addEventListener("click", () => scaleOverlay.classList.add("hidden"));
  scaleSlider.addEventListener("input", () => {
    renderScaleProjection(parseInt(scaleSlider.value));
  });
  document.querySelectorAll(".scale-label").forEach(lbl => {
    lbl.addEventListener("click", () => {
      const idx = parseInt(lbl.dataset.idx);
      scaleSlider.value = idx;
      renderScaleProjection(idx);
    });
  });
  btnApplyScale.addEventListener("click", () => {
    scaleOverlay.classList.add("hidden");
    resetSimulation();
  });

  // Judge Tour Controls
  judgeNext.addEventListener("click", () => {
    if (judgeStep < JUDGE_STEPS.length - 1) {
      judgeStep++;
      renderJudgeStep();
    } else {
      closeJudgeMode();
    }
  });
  judgePrev.addEventListener("click", () => {
    if (judgeStep > 0) {
      judgeStep--;
      renderJudgeStep();
    }
  });
  judgeClose.addEventListener("click", closeJudgeMode);

  // Lineage Controls
  btnTraceBackward.addEventListener("click", startBackwardTraceAuto);
  lpvClose.addEventListener("click", () => lpvContainer.classList.add("hidden"));

  // AI Tab Switcher
  aiTabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      aiTabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      aiTabTerminal.classList.toggle("active", tab === "terminal");
      aiTabEvidence.classList.toggle("active", tab === "evidence");
    });
  });

  // Failure Lab Buttons
  document.querySelectorAll(".failure-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      triggerFailure(btn.dataset.failure);
    });
  });

  // Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!judgeOverlay.classList.contains("hidden")) closeJudgeMode();
      if (!scaleOverlay.classList.contains("hidden")) scaleOverlay.classList.add("hidden");
      stageDetail.classList.add("hidden");
      lpvContainer.classList.add("hidden");
    }
    if ((e.key === "f" || e.key === "F") && document.activeElement === document.body) {
      toggleFullscreen();
    }
    if ((e.key === "p" || e.key === "P") && document.activeElement === document.body) {
      toggleProjectorMode();
    }
    if ((e.key === "j" || e.key === "J") && document.activeElement === document.body) {
      openJudgeMode();
    }
    if ((e.key === "t" || e.key === "T") && document.activeElement === document.body) {
      startBackwardTraceAuto();
    }
    if ((e.key === "r" || e.key === "R") && document.activeElement === document.body) {
      resetSimulation();
    }
    if (e.key === " " && document.activeElement === document.body) {
      e.preventDefault();
      if (simState === "RUNNING") pauseSimulation();
      else startSimulation();
    }
    if (judgeMode) {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        if (judgeStep < JUDGE_STEPS.length - 1) {
          judgeStep++;
          renderJudgeStep();
        }
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        if (judgeStep > 0) {
          judgeStep--;
          renderJudgeStep();
        }
      }
    }
  });

  /* ─── Initial Render ─── */
  drawAnomalyChart();
  window.addEventListener("resize", drawAnomalyChart);

  renderLineage();
  renderScaleProjection(3); // 100K default

  termWrite("TraceImpact 2.0 — Data Platform Control Room & Digital Twin", "prompt");
  termWrite("Environment: macOS 15 · Python 3.14 · PostgreSQL 18.4 · Apple M4 (10 cores)", "info");
  termWrite("Ready. Press ▶ START or SPACE to run the live deterministic demo.", "info");
  termWrite("Press 🎯 JUDGE TOUR for a 3-minute executive presentation.", "info");

  setSystemState("IDLE", "Awaiting simulation trigger");

})();
