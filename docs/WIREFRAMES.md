# Bocetos de interfaz (Wireframes) · LabCount

Tres pantallas principales, descritas en texto/ASCII. La UI real usa el
design system definido en `static/css/app.css` (tema oscuro, acento cian).

## 1. Landing / portada (`templates/core/landing.html`)

```
┌──────────────────────────────────────────────────────────────┐
│  [LabCount]                                    [Iniciar sesión] [Registrarse] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   Conteo de personas en el laboratorio                       │
│   Django + OpenCV + PostgreSQL · Tiempo real                 │
│                                                              │
│   [ Comenzar ]   [ Ver documentación ]                       │
│                                                              │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐            │
│   │ Video  │  │ Conteo │  │ Hist.  │  │ Report │            │
│   │ en vivo│  │ líneas │  │ sesion │  │  CSV   │            │
│   └────────┘  └────────┘  └────────┘  └────────┘            │
│                                                              │
│   Stack: Django 5.2 · OpenCV 4.14 · PostgreSQL 16            │
└──────────────────────────────────────────────────────────────┘
```

Elementos clave: hero con CTA, tarjetas de capacidades, pie con stack.
Visible sin autenticación; usuarios autenticados son redirigidos al panel.

## 2. Panel de monitoreo (`templates/monitoring/dashboard.html`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  [LabCount]  Panel   Sesiones   Reportes        [usuario] [Salir]   │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┐  ┌────────────────────────────┐  │
│  │                              │  │ Iniciar monitoreo          │  │
│  │   VIDEO EN VIVO (MJPEG)      │  │ Fuente: [○Cam][○Video]     │  │
│  │   con anotaciones OpenCV     │  │   [○Demo]                  │  │
│  │   (cajas, trayectorias, HUD) │  │ Método: [HOG|MOG2|Híbrido] │  │
│  │                              │  │ Línea: [Vert|Horiz] pos 0.5│  │
│  │                              │  │ [ Iniciar ] [ Capturar ]   │  │
│  └──────────────────────────────┘  │ [ Finalizar ]              │  │
│  ┌─ KPIs ──────────────────────┐  └────────────────────────────┘  │
│  │ En lab: 05  Entradas: 12    │  ┌────────────────────────────┐  │
│  │ Salidas: 7  Únicos: 9       │  │ Gráfica de ocupación       │  │
│  │ Pico: 8     FPS: 15.2      │  │ (Canvas, últimos 90 muestr.)│  │
│  └─────────────────────────────┘  └────────────────────────────┘  │
│  Sesiones recientes (tabla)                                      │
└─────────────────────────────────────────────────────────────────────┘
```

Elementos clave: video MJPEG a la izquierda, formulario de control a la
derecha, KPIs, gráfica Canvas, tabla de sesiones recientes. Polling a
`/monitoring/api/stats/` cada 2 s.

## 3. Historial de sesiones (`templates/monitoring/sessions.html` + detalle)

Listado:

```
┌──────────────────────────────────────────────────────────────┐
│  Historial de sesiones                                       │
│  Filtros: [estado ▾]  [buscar...]   [Exportar CSV]           │
├──────────────────────────────────────────────────────────────┤
│  ID │ Laboratorio │ Fuente │ Inicio │ Entradas │ Salidas │ … │
│  12 │ Lab P       │ Demo   │ 14:02  │ 5        │ 2       │ … │
│  ...                                                         │
│  Paginación: ◀ 1 2 3 ▶                                      │
└──────────────────────────────────────────────────────────────┘
```

Detalle (`session_detail.html`):

```
┌──────────────────────────────────────────────────────────────┐
│  Sesión #12 · Lab P · Demo · Finalizada                     │
│  KPIs: entradas, salidas, únicos, pico, duración             │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌─────────────────────────────┐  │
│  │ Gráfica de ocupación │  │ Capturas (thumbnails)       │  │
│  │ (Canvas)             │  │                             │  │
│  └──────────────────────┘  └─────────────────────────────┘  │
│  Eventos de cruce (tabla) · Exportar CSV de la sesión       │
└──────────────────────────────────────────────────────────────┘
```

Reportes (`templates/reports/index.html`): resumen agregado + accesos a
exportación CSV de sesiones y de una sesión específica.