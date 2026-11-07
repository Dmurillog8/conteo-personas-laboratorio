/* LabCount · utilidades generales de la interfaz */
(function () {
  "use strict";

  const $ = (selector, scope) => (scope || document).querySelector(selector);
  const $$ = (selector, scope) => Array.from((scope || document).querySelectorAll(selector));

  /* Reloj del encabezado -------------------------------------------------- */
  const clock = $("#topbarClock");
  if (clock) {
    const tick = () => {
      const now = new Date();
      clock.textContent = now.toLocaleTimeString("es-EC", { hour12: false });
    };
    tick();
    setInterval(tick, 1000);
  }

  /* Año del pie de página -------------------------------------------------- */
  const year = $("#footerYear");
  if (year) year.textContent = new Date().getFullYear();

  /* Menú lateral móvil ------------------------------------------------------ */
  const sidebar = $("#sidebar");
  const toggle = $("#sidebarToggle");
  const backdrop = $("#sidebarBackdrop");

  const closeSidebar = () => {
    if (!sidebar) return;
    sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("visible");
    document.body.style.overflow = "";
  };

  if (toggle && sidebar) {
    toggle.addEventListener("click", () => {
      const open = sidebar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("visible", open);
      document.body.style.overflow = open ? "hidden" : "";
    });
  }
  if (backdrop) backdrop.addEventListener("click", closeSidebar);
  $$(".sidebar .nav-link").forEach((link) => link.addEventListener("click", closeSidebar));
  window.addEventListener("resize", () => {
    if (window.innerWidth > 900) closeSidebar();
  });

  /* Mensajes --------------------------------------------------------------- */
  $$(".alert").forEach((alert) => {
    const close = $(".alert-close", alert);
    if (close) {
      close.addEventListener("click", () => {
        alert.style.transition = "opacity 180ms ease, transform 180ms ease";
        alert.style.opacity = "0";
        alert.style.transform = "translateY(-4px)";
        setTimeout(() => alert.remove(), 190);
      });
    }
    if (alert.classList.contains("alert-success")) {
      setTimeout(() => {
        if (!alert.isConnected) return;
        alert.style.transition = "opacity 300ms ease";
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 320);
      }, 7000);
    }
  });

  /* Confirmación de acciones destructivas ---------------------------------- */
  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.dataset.confirm || "¿Confirma esta acción?";
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  /* Mostrar / ocultar contraseña ------------------------------------------- */
  $$("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (!input) return;
      const visible = input.type === "text";
      input.type = visible ? "password" : "text";
      button.textContent = visible ? "Ver" : "Ocultar";
    });
  });

  /* Evita envíos duplicados ------------------------------------------------ */
  $$("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (event.defaultPrevented) return;
      const submit = form.querySelector('button[type="submit"]');
      if (!submit) return;
      setTimeout(() => {
        submit.disabled = true;
        submit.style.opacity = "0.65";
      }, 30);
    });
  });

  window.LabCount = window.LabCount || {};
  window.LabCount.formatDuration = function (seconds) {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const pad = (value) => String(value).padStart(2, "0");
    return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  };
})();
