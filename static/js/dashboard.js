/* LabCount · panel en vivo y formulario de inicio */
(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);

  /* ------------------------------------------------------------------
     Formulario de configuración
     ------------------------------------------------------------------ */
  const startForm = $("#startForm");
  if (startForm) {
    const radios = Array.from(startForm.querySelectorAll('input[name="source_type"]'));
    const panels = Array.from(startForm.querySelectorAll("[data-source-panel]"));
    const labels = Array.from(startForm.querySelectorAll("[data-source-label]"));
    const fileInput = startForm.querySelector('input[type="file"]');
    const fileName = startForm.querySelector("[data-file-name]");
    const range = $("#linePosition");
    const rangeOutput = $("#linePositionValue");

    const refreshSource = () => {
      const selected = radios.find((radio) => radio.checked);
      const value = selected ? selected.value : "webcam";
      labels.forEach((label) => {
        label.classList.toggle("selected", label.dataset.sourceLabel === value);
      });
      panels.forEach((panel) => {
        panel.hidden = panel.dataset.sourcePanel !== value;
      });
    };

    radios.forEach((radio) => radio.addEventListener("change", refreshSource));
    refreshSource();

    if (fileInput && fileName) {
      fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
          fileName.textContent = "Seleccionar un video";
          return;
        }
        const megabytes = (file.size / (1024 * 1024)).toFixed(1);
        fileName.textContent = `${file.name} · ${megabytes} MB`;
      });
    }

    if (range && rangeOutput) {
      const refreshRange = () => {
        rangeOutput.textContent = Number(range.value).toFixed(2);
      };
      range.addEventListener("input", refreshRange);
      refreshRange();
    }
  }

  /* ------------------------------------------------------------------
     Panel en vivo
     ------------------------------------------------------------------ */
  const config = $("#dashboardConfig");
  if (!config || config.dataset.live !== "true") return;

  const statsUrl = config.dataset.statsUrl;

  /* ------------------------------------------------------------------
     Pantalla completa de la cámara
     ------------------------------------------------------------------ */
  const videoShell = $("#videoShell");
  if (videoShell) {
    const fsElement = () =>
      document.fullscreenElement || document.webkitFullscreenElement || null;
    const isFullscreen = () => fsElement() === videoShell;
    const enter = () => {
      const request = videoShell.requestFullscreen || videoShell.webkitRequestFullscreen;
      if (request) {
        const result = request.call(videoShell);
        if (result && result.catch) result.catch(() => videoShell.classList.add("is-pseudo-fullscreen"));
      } else {
        // Navegadores sin API: se simula ocupando toda la ventana.
        videoShell.classList.add("is-pseudo-fullscreen");
        refreshFullscreen();
      }
    };
    const exit = () => {
      if (videoShell.classList.contains("is-pseudo-fullscreen")) {
        videoShell.classList.remove("is-pseudo-fullscreen");
        refreshFullscreen();
        return;
      }
      const leave = document.exitFullscreen || document.webkitExitFullscreen;
      if (leave && fsElement()) leave.call(document);
    };
    const active = () => isFullscreen() || videoShell.classList.contains("is-pseudo-fullscreen");
    const toggle = () => (active() ? exit() : enter());

    function refreshFullscreen() {
      const on = active();
      videoShell.classList.toggle("is-fullscreen", on);
      document.body.classList.toggle("video-fullscreen-open", on);
      document.querySelectorAll("[data-fullscreen-label]").forEach((label) => {
        label.textContent = on ? "Salir de pantalla completa" : "Pantalla completa";
      });
      const button = $("#fullscreenToggle");
      if (button) {
        const text = on ? "Salir de pantalla completa (Esc)" : "Pantalla completa (F)";
        button.setAttribute("aria-label", text);
        button.title = text;
      }
    }

    document.addEventListener("fullscreenchange", refreshFullscreen);
    document.addEventListener("webkitfullscreenchange", refreshFullscreen);
    document.querySelectorAll("[data-fullscreen-toggle], #fullscreenToggle").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        toggle();
      });
    });
    videoShell.addEventListener("dblclick", toggle);
    document.addEventListener("keydown", (event) => {
      const tag = (event.target && event.target.tagName) || "";
      if (["INPUT", "TEXTAREA", "SELECT"].includes(tag) || event.ctrlKey || event.metaKey || event.altKey) return;
      if (event.key === "f" || event.key === "F") {
        event.preventDefault();
        toggle();
      } else if (event.key === "Escape" && videoShell.classList.contains("is-pseudo-fullscreen")) {
        exit();
      }
    });
  }
  const chartCanvas = $("#liveChart");
  const chart = chartCanvas
    ? new window.LabCountChart(chartCanvas, {
        capacity: Number(chartCanvas.dataset.capacity) || 0,
      })
    : null;

  const historyElement = $("#live-history");
  if (chart && historyElement) {
    try {
      chart.setData(JSON.parse(historyElement.textContent || "[]"));
    } catch (error) {
      chart.setData([]);
    }
  }

  const elements = {
    current: $("#currentCount"),
    peak: $("#peakCount"),
    elapsed: $("#elapsedTime"),
    entries: $("#entriesCount"),
    exits: $("#exitsCount"),
    unique: $("#uniqueCount"),
    fps: $("#fpsValue"),
    detections: $("#detectionsValue"),
    streamFps: $("#streamFps"),
    percent: $("#occupancyPercent"),
    status: $("#occupancyStatus"),
    note: $("#occupancyNote"),
    bar: $("#occupancyBar"),
    ring: $("#occupancyRing"),
  };

  const setText = (element, value) => {
    if (element && value !== undefined && value !== null) element.textContent = value;
  };

  let stopped = false;
  let timer = null;

  const update = (data) => {
    const current = Number(data.current) || 0;
    const capacity = Number(data.capacity) || 0;
    const percent = capacity ? Math.min(100, Math.max(0, (current / capacity) * 100)) : 0;
    const percentLabel = capacity ? percent.toFixed(1) : "0.0";

    setText(elements.current, String(current).padStart(2, "0"));
    setText(elements.peak, data.peak ?? 0);
    setText(elements.elapsed, data.elapsed || "00:00");
    setText(elements.entries, data.entries ?? 0);
    setText(elements.exits, data.exits ?? 0);
    setText(elements.unique, data.unique ?? 0);
    setText(elements.fps, data.fps ?? 0);
    setText(elements.detections, data.detections ?? 0);
    setText(elements.streamFps, `${data.fps ?? 0} FPS`);
    setText(elements.percent, `${percentLabel}% del aforo`);

    if (elements.bar) elements.bar.style.width = `${percent}%`;
    if (elements.ring) elements.ring.style.setProperty("--pct", percent.toString());

    let statusText = "Dentro del límite";
    let statusColor = "";
    if (capacity && current >= capacity) {
      statusText = "Aforo excedido";
      statusColor = "var(--danger)";
    } else if (capacity && current >= capacity * 0.8) {
      statusText = "Cerca del límite";
      statusColor = "var(--warning)";
    } else {
      statusColor = "var(--success)";
    }
    if (elements.status) {
      elements.status.textContent = statusText;
      elements.status.style.color = statusColor;
    }

    if (data.db_ok === false) {
      setText(
        elements.note,
        "Base de datos no disponible: el video sigue en vivo, pero las muestras no se están guardando."
      );
      elements.note.style.color = "var(--warning)";
    } else if (data.error) {
      setText(elements.note, `Error del procesador: ${data.error}`);
      elements.note.style.color = "var(--danger)";
    } else {
      const now = data.server_time || new Date().toLocaleTimeString("es-EC", { hour12: false });
      setText(
        elements.note,
        `Actualizado a las ${now} · ${data.detector || "OpenCV"} procesando en tiempo real.`
      );
      elements.note.style.color = "";
    }

    if (chart) chart.setData(data.history || []);
  };

  const finish = () => {
    if (stopped) return;
    stopped = true;
    if (timer) clearTimeout(timer);
    const badge = document.querySelector(".status-live");
    if (badge) {
      badge.classList.remove("status-live");
      badge.classList.add("status-idle");
      badge.innerHTML = '<span class="dot"></span> Sesión finalizada';
    }
    setText(elements.note, "La sesión finalizó. Actualizando el panel…");
    setTimeout(() => window.location.reload(), 1400);
  };

  const poll = async () => {
    try {
      const response = await fetch(statsUrl, {
        headers: { Accept: "application/json" },
        cache: "no-store",
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      update(data);
      if (!data.running) {
        finish();
        return;
      }
    } catch (error) {
      if (elements.note) {
        elements.note.textContent = "Reconectando con el servidor de video…";
        elements.note.style.color = "var(--warning)";
      }
    }
    if (!stopped) timer = setTimeout(poll, 1200);
  };

  poll();

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && !stopped) {
      if (timer) clearTimeout(timer);
      poll();
    }
  });
})();
