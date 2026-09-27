/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Network Map Data Batch Packet System
   Bounded canvas particle animation following Bezier routes with
   dynamic batch sizing, stream splitting, and zero memory leaks.
   ═══════════════════════════════════════════════════════════════════ */

class NetworkParticleSystem {
  constructor(canvasId, mapRenderer) {
    this.canvas = typeof canvasId === "string" ? document.getElementById(canvasId) : canvasId;
    this.ctx = this.canvas ? this.canvas.getContext("2d") : null;
    this.map = mapRenderer;
    this.packets = [];
    this.running = false;
    this.spawnRate = 1.0;
    this.frameCount = 0;
    this.scaleFactor = 1.0;
    this.speedMultiplier = 1.0;
    this.batchRecordLabel = "1,000 RECS";
    this.reducedMotion = false;
    this.animationId = null;

    this.routes = mapRenderer ? mapRenderer.routes : [];
    this.nodes = mapRenderer ? mapRenderer.nodes : [];

    // Check system prefers-reduced-motion
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      this.reducedMotion = true;
    }

    this._startLoop();
  }

  setSpeed(multiplier) {
    this.speedMultiplier = Math.max(0.2, Math.min(10.0, multiplier));
  }

  setBatchSize(batchSizeStr) {
    this.batchRecordLabel = batchSizeStr;
  }

  setReducedMotion(enabled) {
    this.reducedMotion = !!enabled;
    if (this.reducedMotion) {
      this.clear();
    }
  }

  start(throughput = 22215) {
    this.spawnRate = Math.min(3.5, Math.max(0.6, throughput / 6000));
    this.running = true;
  }

  pause() {
    this.running = false;
  }

  resume() {
    this.running = true;
  }

  stop() {
    this.running = false;
  }

  clear() {
    this.packets = [];
    this.running = false;
    if (this.ctx && this.canvas) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }

  setScale(scaleMultiplier, batchLabel) {
    this.scaleFactor = scaleMultiplier;
    if (batchLabel) this.batchRecordLabel = batchLabel;
  }

  _spawnPacket() {
    if (this.reducedMotion || !this.routes || this.routes.length === 0) return;
    if (this.packets.length >= 65) return; // Bounded packet pool (no infinite accumulation)

    // Weighted route selection
    const activeRouteIndex = Math.floor(Math.random() * this.routes.length);
    const route = this.routes[activeRouteIndex];
    const fromNode = this.nodes.find(n => n.id === route.from);
    const toNode = this.nodes.find(n => n.id === route.to);

    if (!fromNode || !toNode) return;

    const batchNum = Math.floor(Math.random() * 900 + 100);
    let recCount = this.batchRecordLabel;

    // Color by route semantic type
    let color = "#06d6a0"; // Default Emerald
    if (route.type === "clean") {
      color = "#84cc16";
      recCount = "993 RECS";
    } else if (route.type === "dq") {
      color = "#ef476f";
      recCount = "7 RECS [FLAGGED]";
    } else if (route.type === "ml") {
      color = "#8b5cf6";
      recCount = "40 ANOMALIES";
    } else if (route.type === "lineage") {
      color = "#ec4899";
      recCount = "SHA-256 PROOF";
    } else if (route.type === "ai") {
      color = "#06b6d4";
      recCount = "AI REPORT";
    } else if (route.type === "control") {
      color = "#0ea5e9";
      recCount = "CRON SYNC";
    }

    this.packets.push({
      from: fromNode,
      to: toNode,
      t: 0,
      speed: (0.007 + Math.random() * 0.006) * this.speedMultiplier,
      color: color,
      batchNum: batchNum,
      recCount: recCount,
      type: route.type,
      trail: []
    });
  }

  _startLoop() {
    const render = () => {
      this._updateAndDraw();
      this.animationId = requestAnimationFrame(render);
    };
    this.animationId = requestAnimationFrame(render);
  }

  destroy() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
    this.clear();
  }

  _updateAndDraw() {
    if (!this.ctx || !this.canvas) return;

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.frameCount++;

    if (this.running && !this.reducedMotion) {
      if (Math.random() < this.spawnRate * 0.35) {
        this._spawnPacket();
      }
    }

    if (this.reducedMotion) return;

    // Process active data packets
    for (let i = this.packets.length - 1; i >= 0; i--) {
      const p = this.packets[i];
      p.t += p.speed * this.speedMultiplier;

      // Calculate Bezier coordinates (x, y)
      const pos = this._getBezierPoint(p.from, p.to, p.t);
      p.x = pos.x;
      p.y = pos.y;

      // Record particle tail
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 8) p.trail.shift();

      // 1. Draw glowing packet trail
      if (p.trail.length > 1) {
        this.ctx.beginPath();
        this.ctx.moveTo(p.trail[0].x, p.trail[0].y);
        for (let j = 1; j < p.trail.length; j++) {
          this.ctx.lineTo(p.trail[j].x, p.trail[j].y);
        }
        this.ctx.strokeStyle = p.color;
        this.ctx.lineWidth = 2.0;
        this.ctx.globalAlpha = 0.28;
        this.ctx.stroke();
      }

      // 2. Draw Packet Center Core
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = 0.95;
      this.ctx.fill();

      // 3. Draw Outer Pulse Ring
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = 0.15;
      this.ctx.fill();

      // 4. Batch Label
      this.ctx.fillStyle = "#ffffff";
      this.ctx.font = "bold 8.5px 'JetBrains Mono', monospace";
      this.ctx.textAlign = "left";
      this.ctx.globalAlpha = 0.9;
      this.ctx.fillText(`BATCH #${p.batchNum}`, p.x + 9, p.y - 3);

      this.ctx.fillStyle = p.color;
      this.ctx.font = "8px 'JetBrains Mono', monospace";
      this.ctx.fillText(p.recCount, p.x + 9, p.y + 7);

      this.ctx.globalAlpha = 1.0;

      // Remove when reached destination
      if (p.t >= 1.0) {
        this.packets.splice(i, 1);
      }
    }
  }

  _getBezierPoint(from, to, t) {
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const cx1 = from.x + dx * 0.45;
    const cy1 = from.y;
    const cx2 = from.x + dx * 0.55;
    const cy2 = to.y;

    const u = 1 - t;
    const tt = t * t;
    const uu = u * u;
    const uuu = uu * u;
    const ttt = tt * t;

    const x = uuu * from.x + 3 * uu * t * cx1 + 3 * u * tt * cx2 + ttt * to.x;
    const y = uuu * from.y + 3 * uu * t * cy1 + 3 * u * tt * cy2 + ttt * to.y;

    return { x, y };
  }
}

// Global alias for compatibility
class ParticleSystem extends NetworkParticleSystem {
  constructor(canvasId) {
    super(canvasId, window.pipelineInstance || { routes: [], nodes: [] });
  }
}
