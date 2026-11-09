/* LabCount · gráfica de ocupación dibujada con Canvas (sin dependencias) */
(function () {
  "use strict";

  const COLORS = {
    grid: "#e8eef5",
    text: "#94a3b8",
    line: "#0891b2",
    lineDark: "#0e7490",
    point: "#22d3ee",
    capacity: "#f59e0b",
    fillTop: "rgba(34, 211, 238, 0.22)",
    fillBottom: "rgba(34, 211, 238, 0.01)",
  };

  function parseTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      const match = String(value).match(/T(\d{2}:\d{2})/);
      return match ? match[1] : "";
    }
    return date.toLocaleTimeString("es-EC", { hour: "2-digit", minute: "2-digit", hour12: false });
  }

  class LabCountChart {
    constructor(canvas, options) {
      this.canvas = canvas;
      this.ctx = canvas.getContext("2d");
      this.options = options || {};
      this.capacity = Number(this.options.capacity) || 0;
      this.data = [];
      this.padding = { top: 22, right: 18, bottom: 30, left: 40 };
      this._resize = this._resize.bind(this);

      if (window.ResizeObserver) {
        this.observer = new ResizeObserver(this._resize);
        this.observer.observe(canvas.parentElement || canvas);
      } else {
        window.addEventListener("resize", this._resize);
      }
      this._resize();
    }

    setData(points) {
      this.data = (Array.isArray(points) ? points : [])
        .map((point) => ({
          t: point.t || point.time || "",
          y: Math.max(0, Number(point.y ?? point.occupancy ?? 0) || 0),
        }))
        .slice(-150);
      this.draw();
      return this;
    }

    append(point) {
      if (!point) return this;
      this.data.push({
        t: point.t || point.time || new Date().toISOString(),
        y: Math.max(0, Number(point.y ?? point.occupancy ?? 0) || 0),
      });
      if (this.data.length > 150) this.data.splice(0, this.data.length - 150);
      this.draw();
      return this;
    }

    _resize() {
      const parent = this.canvas.parentElement || this.canvas;
      const width = Math.max(280, parent.clientWidth || this.canvas.clientWidth || 300);
      const height = Math.max(200, parent.clientHeight || this.canvas.clientHeight || 240);
      const ratio = window.devicePixelRatio || 1;
      this.canvas.width = Math.round(width * ratio);
      this.canvas.height = Math.round(height * ratio);
      this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
      this.width = width;
      this.height = height;
      this.draw();
    }

    draw() {
      if (!this.ctx) return;
      const ctx = this.ctx;
      const width = this.width || this.canvas.clientWidth || 300;
      const height = this.height || this.canvas.clientHeight || 240;
      const { top, right, bottom, left } = this.padding;
      const plotWidth = Math.max(10, width - left - right);
      const plotHeight = Math.max(10, height - top - bottom);

      ctx.clearRect(0, 0, width, height);

      if (!this.data.length) {
        ctx.fillStyle = COLORS.text;
        ctx.font = '12px "Segoe UI", sans-serif';
        ctx.textAlign = "center";
        ctx.fillText("Recolectando datos de ocupación…", width / 2, height / 2);
        ctx.textAlign = "start";
        return;
      }

      const values = this.data.map((point) => point.y);
      const maxData = Math.max(...values, 0);
      let yMax = Math.max(5, Math.ceil(maxData * 1.28));
      const capacityVisible = this.capacity > 0 && this.capacity <= yMax * 1.3;
      if (capacityVisible) yMax = Math.max(yMax, this.capacity * 1.08);
      yMax = Math.ceil(yMax / 5) * 5;

      const xAt = (index) => {
        if (this.data.length === 1) return left + plotWidth / 2;
        return left + (plotWidth * index) / (this.data.length - 1);
      };
      const yAt = (value) => top + plotHeight - (Math.min(value, yMax) / yMax) * plotHeight;

      // Líneas horizontales y etiquetas del eje Y
      ctx.font = '10px "Segoe UI", sans-serif';
      ctx.fillStyle = COLORS.text;
      ctx.strokeStyle = COLORS.grid;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 5]);
      const steps = 4;
      for (let i = 0; i <= steps; i += 1) {
        const value = (yMax / steps) * i;
        const y = yAt(value);
        ctx.beginPath();
        ctx.moveTo(left, Math.round(y) + 0.5);
        ctx.lineTo(width - right, Math.round(y) + 0.5);
        ctx.stroke();
        ctx.textAlign = "right";
        ctx.fillText(String(Math.round(value)), left - 9, y + 3);
      }
      ctx.setLineDash([]);

      // Etiquetas del eje X
      const labelIndexes = new Set([0, Math.floor((this.data.length - 1) / 2), this.data.length - 1]);
      labelIndexes.forEach((index) => {
        const x = xAt(index);
        ctx.fillStyle = COLORS.text;
        ctx.textAlign = index === 0 ? "left" : index === this.data.length - 1 ? "right" : "center";
        ctx.fillText(parseTime(this.data[index].t), x, height - 8);
      });

      // Área bajo la curva
      const gradient = ctx.createLinearGradient(0, top, 0, top + plotHeight);
      gradient.addColorStop(0, COLORS.fillTop);
      gradient.addColorStop(1, COLORS.fillBottom);
      ctx.beginPath();
      ctx.moveTo(xAt(0), yAt(this.data[0].y));
      for (let i = 1; i < this.data.length; i += 1) {
        const prevX = xAt(i - 1);
        const prevY = yAt(this.data[i - 1].y);
        const x = xAt(i);
        const y = yAt(this.data[i].y);
        const midX = (prevX + x) / 2;
        ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
      }
      ctx.lineTo(xAt(this.data.length - 1), top + plotHeight);
      ctx.lineTo(xAt(0), top + plotHeight);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Línea principal
      ctx.beginPath();
      ctx.moveTo(xAt(0), yAt(this.data[0].y));
      for (let i = 1; i < this.data.length; i += 1) {
        const prevX = xAt(i - 1);
        const prevY = yAt(this.data[i - 1].y);
        const x = xAt(i);
        const y = yAt(this.data[i].y);
        const midX = (prevX + x) / 2;
        ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
      }
      ctx.strokeStyle = COLORS.line;
      ctx.lineWidth = 2.25;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.stroke();

      // Línea de aforo
      if (capacityVisible) {
        const capY = yAt(this.capacity);
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = COLORS.capacity;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left, capY);
        ctx.lineTo(width - right, capY);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = COLORS.capacity;
        ctx.font = '9px "Segoe UI", sans-serif';
        ctx.textAlign = "left";
        ctx.fillText(`Aforo ${this.capacity}`, left + 5, capY - 5);
      }

      // Punto actual
      const lastX = xAt(this.data.length - 1);
      const lastY = yAt(this.data[this.data.length - 1].y);
      ctx.beginPath();
      ctx.arc(lastX, lastY, 7, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(34, 211, 238, 0.16)";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(lastX, lastY, 3.4, 0, Math.PI * 2);
      ctx.fillStyle = COLORS.lineDark;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "#ffffff";
      ctx.stroke();
    }
  }

  window.LabCountChart = LabCountChart;
})();
