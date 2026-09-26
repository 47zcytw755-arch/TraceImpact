/* ═══════════════════════════════════════════════════════════════════
   TraceImpact 2.0 — Particle System for Pipeline Flow Visualization
   High-performance canvas-based particle animation
   ═══════════════════════════════════════════════════════════════════ */

class ParticleSystem {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext("2d");
    this.particles = [];
    this.running = false;
    this.maxParticles = 60;
    this.spawnRate = 0;  // particles per frame
    this.frameCount = 0;
    this.activeStageIndex = -1;
    this.totalStages = PIPELINE_STAGES.length;
    this._resize();
    window.addEventListener("resize", () => this._resize());
  }

  _resize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    this.canvas.width = rect.width * window.devicePixelRatio;
    this.canvas.height = rect.height * window.devicePixelRatio;
    this.canvas.style.width = rect.width + "px";
    this.canvas.style.height = rect.height + "px";
    this.ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    this.width = rect.width;
    this.height = rect.height;
  }

  start(throughput) {
    // throughput: simulated records/sec → controls spawn rate
    this.spawnRate = Math.min(3, Math.max(0.3, throughput / 8000));
    this.running = true;
    if (!this._animating) {
      this._animating = true;
      this._loop();
    }
  }

  stop() {
    this.running = false;
  }

  clear() {
    this.particles = [];
    this.running = false;
    this.ctx.clearRect(0, 0, this.width, this.height);
  }

  setActiveStage(index) {
    this.activeStageIndex = index;
  }

  _spawn() {
    if (this.particles.length >= this.maxParticles) return;

    const stageColors = PIPELINE_STAGES.map(s => s.color);
    const startY = 10;
    const endY = this.height - 10;
    const x = 14 + Math.random() * 6; // near the left indicator column

    // Determine which color to use based on active stage
    const colorIdx = this.activeStageIndex >= 0
      ? this.activeStageIndex
      : Math.floor(Math.random() * stageColors.length);

    this.particles.push({
      x: x,
      y: startY,
      targetY: endY,
      speed: 0.8 + Math.random() * 1.6,
      radius: 1.5 + Math.random() * 1.5,
      color: stageColors[colorIdx % stageColors.length],
      alpha: 0.6 + Math.random() * 0.4,
      trail: []
    });
  }

  _loop() {
    if (!this._animating) return;
    requestAnimationFrame(() => this._loop());

    this.ctx.clearRect(0, 0, this.width, this.height);
    this.frameCount++;

    if (this.running) {
      // Spawn particles
      const spawnThisFrame = this.spawnRate >= 1
        ? Math.floor(this.spawnRate)
        : (Math.random() < this.spawnRate ? 1 : 0);

      for (let i = 0; i < spawnThisFrame; i++) {
        this._spawn();
      }
    }

    // Update & draw
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.y += p.speed;

      // Record trail
      p.trail.push({ x: p.x, y: p.y });
      if (p.trail.length > 8) p.trail.shift();

      // Draw trail
      if (p.trail.length > 1) {
        this.ctx.beginPath();
        this.ctx.strokeStyle = p.color;
        this.ctx.lineWidth = p.radius * 0.6;
        this.ctx.globalAlpha = p.alpha * 0.15;
        this.ctx.moveTo(p.trail[0].x, p.trail[0].y);
        for (let j = 1; j < p.trail.length; j++) {
          this.ctx.lineTo(p.trail[j].x, p.trail[j].y);
        }
        this.ctx.stroke();
      }

      // Draw particle
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = p.color;
      this.ctx.globalAlpha = p.alpha;
      this.ctx.fill();

      // Glow
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius * 3, 0, Math.PI * 2);
      const grad = this.ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.radius * 3);
      grad.addColorStop(0, p.color);
      grad.addColorStop(1, "transparent");
      this.ctx.fillStyle = grad;
      this.ctx.globalAlpha = p.alpha * 0.15;
      this.ctx.fill();

      this.ctx.globalAlpha = 1;

      // Remove if past bottom
      if (p.y > p.targetY + 20) {
        this.particles.splice(i, 1);
      }
    }
  }
}
