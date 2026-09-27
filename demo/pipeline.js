/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Interactive Data Processing Map / Digital Twin
   Non-linear Network Topology, SVG Bezier Routes, Pan/Zoom & Batch Animation
   ═══════════════════════════════════════════════════════════════════ */

class PipelineNetworkMap {
  constructor(containerId, onNodeSelected) {
    this.container = typeof containerId === "string" ? document.getElementById(containerId) : containerId;
    this.onNodeSelected = onNodeSelected || null;
    this.viewport = null;
    this.svgLayer = null;
    this.nodesContainer = null;
    this.canvasLayer = null;
    this.ctx = null;

    // Viewport transform state (Pan / Zoom)
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };
    this.activeTraceNode = null;
    this.activeTracePath = [];

    // Stage nodes definitions with logical coordinates
    this.nodes = [
      // LAYER 1: SOURCES (X: 50)
      { id: "api", label: "World Bank API", icon: "🌐", layer: "source", x: 50, y: 90, tier: "major", status: "ONLINE", tech: "api.worldbank.org/v2", recs: "15,000 [REAL]", sub: "HTTP REST API" },
      { id: "scheduler", label: "APScheduler", icon: "⏱", layer: "ingest", x: 50, y: 240, tier: "small", status: "CRON", tech: "APScheduler 3.10", recs: "Daily 02:00", sub: "Cron Trigger" },

      // LAYER 2: INGESTION & RAW STAGING (X: 230)
      { id: "ingestion", label: "Ingestion Engine", icon: "📥", layer: "ingest", x: 230, y: 90, tier: "major", status: "READY", tech: "WorldBankExtractor", recs: "22,215 rps", sub: "Stream Parser" },
      { id: "pagination", label: "Page Iterator", icon: "📑", layer: "ingest", x: 230, y: 210, tier: "normal", status: "STANDBY", tech: "16 Pages @ 1K", recs: "16 pages", sub: "Page Chunks" },
      { id: "bronze", label: "Raw / Bronze", icon: "🥉", layer: "ingest", x: 230, y: 330, tier: "normal", status: "STORED", tech: "api_raw_responses", recs: "Immutable", sub: "JSONB Staging" },
      { id: "hash", label: "SHA-256 Digest", icon: "🔐", layer: "ingest", x: 230, y: 440, tier: "normal", status: "VERIFIED", tech: "SHA-256 Digest", recs: "100% Hash Check", sub: "Provenance" },

      // LAYER 3: DATA QUALITY & VALIDATION (X: 430 - 580)
      { id: "validate", label: "Validation Engine", icon: "✓", layer: "quality", x: 430, y: 220, tier: "major", status: "READY", tech: "WorldBankValidator", recs: "99.3% Valid", sub: "Boundary Engine" },
      { id: "clean", label: "Clean / Silver", icon: "🔧", layer: "quality", x: 600, y: 110, tier: "normal", status: "CLEANED", tech: "UPSERT Normalizer", recs: "99,299 Obs", sub: "Silver Table" },
      { id: "dq", label: "DQ Quarantine", icon: "📊", layer: "quality", x: 600, y: 340, tier: "alert", status: "AUDITED", tech: "701 Logged Issues", recs: "701 Issues", sub: "Audit Log" },

      // LAYER 4: CENTRAL DATA CORE HUB (X: 780)
      { id: "postgres", label: "POSTGRESQL CORE", icon: "🐘", layer: "core", x: 780, y: 220, tier: "core", status: "CENTRAL HUB", tech: "PostgreSQL 18.4 Engine", recs: "100,000 OBS", sub: "Single Source of Truth" },

      // LAYER 5: INTELLIGENCE & ML (X: 970)
      { id: "analytics", label: "Analytical Views", icon: "📈", layer: "intelligence", x: 970, y: 60, tier: "normal", status: "QUERYING", tech: "5 SQL Views", recs: "v_country_trends", sub: "Trend Analytics" },
      { id: "features", label: "Feature Engine", icon: "⚙️", layer: "intelligence", x: 970, y: 165, tier: "normal", status: "COMPUTING", tech: "z-score & peer growth", recs: "100K features", sub: "Vector Engine" },
      { id: "ml", label: "ML Isolation Forest", icon: "🧠", layer: "intelligence", x: 970, y: 275, tier: "major", status: "EVALUATING", tech: "sklearn IsolationForest", recs: "4,000 Anomalies", sub: "Contamination 4%" },
      { id: "lineage", label: "Lineage Tracker", icon: "🔗", layer: "intelligence", x: 970, y: 395, tier: "normal", status: "VERIFIED", tech: "7-Step JOIN Lineage", recs: "100% Trace", sub: "Audit Trail" },

      // LAYER 6: AI INVESTIGATION & PRESENTATION (X: 1160 - 1320)
      { id: "ai", label: "AI Investigator", icon: "🤖", layer: "ai", x: 1160, y: 220, tier: "major", status: "SYNTHESIZING", tech: "WorldBankInvestigator", recs: "5 insights", sub: "Non-Causality" },
      { id: "power_bi", label: "Power BI Executive", icon: "📊", layer: "presentation", x: 1330, y: 130, tier: "output", status: "CONNECTED", tech: "Star Schema Model", recs: "9-Page Model", sub: "Board Reports" },
      { id: "streamlit", label: "Streamlit App", icon: "📱", layer: "presentation", x: 1330, y: 310, tier: "output", status: "ACTIVE", tech: "Interactive Portal", recs: "Lineage UI", sub: "Drilldown" }
    ];

