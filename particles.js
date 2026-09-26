/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Network Map Data Batch Packet System
   High-performance canvas particle animation following Bezier routes
   ═══════════════════════════════════════════════════════════════════ */

class NetworkParticleSystem {
  constructor(canvasId, mapRenderer) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.map = mapRenderer;
    this.packets = [];
    this.running = false;
    this.spawnRate = 1.0;
    this.frameCount = 0;
    this.activeStageIndex = -1;
    this.scaleFactor = 1.0;

    this.routes = mapRenderer.routes;
    this.nodes = mapRenderer.nodes;
    this.animating = false;

    this._loop();
  }

  start(throughput = 22215) {
    this.spawnRate = Math.min(4.0, Math.max(0.5, throughput / 5000)) * this.scaleFactor;
    this.running = true;
  }

  stop() {
    this.running = false;
  }

  clear() {
    this.packets = [];
    this.running = false;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  setScale(scaleMultiplier) {
    this.scaleFactor = scaleMultiplier;
  }

  setActiveStage(index) {
    this.activeStageIndex = index;
  }

  _spawnPacket() {
    if (this.packets.length >= 80) return;

    // Pick a route to spawn a batch packet on
    const activeRouteIndex = Math.floor(Math.random() * this.routes.length);
    const route = this.routes[activeRouteIndex];
    const fromNode = this.nodes.find(n => n.id === route.from);
    const toNode = this.nodes.find(n => n.id === route.to);

    if (!fromNode || !toNode) return;

    const batchNum = Math.floor(Math.random() * 90 + 10);
    const recCount = route.type === "dq" ? "158 RECS" : (route.type === "clean" ? "9,842 RECS" : "10,000 RECS");

    let color = "#06d6a0"; // Default Emerald
    if (route.type === "clean") color = "#84cc16";
    else if (route.type === "dq") color = "#ef476f";
    else if (route.type === "ml") color = "#8b5cf6";
    else if (route.type === "lineage") color = "#ec4899";
    else if (route.type === "ai") color = "#06b6d4";

    this.packets.push({
      from: fromNode,
      to: toNode,
      t: 0, // 0.0 to 1.0 along Bezier path
      speed: (0.006 + Math.random() * 0.008) * this.scaleFactor,
      color: color,
      batchNum: batchNum,
      recCount: recCount,
      type: route.type,
      trail: []
    });
  }

  _loop() {
    requestAnimationFrame(() => this._loop());

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.frameCount++;

    if (this.running) {
      if (Math.random() < this.spawnRate * 0.3) {
        this._spawnPacket();
      }
    }

    // Update and draw packets
    for (let i = this.packets.length - 1; i >= 0; i--) {
      const p = this.packets[i];
      p.t += p.speed;

      // Calculate Bezier coordinates (x, y)
      const pos = this._getBezierPoint(p.from, p.to, p.t);
      p.x = pos.x;
      p.y = pos.y;

      // Record trail
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 10) p.trail.shift();

      // Draw Packet Trail
      if (p.trail.length > 1) {
        this.ctx.beginPath();
        this.ctx.moveTo(p.trail[0].x, p.trail[0].y);
        for (let j = 1; j < p.trail.length; j++) {
          this.ctx.lineTo(p.trail[j].x, p.trail[j].y);
        }
        this.ctx.strokeStyle = p.color;
        this.ctx.lineWidth = 2.5;
        this.ctx.globalAlpha = 0.3;
        this.ctx.stroke();
      }

      // Draw Packet Head
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = 0.9;
      this.ctx.fill();

      // Glow Ring
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, 9, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = 0.15;
      this.ctx.fill();

      // Batch Data Label
      this.ctx.fillStyle = "#ffffff";
      this.ctx.font = "bold 8px 'JetBrains Mono'";
      this.ctx.textAlign = "left";
      this.ctx.globalAlpha = 0.85;
      this.ctx.fillText(`● BATCH ${p.batchNum}`, p.x + 8, p.y - 3);

      this.ctx.fillStyle = p.color;
      this.ctx.font = "8px 'JetBrains Mono'";
      this.ctx.fillText(p.recCount, p.x + 8, p.y + 7);

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

// Global particle alias for backwards compatibility
class ParticleSystem extends NetworkParticleSystem {
  constructor(canvasId) {
    super(canvasId, window.pipelineInstance || { routes: [], nodes: [] });
  }
}
