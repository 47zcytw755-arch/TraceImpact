/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Pipeline Stage Rendering & Animation
   ═══════════════════════════════════════════════════════════════════ */

class PipelineRenderer {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.stages = PIPELINE_STAGES;
    this.activeIndex = -1;
    this.completedSet = new Set();
    this.errorSet = new Set();
    this.nodeElements = [];
    this.connectorElements = [];
    this._render();
  }

  _render() {
    this.container.innerHTML = "";
    this.nodeElements = [];
    this.connectorElements = [];

    this.stages.forEach((stage, i) => {
      const node = document.createElement("div");
      node.className = "stage-node";
      node.dataset.stageId = stage.id;
      node.dataset.index = i;
      node.innerHTML = `
        <div class="stage-indicator"></div>
        <span class="stage-label">${stage.icon} ${stage.label}</span>
      `;
      node.addEventListener("click", () => this._onStageClick(i));
      this.container.appendChild(node);
      this.nodeElements.push(node);

      if (i < this.stages.length - 1) {
        const conn = document.createElement("div");
        conn.className = "stage-connector";
        this.container.appendChild(conn);
        this.connectorElements.push(conn);
      }
    });
  }

  _onStageClick(index) {
    const stage = this.stages[index];
    const detail = document.getElementById("stage-detail");
    const title = document.getElementById("detail-title");
    const body = document.getElementById("detail-body");

    title.textContent = `${stage.icon} ${stage.label}`;
    let html = `<p style="margin-bottom:10px;color:var(--text-primary)">${stage.detail.description}</p>`;
    stage.detail.specs.forEach(s => {
      html += `<div class="detail-row">
        <span class="detail-label">${s.label}</span>
        <span class="detail-value">${s.value}</span>
      </div>`;
    });
    body.innerHTML = html;
    detail.classList.remove("hidden");
  }

  setActive(index) {
    this.activeIndex = index;
    this._updateClasses();
  }

  setCompleted(index) {
    this.completedSet.add(index);
    this._updateClasses();
  }

  setError(index) {
    this.errorSet.add(index);
    this._updateClasses();
  }

  clearError(index) {
    this.errorSet.delete(index);
    this._updateClasses();
  }

  highlightStage(stageId) {
    const idx = this.stages.findIndex(s => s.id === stageId);
    if (idx >= 0) {
      this.setActive(idx);
      // Scroll into view if needed
      this.nodeElements[idx]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  reset() {
    this.activeIndex = -1;
    this.completedSet.clear();
    this.errorSet.clear();
    this._updateClasses();
  }

  _updateClasses() {
    this.nodeElements.forEach((node, i) => {
      node.classList.remove("active", "completed", "error");
      if (this.errorSet.has(i)) {
        node.classList.add("error");
      } else if (i === this.activeIndex) {
        node.classList.add("active");
      } else if (this.completedSet.has(i)) {
        node.classList.add("completed");
      }
    });
    this.connectorElements.forEach((conn, i) => {
      conn.classList.toggle("lit", this.completedSet.has(i) || i < this.activeIndex);
    });
  }

  getStagePosition(index) {
    const node = this.nodeElements[index];
    if (!node) return null;
    const rect = node.getBoundingClientRect();
    const canvasRect = this.container.closest("#pipeline-canvas").getBoundingClientRect();
    return {
      x: rect.left - canvasRect.left + rect.width / 2,
      y: rect.top - canvasRect.top + rect.height / 2
    };
  }
}