    this.routes = [
      // Source & Schedule to Ingestion
      { from: "api", to: "ingestion", type: "main" },
      { from: "scheduler", to: "ingestion", type: "control" },

      // Ingestion Flow
      { from: "ingestion", to: "pagination", type: "main" },
      { from: "pagination", to: "bronze", type: "main" },
      { from: "bronze", to: "hash", type: "main" },
      { from: "hash", to: "validate", type: "main" },

      // Validation Branching (Clean Data vs DQ Flagged Quarantine)
      { from: "validate", to: "clean", type: "clean", label: "Valid Data (99.3%)" },
      { from: "validate", to: "dq", type: "dq", label: "DQ Issues (Quarantined)" },

      // Convergence into PostgreSQL Core Hub
      { from: "clean", to: "postgres", type: "clean" },
      { from: "dq", to: "postgres", type: "dq" },

      // Central Hub Branching into Analytics, ML Features, Lineage
      { from: "postgres", to: "analytics", type: "main" },
      { from: "postgres", to: "features", type: "main" },
      { from: "features", to: "ml", type: "main" },
      { from: "postgres", to: "lineage", type: "lineage" },

      // Convergence to AI Investigation Engine
      { from: "analytics", to: "ai", type: "main" },
      { from: "ml", to: "ai", type: "ml", label: "Anomalies (4.0%)" },
      { from: "lineage", to: "ai", type: "lineage" },

      // Presentation Layer Deliveries
      { from: "ai", to: "power_bi", type: "ai" },
      { from: "ai", to: "streamlit", type: "ai" }
    ];

    this.activeNodeId = null;
    this.completedNodes = new Set();
    this.errorNodes = new Set();
    this.bottleneckNode = null;
    this.nodeMetrics = {};

