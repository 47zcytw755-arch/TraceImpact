/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Data Processing Control Room
   Main Application Controller
   ═══════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  /* ─── State ─── */
  let mode = "live";          // "live" | "stress"
  let simRunning = false;
  let simPaused = false;
  let simTimer = null;
  let simProgress = 0;        // 0-100
  let currentStageIdx = -1;
  let judgeMode = false;
  let judgeStep = 0;
  let judgeTimerInterval = null;
  let judgeTimeLeft = 180;    // 3 minutes

  /* ─── DOM Refs ─── */
  const $ = (id) => document.getElementById(id);
  const clock = $("live-clock");
  const btnStart = $("btn-start");
  const btnPause = $("btn-pause");
  const btnReset = $("btn-reset");
  const btnModeToggle = $("btn-mode-toggle");
  const modeLabel = $("mode-label");
  const btnJudgeMode = $("btn-judge-mode");
  const btnFullscreen = $("btn-fullscreen");
  const statusDot = $("status-dot");
  const statusText = $("status-text");
  const progressFill = $("progress-fill");
  const progressPct = $("progress-pct");
  const memUsage = $("mem-usage");
  const detailClose = $("detail-close");
  const stageDetail = $("stage-detail");

  // Metrics
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

  // ML
  const mlFitTime = $("ml-fit-time");
  const mlInferTime = $("ml-infer-time");
  const mlThroughput = $("ml-throughput");

  // AI Terminal
  const aiOutput = $("ai-output");

  // Judge
  const judgeOverlay = $("judge-overlay");
  const judgeText = $("judge-text");
  const judgeTimerEl = $("judge-timer");
  const judgeStepIndicator = $("judge-step-indicator");
  const judgePrev = $("judge-prev");
  const judgeNext = $("judge-next");
  const judgeClose = $("judge-close");

  // Scale
  const scaleOverlay = $("scale-overlay");
  const scaleSlider = $("scale-slider");
  const scaleProjections = $("scale-projections");
  const scaleClose = $("scale-close");

  // Failure
  const failureResult = $("failure-result");

  /* ─── Initialize Components ─── */
  const pipeline = new PipelineRenderer("pipeline-stages");
  const particles = new ParticleSystem("particle-canvas");

  /* ─── Clock ─── */
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

  /* ─── Utility ─── */
  function formatNum(n) {
    if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n.toLocaleString();
  }

  function animateValue(el, start, end, duration, formatter) {
    const range = end - start;
    const startTime = performance.now();
    formatter = formatter || ((v) => Math.round(v).toLocaleString());

    function step(ts) {
      const elapsed = ts - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = start + range * eased;
      el.textContent = formatter(current);
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function pulseCard(cardId) {
    const card = $(cardId);
    card.classList.add("pulse");
    setTimeout(() => card.classList.remove("pulse"), 800);
  }

  function setStatus(state, text) {
    statusDot.className = "status-dot " + state;
    statusText.textContent = text;
  }

  function setProgress(pct) {
    simProgress = pct;
    progressFill.style.width = pct + "%";
    progressPct.textContent = Math.round(pct) + "%";
  }

  /* ─── AI Terminal ─── */
  function termWrite(text, cls) {
    const line = document.createElement("div");
    line.className = "terminal-line " + (cls || "");
    line.textContent = text;
    aiOutput.appendChild(line);
    aiOutput.scrollTop = aiOutput.scrollHeight;
  }

  function termClear() { aiOutput.innerHTML = ""; }

  function termTyping(lines, cls, delay, callback) {
    let i = 0;
    function next() {
      if (i >= lines.length) {
        if (callback) callback();
        return;
      }
      termWrite(lines[i], cls || "info");
      i++;
      setTimeout(next, delay || 120);
    }
    next();
  }

  /* ─── Anomaly Chart ─── */
  function drawAnomalyChart() {
    const canvas = $("anomaly-chart");
    const ctx = canvas.getContext("2d");
    const w = canvas.width = canvas.offsetWidth * window.devicePixelRatio;
    const h = canvas.height = canvas.offsetHeight * window.devicePixelRatio;
    ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;

    ctx.clearRect(0, 0, cw, ch);

    // Generate synthetic score distribution for visualization
    const bins = 40;
    const data = new Array(bins).fill(0);
    const minScore = STRESS_DATA.ml.score_min;
    const maxScore = STRESS_DATA.ml.score_max;
    const range = maxScore - minScore;
    const mean = STRESS_DATA.ml.score_mean;
    const sd = range / 4;

    // Gaussian-like distribution
    for (let i = 0; i < bins; i++) {
      const x = minScore + (i / bins) * range;
      data[i] = Math.exp(-0.5 * Math.pow((x - mean) / sd, 2));
    }

    // Normalize
    const maxVal = Math.max(...data);
    const barW = (cw - 40) / bins;
    const plotH = ch - 30;
    const plotY = 10;

    // Threshold line (anomaly cutoff)
    const thresholdBin = Math.floor(((0 - minScore) / range) * bins);

    // Draw bars
    for (let i = 0; i < bins; i++) {
      const barH = (data[i] / maxVal) * (plotH - 10);
      const x = 30 + i * barW;
      const y = plotY + plotH - barH;

      const isAnomaly = i < thresholdBin + 2;
      ctx.fillStyle = isAnomaly ? "rgba(239, 71, 111, 0.7)" : "rgba(139, 92, 246, 0.5)";
      ctx.fillRect(x, y, barW - 1, barH);

      // Glow on anomaly bars
      if (isAnomaly) {
        ctx.fillStyle = "rgba(239, 71, 111, 0.15)";
        ctx.fillRect(x - 1, y - 2, barW + 1, barH + 4);
      }
    }

    // Threshold line
    const tx = 30 + (thresholdBin + 2) * barW;
    ctx.strokeStyle = "rgba(239, 71, 111, 0.6)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(tx, plotY);
    ctx.lineTo(tx, plotY + plotH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = "#4f6080";
    ctx.font = "9px 'JetBrains Mono'";
    ctx.textAlign = "center";
    ctx.fillText(minScore.toFixed(2), 30, plotY + plotH + 14);
    ctx.fillText(maxScore.toFixed(2), 30 + bins * barW, plotY + plotH + 14);
    ctx.fillText("score", 30 + bins * barW / 2, plotY + plotH + 14);

    // Anomaly label
    ctx.fillStyle = "#ef476f";
    ctx.font = "bold 8px 'JetBrains Mono'";
    ctx.textAlign = "left";
    ctx.fillText("ANOMALIES (4%)", tx + 4, plotY + 10);

    // Normal label
    ctx.fillStyle = "#8b5cf6";
    ctx.textAlign = "right";
    ctx.fillText("NORMAL (96%)", tx - 4, plotY + 10);
  }

  /* ─── Lineage Visualization ─── */
  function renderLineage() {
    const container = $("lineage-viz");
    container.innerHTML = "";

    LINEAGE_CHAIN.forEach((step, i) => {
      const stepEl = document.createElement("div");
      stepEl.className = "lineage-step";
      stepEl.style.animationDelay = (i * 0.12) + "s";
      stepEl.innerHTML = `
        <div class="lineage-step-icon">${step.step}</div>
        <div class="lineage-step-content">
          <div class="lineage-step-title">${step.title}</div>
          <div class="lineage-step-detail">${step.detail}</div>
        </div>
      `;
      container.appendChild(stepEl);

      if (i < LINEAGE_CHAIN.length - 1) {
        const conn = document.createElement("div");
        conn.className = "lineage-connector-v lit";
        container.appendChild(conn);
      }
    });
  }

  /* ─── Scale Projections ─── */
  function renderScaleProjection(index) {
    const proj = SCALE_PROJECTIONS[index];
    scaleProjections.innerHTML = `
      <div class="sp-row">
        <span class="sp-label">Records</span>
        <span class="sp-value">${formatNum(proj.records)}</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Ingestion Time</span>
        <span class="sp-value">${proj.ingestion_s.toFixed(2)}s <span class="sp-badge ${proj.ingestion_badge}">${proj.ingestion_badge.toUpperCase()}</span></span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Throughput</span>
        <span class="sp-value">${formatNum(proj.throughput_rps)} rec/sec</span>
      </div>
      <div class="sp-row">
        <span class="sp-label">Peak Memory</span>
        <span class="sp-value">${proj.mem_mb.toFixed(0)} MB <span class="sp-badge ${proj.mem_badge}">${proj.mem_badge.toUpperCase()}</span></span>
      </div>
      <div class="sp-row">
        <span class="sp-label">ML Pipeline</span>
        <span class="sp-value">${proj.ml_s.toFixed(2)}s <span class="sp-badge ${proj.ml_badge}">${proj.ml_badge.toUpperCase()}</span></span>
      </div>
    `;
    // Update active scale label
    document.querySelectorAll(".scale-label").forEach((lbl, i) => {
      lbl.classList.toggle("active", i === index);
    });
  }

  /* ─── Simulation Engine ─── */
  const SIM_STAGES = PIPELINE_STAGES.map((s, i) => ({
    ...s,
    duration: [800, 500, 1200, 600, 800, 400, 900, 700, 600, 500, 1000, 800, 600, 400][i] || 600,
    progressWeight: [8, 3, 12, 6, 8, 4, 10, 8, 6, 10, 15, 5, 3, 2][i] || 5
  }));

  function getTotalSimDuration() {
    return SIM_STAGES.reduce((sum, s) => sum + s.duration, 0);
  }

  function startSimulation() {
    if (simRunning) return;
    simRunning = true;
    simPaused = false;
    currentStageIdx = -1;
    simProgress = 0;

    btnStart.disabled = true;
    btnPause.disabled = false;
    btnReset.disabled = false;
    setStatus("running", "PROCESSING");
    setProgress(0);
    pipeline.reset();
    particles.start(STRESS_DATA.batch_benchmarks[1000].rps);
    termClear();
    termWrite("▸ TraceImpact 2.0 Pipeline Simulation Started", "prompt");
    termWrite(`  Mode: ${mode === "live" ? "Live Demo" : "Stress Simulation"}`, "info");
    termWrite("", "");

    advanceStage();
  }

  function advanceStage() {
    if (!simRunning || simPaused) return;

    currentStageIdx++;
    if (currentStageIdx >= SIM_STAGES.length) {
      completeSimulation();
      return;
    }

    const stage = SIM_STAGES[currentStageIdx];
    pipeline.setActive(currentStageIdx);
    particles.setActiveStage(currentStageIdx);

    // Update metrics progressively
    updateMetricsForStage(currentStageIdx);

    // Terminal output
    termWrite(`▸ ${stage.icon} ${stage.label}`, "prompt");

    simTimer = setTimeout(() => {
      pipeline.setCompleted(currentStageIdx);

      // Stage-specific terminal output
      writeStageResult(currentStageIdx);

      // Accumulate progress
      const totalWeight = SIM_STAGES.reduce((s, st) => s + st.progressWeight, 0);
      const accumulated = SIM_STAGES.slice(0, currentStageIdx + 1).reduce((s, st) => s + st.progressWeight, 0);
      setProgress((accumulated / totalWeight) * 100);

      advanceStage();
    }, stage.duration);
  }

  function updateMetricsForStage(idx) {
    const stage = SIM_STAGES[idx];

    switch (stage.id) {
      case "api":
        animateValue(mvRecords, 0, STRESS_DATA.dataset.real_api_records, 800);
        msRecords.textContent = "from API";
        pulseCard("mc-records");
        break;
      case "ingestion":
        animateValue(mvThroughput, 0, STRESS_DATA.batch_benchmarks[1000].rps, 1000, v => formatNum(Math.round(v)));
        pulseCard("mc-throughput");
        break;
      case "validate":
      case "dq":
        mvDq.textContent = "99.3%";
        msDqIssues.textContent = "701 issues";
        pulseCard("mc-dq");
        break;
      case "postgres":
        animateValue(mvRecords, STRESS_DATA.dataset.real_api_records, STRESS_DATA.dataset.total_observations, 600);
        msRecords.textContent = "total observations";
        mvLatency.textContent = "0.15";
        pulseCard("mc-latency");
        memUsage.textContent = `RAM: ${STRESS_DATA.batch_benchmarks[25000].mem_mb.toFixed(0)} MB`;
        break;
      case "ml":
        animateValue(mvAnomalies, 0, STRESS_DATA.ml.anomalies, 800);
        msAnomalyRate.textContent = STRESS_DATA.ml.anomaly_pct + "%";
        pulseCard("mc-anomalies");
        mlFitTime.textContent = STRESS_DATA.ml.fit_s + "s";
        mlInferTime.textContent = STRESS_DATA.ml.inference_s + "s";
        mlThroughput.textContent = formatNum(STRESS_DATA.ml.throughput_rps) + "/s";
        memUsage.textContent = `RAM: ${STRESS_DATA.ml.peak_ram_mb.toFixed(0)} MB`;
        drawAnomalyChart();
        break;
      case "ai":
        mvSecurity.textContent = "100%";
        msSecurity.textContent = "10/10 blocked";
        pulseCard("mc-security");
        break;
      case "lineage":
        renderLineage();
        break;
    }
  }

  function writeStageResult(idx) {
    const stage = SIM_STAGES[idx];

    switch (stage.id) {
      case "api":
        termWrite(`  ✓ Fetched ${STRESS_DATA.dataset.real_api_records.toLocaleString()} records in ${STRESS_DATA.timings.api_extraction_s}s`, "success");
        break;
      case "scheduler":
        termWrite("  ✓ APScheduler: next run in 24h", "success");
        break;
      case "ingestion":
        termWrite(`  ✓ Throughput: ${STRESS_DATA.batch_benchmarks[1000].rps.toLocaleString()} rec/sec`, "success");
        break;
      case "pagination":
        termWrite(`  ✓ ${STRESS_DATA.db_tables.api_raw_responses} pages processed`, "success");
        break;
      case "bronze":
        termWrite("  ✓ Raw JSONB payloads stored (immutable)", "success");
        break;
      case "hash":
        termWrite("  ✓ SHA-256 fingerprints computed", "success");
        break;
      case "validate":
        termWrite(`  ✓ ${STRESS_DATA.db_tables.world_bank_data_quality_issues} DQ issues cataloged`, "success");
        break;
      case "dq":
        termWrite("  ✓ DQ Score: 99.3%", "success");
        break;
      case "transform":
        termWrite(`  ✓ UPSERT: 0 duplicates`, "success");
        break;
      case "postgres":
        termWrite(`  ✓ ${STRESS_DATA.dataset.total_observations.toLocaleString()} observations loaded`, "success");
        termWrite(`  ✓ Composite query: ${STRESS_DATA.db_benchmarks.composite_ms}ms`, "success");
        break;
      case "ml":
        termWrite(`  ✓ IsolationForest: ${STRESS_DATA.ml.anomalies.toLocaleString()} anomalies (${STRESS_DATA.ml.anomaly_pct}%)`, "success");
        termWrite(`  ✓ Throughput: ${STRESS_DATA.ml.throughput_rps.toLocaleString()} obs/sec`, "success");
        break;
      case "ai":
        termWrite(`  ✓ ${STRESS_DATA.ai.investigations} investigations @ ${STRESS_DATA.ai.avg_latency_s * 1000}ms avg`, "success");
        termWrite(`  ✓ Sample: "${STRESS_DATA.ai.sample.summary.substring(0, 60)}..."`, "highlight");
        break;
      case "lineage":
        termWrite(`  ✓ ${STRESS_DATA.lineage.traced}/${STRESS_DATA.lineage.sample_size} traces verified (${STRESS_DATA.lineage.success_pct}%)`, "success");
        break;
      case "dashboard":
        termWrite(`  ✓ 6 dashboard pages ready`, "success");
        termWrite(`  ✓ Security: ${STRESS_DATA.security.attacks_blocked}/${STRESS_DATA.security.attacks_tested} attacks blocked`, "success");
        break;
    }
  }

  function completeSimulation() {
    simRunning = false;
    setStatus("completed", "COMPLETE");
    setProgress(100);
    particles.stop();
    btnStart.disabled = false;
    btnPause.disabled = true;
    termWrite("", "");
    termWrite("═══ Pipeline Simulation Complete ═══", "prompt");
    termWrite(`Total observations: ${STRESS_DATA.dataset.total_observations.toLocaleString()}`, "success");
    termWrite(`Anomalies detected: ${STRESS_DATA.ml.anomalies.toLocaleString()} (${STRESS_DATA.ml.anomaly_pct}%)`, "success");
    termWrite(`Lineage: ${STRESS_DATA.lineage.verdict}`, "success");
    termWrite(`Security: ${STRESS_DATA.security.verdict}`, "success");
    termWrite(`Overall: PASS`, "success");
  }

  function pauseSimulation() {
    if (!simRunning) return;
    simPaused = !simPaused;
    btnPause.textContent = simPaused ? "▶" : "⏸";
    if (simPaused) {
      clearTimeout(simTimer);
      particles.stop();
      setStatus("running", "PAUSED");
    } else {
      particles.start(STRESS_DATA.batch_benchmarks[1000].rps);
      setStatus("running", "PROCESSING");
      advanceStage();
    }
  }

  function resetSimulation() {
    simRunning = false;
    simPaused = false;
    clearTimeout(simTimer);
    currentStageIdx = -1;
    pipeline.reset();
    particles.clear();
    setStatus("", "IDLE");
    setProgress(0);
    btnStart.disabled = false;
    btnPause.disabled = true;
    btnReset.disabled = true;
    btnPause.textContent = "⏸";

    // Reset metrics
    mvRecords.textContent = "0";
    msRecords.textContent = "—";
    mvThroughput.textContent = "0";
    mvAnomalies.textContent = "0";
    msAnomalyRate.textContent = "0%";
    mvDq.textContent = "—";
    msDqIssues.textContent = "0 issues";
    mvLatency.textContent = "—";
    mvSecurity.textContent = "—";
    msSecurity.textContent = "0/0 blocked";
    mlFitTime.textContent = "—";
    mlInferTime.textContent = "—";
    mlThroughput.textContent = "—";
    memUsage.textContent = "RAM: —";
    termClear();
    $("lineage-viz").innerHTML = "";
  }

  /* ─── Failure Lab ─── */
  function triggerFailure(failureKey) {
    const scenario = FAILURE_SCENARIOS[failureKey];
    if (!scenario) return;

    // Highlight button
    const btn = document.querySelector(`[data-failure="${failureKey}"]`);
    btn.classList.add("triggered");
    setTimeout(() => btn.classList.remove("triggered"), 1200);

    // Flash error on a pipeline stage
    const errorStageIdx = failureKey === "sqli" ? 13 : 2; // ingestion stage for most
    pipeline.setError(errorStageIdx);
    setTimeout(() => pipeline.clearError(errorStageIdx), 1500);

    // Show result
    failureResult.classList.remove("hidden");
    failureResult.innerHTML = `<strong style="color:var(--amber)">${scenario.title}</strong><br>`;

    let i = 0;
    const interval = setInterval(() => {
      if (i >= scenario.narrative.length) {
        clearInterval(interval);
        failureResult.innerHTML += `<br><span class="fr-pass">Result: ${scenario.result} ${scenario.measured ? "[MEASURED]" : ""}</span>`;
        return;
      }
      failureResult.innerHTML += scenario.narrative[i] + "<br>";
      failureResult.scrollTop = failureResult.scrollHeight;
      i++;
    }, 200);
  }

  /* ─── Judge Mode ─── */
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
    judgeOverlay.classList.add("hidden");
    clearInterval(judgeTimerInterval);
  }

  function renderJudgeStep() {
    const step = JUDGE_STEPS[judgeStep];
    judgeText.innerHTML = `<strong>${step.title}</strong><br><br>${step.text}`;
    judgeStepIndicator.textContent = `${judgeStep + 1} / ${JUDGE_STEPS.length}`;
    judgePrev.disabled = judgeStep === 0;
    judgeNext.textContent = judgeStep === JUDGE_STEPS.length - 1 ? "FINISH" : "NEXT →";

    // Execute action
    if (step.action) {
      executeJudgeAction(step.action);
    }
  }

  function executeJudgeAction(action) {
    if (action === "startPipeline") {
      resetSimulation();
      startSimulation();
    } else if (action.startsWith("highlightStage:")) {
      const stageId = action.split(":")[1];
      pipeline.highlightStage(stageId);
    } else if (action === "showLineage") {
      renderLineage();
    } else if (action === "highlightFailureLab") {
      // Flash failure panel border
      $("failure-panel").style.borderColor = "var(--amber)";
      $("failure-panel").style.boxShadow = "0 0 16px var(--amber-dim)";
      setTimeout(() => {
        $("failure-panel").style.borderColor = "";
        $("failure-panel").style.boxShadow = "";
      }, 2000);
    } else if (action === "showScale") {
      // Show scale info in metrics
      $("metrics-provenance").textContent = "[MEASURED + PROJECTED]";
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
      if (judgeTimeLeft <= 30) {
        judgeTimerEl.style.color = "var(--red)";
        judgeTimerEl.style.borderColor = "var(--red)";
      }
    }, 1000);
  }

  /* ─── Mode Toggle ─── */
  function toggleMode() {
    mode = mode === "live" ? "stress" : "live";
    modeLabel.textContent = mode === "live" ? "LIVE DEMO" : "STRESS SIM";
    btnModeToggle.classList.toggle("active", mode === "stress");

    if (mode === "stress") {
      scaleOverlay.classList.remove("hidden");
      renderScaleProjection(2); // default to 100K
      scaleSlider.value = 2;
    }
  }

  /* ─── Fullscreen ─── */
  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen();
    }
  }

  /* ─── Event Listeners ─── */
  btnStart.addEventListener("click", startSimulation);
  btnPause.addEventListener("click", pauseSimulation);
  btnReset.addEventListener("click", resetSimulation);
  btnModeToggle.addEventListener("click", toggleMode);
  btnJudgeMode.addEventListener("click", openJudgeMode);
  btnFullscreen.addEventListener("click", toggleFullscreen);
  detailClose.addEventListener("click", () => stageDetail.classList.add("hidden"));

  // Judge controls
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

  // Scale controls
  scaleSlider.addEventListener("input", () => {
    renderScaleProjection(parseInt(scaleSlider.value));
  });
  scaleClose.addEventListener("click", () => scaleOverlay.classList.add("hidden"));

  // Scale labels clickable
  document.querySelectorAll(".scale-label").forEach(lbl => {
    lbl.addEventListener("click", () => {
      const idx = parseInt(lbl.dataset.idx);
      scaleSlider.value = idx;
      renderScaleProjection(idx);
    });
  });

  // Failure lab buttons
  document.querySelectorAll(".failure-btn").forEach(btn => {
    btn.addEventListener("click", () => triggerFailure(btn.dataset.failure));
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (!judgeOverlay.classList.contains("hidden")) closeJudgeMode();
      if (!scaleOverlay.classList.contains("hidden")) scaleOverlay.classList.add("hidden");
      stageDetail.classList.add("hidden");
    }
    if (e.key === "f" || e.key === "F") {
      if (!e.ctrlKey && !e.metaKey && document.activeElement === document.body) {
        toggleFullscreen();
      }
    }
    if (e.key === " " && document.activeElement === document.body) {
      e.preventDefault();
      if (!simRunning) startSimulation();
      else pauseSimulation();
    }
    // Arrow keys for judge mode
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

  // Set initial terminal state
  termWrite("TraceImpact 2.0 — Data Processing Control Room", "prompt");
  termWrite("Ready. Press ▶ START or SPACE to begin.", "info");
  termWrite("Press JUDGE MODE for 3-minute guided tour.", "info");

  // Render initial lineage
  renderLineage();

})();