    this._initDom();
    this._bindEvents();
  }

  _initDom() {
    if (!this.container) return;
    this.container.innerHTML = "";
    this.container.className = "network-map-container";

    // Viewport transform wrapper
    this.viewport = document.createElement("div");
    this.viewport.className = "map-viewport";
    this.container.appendChild(this.viewport);

    // SVG Layer for Bezier Routes
    this.svgLayer = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svgLayer.setAttribute("class", "map-svg-layer");
    this.svgLayer.setAttribute("width", "1480");
    this.svgLayer.setAttribute("height", "540");
    this.viewport.appendChild(this.svgLayer);

    // Canvas Layer for Animated Data Batches
    this.canvasLayer = document.createElement("canvas");
    this.canvasLayer.id = "particle-canvas";
    this.canvasLayer.setAttribute("class", "map-canvas-layer");
    this.canvasLayer.width = 1480;
    this.canvasLayer.height = 540;
    this.viewport.appendChild(this.canvasLayer);
    this.ctx = this.canvasLayer.getContext("2d");

    // Nodes Container
    this.nodesContainer = document.createElement("div");
    this.nodesContainer.className = "map-nodes-container";
    this.viewport.appendChild(this.nodesContainer);

    // Map Navigation Controls Overlay
    const mapControls = document.createElement("div");
    mapControls.className = "map-nav-controls";
    mapControls.innerHTML = `
      <button class="map-btn" id="map-zoom-in" title="Zoom In (+)">+</button>
      <button class="map-btn" id="map-zoom-out" title="Zoom Out (−)">−</button>
      <button class="map-btn" id="map-fit" title="Fit to Screen">FIT</button>
      <button class="map-btn" id="map-reset" title="Reset View">RESET</button>
    `;
    this.container.appendChild(mapControls);

    this._renderSvgRoutes();
    this._renderNodes();
    setTimeout(() => this.fitToMap(), 50);
  }

  _bindEvents() {
    const controls = this.container.querySelector(".map-nav-controls");
    if (controls) {
      controls.querySelector("#map-zoom-in").addEventListener("click", () => this.zoomBy(0.15));
      controls.querySelector("#map-zoom-out").addEventListener("click", () => this.zoomBy(-0.15));
      controls.querySelector("#map-reset").addEventListener("click", () => this.resetView());
      controls.querySelector("#map-fit").addEventListener("click", () => this.fitToMap());
    }

    // Mouse Dragging Pan
    this.container.addEventListener("mousedown", (e) => {
      if (e.target.closest(".map-node") || e.target.closest(".map-nav-controls")) return;
      this.isDragging = true;
      this.dragStart = { x: e.clientX - this.panX, y: e.clientY - this.panY };
      this.container.style.cursor = "grabbing";
    });

    window.addEventListener("mousemove", (e) => {
      if (!this.isDragging) return;
      this.panX = e.clientX - this.dragStart.x;
      this.panY = e.clientY - this.dragStart.y;
      this._updateTransform();
    });

    window.addEventListener("mouseup", () => {
      if (this.isDragging) {
        this.isDragging = false;
        this.container.style.cursor = "default";
      }
    });

    // Wheel Zoom
    this.container.addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      this.zoomBy(delta);
    }, { passive: false });

    // Window Resize Observer for Auto Fit
    window.addEventListener("resize", () => {
      if (!this.activeTraceNode && !this.isDragging) {
        this.fitToMap();
      }
    });
  }

  zoomBy(delta) {
    this.zoom = Math.min(2.0, Math.max(0.4, this.zoom + delta));
    this._updateTransform();
  }

  resetView() {
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this._updateTransform(true);
  }

  fitToMap() {
    if (!this.container) return;
    const containerRect = this.container.getBoundingClientRect();
    const mapW = 1480;
    const mapH = 540;
    if (containerRect.width <= 0 || containerRect.height <= 0) return;

    const scaleX = (containerRect.width - 24) / mapW;
    const scaleY = (containerRect.height - 24) / mapH;
    this.zoom = Math.min(scaleX, scaleY, 1.05);
    this.panX = (containerRect.width - mapW * this.zoom) / 2;
    this.panY = (containerRect.height - mapH * this.zoom) / 2;
    this._updateTransform(true);
  }

  panToNode(nodeId, targetZoom = 1.2) {
    const node = this.nodes.find(n => n.id === nodeId);
    if (!node || !this.container) return;
    const containerRect = this.container.getBoundingClientRect();
    this.zoom = targetZoom;
    this.panX = (containerRect.width / 2) - (node.x * this.zoom);
    this.panY = (containerRect.height / 2) - (node.y * this.zoom);
    this._updateTransform(true);
  }

  _updateTransform(animated = false) {
    if (!this.viewport) return;
    if (animated) {
      this.viewport.style.transition = "transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)";
    } else {
      this.viewport.style.transition = "none";
    }
    this.viewport.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.zoom})`;
  }

  _renderSvgRoutes() {
    this.svgLayer.innerHTML = "";
    
    // SVG Defs for gradients & glowing filters
    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
      <filter id="glow-route" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
      <linearGradient id="grad-main" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#06d6a0" stop-opacity="0.85"/>
        <stop offset="100%" stop-color="#118ab2" stop-opacity="0.85"/>
      </linearGradient>
      <linearGradient id="grad-clean" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#06d6a0" stop-opacity="0.9"/>
        <stop offset="100%" stop-color="#84cc16" stop-opacity="0.9"/>
      </linearGradient>
      <linearGradient id="grad-dq" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#ef476f" stop-opacity="0.9"/>
        <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.9"/>
      </linearGradient>
      <linearGradient id="grad-ml" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.9"/>
        <stop offset="100%" stop-color="#a855f7" stop-opacity="0.9"/>
      </linearGradient>
      <linearGradient id="grad-lineage" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#ec4899" stop-opacity="0.9"/>
        <stop offset="100%" stop-color="#f43f5e" stop-opacity="0.9"/>
      </linearGradient>
    `;
    this.svgLayer.appendChild(defs);

    this.routes.forEach((route, idx) => {
      const fromNode = this.nodes.find(n => n.id === route.from);
      const toNode = this.nodes.find(n => n.id === route.to);
      if (!fromNode || !toNode) return;

      const pathStr = this._calcBezierPath(fromNode, toNode);
      
      // Route track path (base background curve)
      const pathEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pathEl.setAttribute("d", pathStr);
      pathEl.setAttribute("class", `map-route-track route-${route.type}`);
      pathEl.dataset.from = route.from;
      pathEl.dataset.to = route.to;
      pathEl.dataset.index = idx;
      this.svgLayer.appendChild(pathEl);

      // Route pulse animated path
      const pulseEl = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pulseEl.setAttribute("d", pathStr);
      pulseEl.setAttribute("class", `map-route-pulse route-${route.type}`);
      pulseEl.dataset.from = route.from;
      pulseEl.dataset.to = route.to;
      this.svgLayer.appendChild(pulseEl);

      // Route Label if present
      if (route.label) {
        const midX = (fromNode.x + toNode.x) / 2;
        const midY = (fromNode.y + toNode.y) / 2 - 8;
        const textEl = document.createElementNS("http://www.w3.org/2000/svg", "text");
        textEl.setAttribute("x", midX);
        textEl.setAttribute("y", midY);
        textEl.setAttribute("class", `map-route-label label-${route.type}`);
        textEl.setAttribute("text-anchor", "middle");
        textEl.textContent = route.label;
        this.svgLayer.appendChild(textEl);
      }
    });
  }

  _calcBezierPath(from, to) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const cx1 = from.x + dx * 0.45;
    const cy1 = from.y;
    const cx2 = from.x + dx * 0.55;
    const cy2 = to.y;
    return `M ${from.x} ${from.y} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${to.x} ${to.y}`;
  }

  _renderNodes() {
    this.nodesContainer.innerHTML = "";

    this.nodes.forEach((node) => {
      const el = document.createElement("div");
      el.className = `map-node tier-${node.tier} layer-${node.layer}`;
      el.dataset.nodeId = node.id;
      el.style.left = `${node.x}px`;
      el.style.top = `${node.y}px`;

      let inner = `
        <div class="node-halo"></div>
        <div class="node-body">
          <div class="node-header">
            <span class="node-icon">${node.icon}</span>
            <span class="node-title">${node.label}</span>
          </div>
          <div class="node-status-row">
            <span class="node-status-dot"></span>
            <span class="node-status-text">${node.status}</span>
          </div>
          <div class="node-recs">${node.recs || ""}</div>
          <div class="node-live-counter mono" id="node-live-${node.id}"></div>
        </div>
      `;

      if (node.tier === "core") {
        inner = `
          <div class="core-hub-ring"></div>
          <div class="core-hub-ring ring-outer"></div>
          <div class="node-body core-body">
            <div class="core-header">
              <span class="core-icon">${node.icon}</span>
              <span class="core-title">${node.label}</span>
            </div>
            <span class="core-sub">${node.tech}</span>
            <div class="core-badge">100,000 OBS STORED</div>
            <div class="core-latency mono text-cyan">⚡ 0.15ms Query Scan</div>
          </div>
        `;
      }

      el.innerHTML = inner;
      el.addEventListener("click", () => this._onNodeClick(node));
      this.nodesContainer.appendChild(el);
    });
  }

  _onNodeClick(node) {
    this.activeNodeId = node.id;
    this.highlightTrace(node.id);
    if (this.onNodeSelected) {
      this.onNodeSelected(node.id);
    }
  }

  updateNodeMetric(nodeId, countStr) {
    const el = document.getElementById(`node-live-${nodeId}`);
    if (el) {
      el.textContent = countStr;
    }
  }

  highlightTrace(nodeId) {
    this.activeTraceNode = nodeId;
    const connectedNodeIds = new Set([nodeId]);
    const connectedRouteIndices = new Set();

    this.routes.forEach((r, idx) => {
      if (r.from === nodeId || r.to === nodeId) {
        connectedNodeIds.add(r.from);
        connectedNodeIds.add(r.to);
        connectedRouteIndices.add(idx);
      }
    });

    this.nodesContainer.querySelectorAll(".map-node").forEach(el => {
      const id = el.dataset.nodeId;
      if (id === nodeId) {
        el.classList.add("active-trace-target");
        el.classList.remove("dimmed");
      } else if (connectedNodeIds.has(id)) {
        el.classList.add("connected-trace");
        el.classList.remove("dimmed");
      } else {
        el.classList.add("dimmed");
        el.classList.remove("active-trace-target", "connected-trace");
      }
    });

    this.svgLayer.querySelectorAll(".map-route-track").forEach(el => {
      const idx = parseInt(el.dataset.index);
      if (connectedRouteIndices.has(idx)) {
        el.classList.add("trace-active");
        el.classList.remove("dimmed");
      } else {
        el.classList.add("dimmed");
        el.classList.remove("trace-active");
      }
    });
  }

  highlightLineageChain(chainNodeIds) {
    const idSet = new Set(chainNodeIds);
    this.nodesContainer.querySelectorAll(".map-node").forEach(el => {
      const id = el.dataset.nodeId;
      if (idSet.has(id)) {
        el.classList.add("lineage-chain-active");
        el.classList.remove("dimmed");
      } else {
        el.classList.add("dimmed");
        el.classList.remove("lineage-chain-active");
      }
    });

    this.svgLayer.querySelectorAll(".map-route-track").forEach(el => {
      const from = el.dataset.from;
      const to = el.dataset.to;
      if (idSet.has(from) && idSet.has(to)) {
        el.classList.add("trace-active", "lineage-route");
        el.classList.remove("dimmed");
      } else {
        el.classList.add("dimmed");
        el.classList.remove("trace-active", "lineage-route");
      }
    });
  }

  clearTrace() {
    this.activeTraceNode = null;
    this.nodesContainer.querySelectorAll(".map-node").forEach(el => {
      el.classList.remove("active-trace-target", "connected-trace", "lineage-chain-active", "dimmed");
    });
    this.svgLayer.querySelectorAll(".map-route-track").forEach(el => {
      el.classList.remove("trace-active", "lineage-route", "dimmed");
    });
  }

  setActive(index) {
    const stage = PIPELINE_STAGES[index];
    if (!stage) return;
    this.activeNodeId = stage.id;
    this._updateNodeClasses();
  }

  setActiveById(nodeId) {
    this.activeNodeId = nodeId;
    this._updateNodeClasses();
  }

  setCompleted(index) {
    const stage = PIPELINE_STAGES[index];
    if (stage) this.completedNodes.add(stage.id);
    this._updateNodeClasses();
  }

  setError(nodeId) {
    this.errorNodes.add(nodeId);
    this._updateNodeClasses();
  }

  clearError(nodeId) {
    this.errorNodes.delete(nodeId);
    this._updateNodeClasses();
  }

  setBottleneck(nodeId) {
    this.bottleneckNode = nodeId;
    this._updateNodeClasses();
  }

  clearBottleneck() {
    this.bottleneckNode = null;
    this._updateNodeClasses();
  }

  highlightStage(stageId) {
    this.panToNode(stageId, 1.2);
    this.highlightTrace(stageId);
  }

  reset() {
    this.activeNodeId = null;
    this.completedNodes.clear();
    this.errorNodes.clear();
    this.bottleneckNode = null;
    this.clearTrace();
    this.resetView();
    this.nodesContainer.querySelectorAll(".node-live-counter").forEach(el => el.textContent = "");
    this._updateNodeClasses();
  }

  _updateNodeClasses() {
    this.nodesContainer.querySelectorAll(".map-node").forEach((el) => {
      const id = el.dataset.nodeId;
      el.classList.remove("active", "completed", "error", "bottleneck");

      if (this.errorNodes.has(id)) {
        el.classList.add("error");
      } else if (this.bottleneckNode === id) {
        el.classList.add("bottleneck");
      } else if (id === this.activeNodeId) {
        el.classList.add("active");
      } else if (this.completedNodes.has(id)) {
        el.classList.add("completed");
      }
    });
  }
}
