// Genera Plan_Monetizacion.docx desde cero usando docx-js.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageBreak,
} = require("docx");

// Helpers ---------------------------------------------------------------------
const FONT = "Calibri";

const p = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: 120 },
    ...opts,
    children: [new TextRun({ text, font: FONT, size: 22, ...(opts.run || {}) })],
  });

const h1 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, font: FONT, size: 36, bold: true })],
  });

const h2 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: FONT, size: 28, bold: true })],
  });

const h3 = (text) =>
  new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, font: FONT, size: 24, bold: true })],
  });

const bullet = (text, level = 0) =>
  new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });

const bulletRich = (children, level = 0) =>
  new Paragraph({
    numbering: { reference: "bullets", level },
    spacing: { after: 80 },
    children,
  });

const bold = (text) => new TextRun({ text, font: FONT, size: 22, bold: true });
const reg = (text) => new TextRun({ text, font: FONT, size: 22 });

const num = (text) =>
  new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });

// Table helpers ---------------------------------------------------------------
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

const cell = (text, opts = {}) =>
  new TableCell({
    borders,
    width: { size: opts.width, type: WidthType.DXA },
    shading: opts.header
      ? { fill: "2C4A52", type: ShadingType.CLEAR }
      : { fill: "FFFFFF", type: ShadingType.CLEAR },
    margins: { top: 100, bottom: 100, left: 140, right: 140 },
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text,
            font: FONT,
            size: 22,
            bold: !!opts.header,
            color: opts.header ? "FFFFFF" : "000000",
          }),
        ],
      }),
    ],
  });

const buildTable = (columnWidths, headerRow, dataRows) => {
  const total = columnWidths.reduce((a, b) => a + b, 0);
  const rows = [
    new TableRow({
      tableHeader: true,
      children: headerRow.map((t, i) =>
        cell(t, { width: columnWidths[i], header: true })
      ),
    }),
    ...dataRows.map(
      (row) =>
        new TableRow({
          children: row.map((t, i) => cell(t, { width: columnWidths[i] })),
        })
    ),
  ];
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths,
    rows,
  });
};

// Document content ------------------------------------------------------------
const cover = [
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 2400, after: 240 },
    children: [
      new TextRun({
        text: "Plan de Monetización",
        font: FONT,
        size: 56,
        bold: true,
        color: "1F2A38",
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [
      new TextRun({
        text: "Mental Equilibrio — canales de filosofía práctica",
        font: FONT,
        size: 28,
        italics: true,
        color: "555555",
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 360, after: 360 },
    children: [
      new TextRun({
        text: "Estrategia integral para llevar contenido reflexivo automatizado a ingresos sostenibles",
        font: FONT,
        size: 22,
        color: "777777",
      }),
    ],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 1600 },
    children: [
      new TextRun({ text: "Versión inicial · Junio 2026", font: FONT, size: 20, color: "888888" }),
    ],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

const summary = [
  h1("Resumen ejecutivo"),
  p(
    "Este documento define la ruta para monetizar los canales sociales de Mental Equilibrio tan pronto como sea razonable, sin sacrificar el tono editorial sereno que sostiene la marca. Se asume un sistema de generación automatizado ya operativo (agentes, RAG, pipelines de imagen y video, panel de administración)."
  ),
  p("La estrategia se organiza en cuatro fases:"),
  num("Fase 0 (semana 1): preparar la infraestructura de monetización antes de publicar."),
  num("Fase 1 (mes 1-3): construir audiencia con llamadas a la acción ya activas."),
  num("Fase 2 (mes 3-6): activar la monetización nativa de las plataformas y lanzar el producto core."),
  num("Fase 3 (mes 6-12): consolidar el negocio con membresía, sponsorships y libro."),
  p(
    "El total estimado de costos operativos (APIs + tooling) durante toda la trayectoria se mantiene entre 6 y 25 USD/mes."
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

const phase0 = [
  h1("Fase 0 — Semana 1: infraestructura previa"),
  p(
    "Sin esta capa, cada vista generada se desperdicia: el espectador no tiene a dónde ir, y la marca no tiene cómo capturar valor."
  ),
  h3("Acciones críticas"),
  num("Link in bio con tienda integrada: Stan Store (~15 USD/mes) o Beacons (gratis). Linktree puro queda corto."),
  num("Crear dos productos digitales mínimos viables (un fin de semana de trabajo):"),
  bullet("Pack 30 wallpapers reflexivos en alta resolución — 7 USD. El sistema ya genera las imágenes; basta seleccionar y exportar.", 1),
  bullet("Journal digital de 30 días en PDF interactivo — 12 USD. Una pregunta por día extraída del RAG de filosofía.", 1),
  num("Newsletter desde el inicio: ConvertKit gratis hasta 1 000 suscriptores. El email es la única capa inmune al algoritmo."),
  num("Pixel de tracking en el link en bio para medir qué publicación convierte."),
  h3("Costo y tiempo"),
  p("Setup: 0–15 USD/mes. Tiempo: un fin de semana de trabajo intenso."),
  new Paragraph({ children: [new PageBreak()] }),
];

const phase1 = [
  h1("Fase 1 — Mes 1-3: audiencia con CTA ya activos"),
  p(
    "Publicación constante, multi-canal y con CTA suaves alineados a la voz de marca. El objetivo no es viralizar; es construir base con conversión desde el primer post."
  ),
  h3("Distribución por canal"),
  buildTable(
    [1600, 5200, 2560],
    ["Canal", "Estrategia", "Primer ingreso esperado"],
    [
      ["TikTok", "El mayor potencial de descubrimiento. Publicar 1–2 veces al día. Meta: 10 000 seguidores.", "2–4 meses"],
      ["Instagram Reels", "Cross-post del mismo video sin watermark de TikTok. Mejor canal para vender productos digitales.", "1–2 meses"],
      ["YouTube Shorts", "Mismo video + hashtag #Shorts. El menos competido del nicho en español.", "3–6 meses"],
      ["Pinterest", "Subir las imágenes con frase. Tráfico evergreen hacia la tienda; subestimado y muy rentable.", "2–3 meses"],
      ["Spotify", "Convertir los audios de los Reels en un podcast diario de 2 minutos. Suma monetización y descubrimiento.", "4–6 meses"],
    ]
  ),
  h3("Monetización activa desde el día uno"),
  bullet("Afiliados de Amazon en los captions: libros de Marco Aurelio, Pessoa, Zambrano, Han, Watts. Comisión 1–4%."),
  bullet("Venta de los productos digitales del Fase 0 desde el primer post. Tasa de conversión realista: 0.5–2%."),
  bullet("Recolectar email en cada CTA cuando aplique (lead magnet con 7 reflexiones gratis)."),
  new Paragraph({ children: [new PageBreak()] }),
];

const phase2 = [
  h1("Fase 2 — Mes 3-6: monetización nativa y producto core"),
  p(
    "Al cruzar los umbrales mínimos de cada plataforma se activan programas de pago. Ninguno es la fuente principal, pero suman base recurrente."
  ),
  h3("Programas nativos por plataforma"),
  buildTable(
    [2000, 2600, 4760],
    ["Programa", "Umbral", "Pago realista para este nicho"],
    [
      ["TikTok Creator Rewards", "10 000 seguidores + 100K views/30 días + video ≥1 min", "0.40 – 1 USD por cada 1 000 views. Mejora con videos reflexivos largos (≥1 min)."],
      ["YouTube Partner (Shorts)", "1 000 subs + 10M views Shorts en 90 días", "Bajo por view, pero combinable con AdSense si se publica video largo."],
      ["Facebook Reels Bonus", "Por país, activo en MX y BR", "Sorprendentemente bueno para contenido adulto reflexivo."],
      ["Instagram Bonificaciones", "Irregular en 2026", "No se debe contar con ello."],
    ]
  ),
  h3("Producto core — primer lanzamiento"),
  p(
    "Un mini-curso de 47–97 USD lanzado en Hotmart o Teachable. Margen aproximado 90%. Vender 10 unidades al mes equivale a 470–970 USD pasivos. Ejemplo de título: «Filosofía práctica para días caóticos — 7 lecciones aplicadas»."
  ),
  h3("Métricas a vigilar mensualmente"),
  bullet("Conversión por publicación (clicks al link in bio / impresiones)."),
  bullet("CTR del link in bio hacia cada producto."),
  bullet("Crecimiento neto de seguidores y suscriptores de email."),
  bullet("Revenue por 1 000 seguidores (RPM informal)."),
  new Paragraph({ children: [new PageBreak()] }),
];

const phase3 = [
  h1("Fase 3 — Mes 6-12: negocio consolidado"),
  p("Cuando la audiencia y la confianza están instaladas, se monetiza por capas, no por venta única."),
  h3("Líneas de ingreso"),
  bulletRich([
    bold("Membresía mensual 7–12 USD: "),
    reg("comunidad cerrada, audios largos, reflexión semanal en directo. Si convierte el 1% de 10 000 seguidores: 700–1 200 USD recurrentes/mes."),
  ]),
  bulletRich([
    bold("Sponsorships seleccionados: "),
    reg("apps de meditación (Petit BamBou, Insight Timer), editoriales independientes, café de especialidad. Tarifa típica: 30–100 USD por cada 1 000 seguidores por publicación patrocinada."),
  ]),
  bulletRich([
    bold("Compilación en libro físico: "),
    reg("Amazon KDP a partir de los mensajes y reflexiones acumuladas durante 6–12 meses. El RAG ya constituye la mitad del manuscrito."),
  ]),
  bulletRich([
    bold("Curso ampliado (149–297 USD): "),
    reg("evolución del producto core con sesiones grupales o cohort opcional."),
  ]),
  new Paragraph({ children: [new PageBreak()] }),
];

const dontDo = [
  h1("Anti-patrones — qué no hacer en este nicho"),
  p("Cada uno de estos rompe la marca o malgasta tiempo y dinero:"),
  bullet("AdSense puro en YouTube como única monetización — se paga más en producción de lo que se gana."),
  bullet("Coaching 1-on-1 sin credenciales — riesgo legal, riesgo de marca."),
  bullet("Cripto, trading, dropshipping o NFTs — incoherente con la voz serena. Quema audiencia."),
  bullet("CTAs agresivos del tipo «¡COMPRA YA!» — destruyen el posicionamiento que sostiene los precios premium."),
  bullet("Etiquetar perfiles para forzar engagement — penalizado por algoritmo y por percepción."),
  bullet("Comprar seguidores — sesga el engagement rate hacia abajo y bloquea programas de creator funds."),
  new Paragraph({ children: [new PageBreak()] }),
];

const ranges = [
  h1("Expectativas realistas de ingreso"),
  p(
    "Estos rangos son orientativos en mercado hispano (España + LatAm). Asumen consistencia de publicación, calidad sostenida y al menos un producto digital propio en venta."
  ),
  buildTable(
    [3000, 6360],
    ["Tamaño de audiencia", "Ingreso/mes realista en USD"],
    [
      ["0 – 1 000", "0 – 50 (productos digitales puntuales + algún clic de afiliado)"],
      ["1 000 – 10 000", "100 – 500"],
      ["10 000 – 50 000", "500 – 2 500"],
      ["50 000 – 200 000", "2 500 – 10 000"],
      ["200 000+", "10 000 – 50 000+ (cursos, membresía, sponsorships)"],
    ]
  ),
  p(
    "Plazo realista para alcanzar 10 000 seguidores publicando bien 1–2 veces/día con el sistema automatizado: 4–9 meses. No es garantizado: depende del algoritmo, la calidad sostenida y un componente irreducible de suerte."
  ),
  new Paragraph({ children: [new PageBreak()] }),
];

const tech = [
  h1("Brechas técnicas a cubrir"),
  p("El sistema actual genera y publica, pero hoy no monetiza nada. Las cuatro brechas críticas:"),
  h3("1. CTA hacia productos en los captions"),
  p(
    "El ContentCreatorAgent no conoce la existencia de la tienda ni del producto activo. Hay que pasarle un catálogo y permitir que cierre el caption con una invitación coherente al tono de marca."
  ),
  h3("2. Captura de email"),
  p(
    "Ningún flujo dirige tráfico a un opt-in con lead magnet. Es la pieza más resistente al algoritmo y la que más capitaliza una audiencia que tarde o temprano cambia de plataforma."
  ),
  h3("3. Tracking con UTM por publicación"),
  p(
    "Sin parámetros UTM por plataforma y por contenido es imposible saber qué publicación vende. El PublisherAgent puede inyectar la URL final con UTM en el caption antes de publicar."
  ),
  h3("4. A/B test de hooks"),
  p(
    "Para iterar rápido cuál hook retiene más vista, el sistema debería generar 2–3 variantes y permitir registrar resultado. Es la mejora de mayor palanca después de las anteriores."
  ),
  h3("Roadmap técnico sugerido"),
  num("Catálogo de productos en config/products.yaml y producto activo seleccionable."),
  num("Helper de UTM por plataforma."),
  num("Inyección de CTA + URL en el PublisherAgent."),
  num("Endpoint del panel web para administrar productos y producto activo."),
  num("Variantes de hook (A/B) en el ContentCreatorAgent."),
  new Paragraph({ children: [new PageBreak()] }),
];

const cost = [
  h1("Estructura de costos sugerida"),
  buildTable(
    [3200, 3160, 3000],
    ["Capa", "Servicio recomendado", "Costo mensual aproximado"],
    [
      ["Texto (LLM)", "GPT-4o-mini o Claude Haiku 4.5", "1 – 3 USD"],
      ["Embeddings (RAG)", "OpenAI text-embedding-3-small", "menos de 0.05 USD"],
      ["Voz (TTS)", "ElevenLabs Starter (multilingual v2) o OpenAI tts-1 (nova)", "0 – 5 USD"],
      ["Imágenes de fondo", "Pexels", "0 USD"],
      ["B-roll de video", "Pexels", "0 USD"],
      ["Música ambient", "Pixabay Music", "0 USD"],
      ["Link in bio + tienda", "Stan Store", "0 – 15 USD"],
      ["Email marketing", "ConvertKit free", "0 USD hasta 1 000 suscriptores"],
      ["Hosting de media", "S3 o Cloudinary (free tier)", "0 – 1 USD"],
    ]
  ),
  p(
    "Estimación total: entre 6 y 25 USD/mes durante todo el primer año, con calidad de producción suficiente para sostener una marca premium en el nicho."
  ),
];

const closing = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Indicadores de éxito por fase"),
  buildTable(
    [1400, 3000, 4960],
    ["Fase", "Métrica clave", "Umbral mínimo de éxito"],
    [
      ["Fase 0", "Infraestructura lista", "Tienda + 2 productos + newsletter + tracking funcionando antes del día 8"],
      ["Fase 1", "Crecimiento + primera venta", "+500 seguidores netos/mes y ≥ 1 venta digital/mes"],
      ["Fase 2", "Producto core probado", "≥ 10 ventas/mes del producto core y al menos un programa nativo activo"],
      ["Fase 3", "Negocio recurrente", "Ingreso recurrente (membresía + sponsorships) > 1 500 USD/mes"],
    ]
  ),
  p(
    "Si después de tres meses en una fase no se alcanza el umbral mínimo, conviene revisar antes de pasar a la siguiente; no es una escalera obligatoria sino una secuencia recomendada."
  ),
];

// Build document --------------------------------------------------------------
const doc = new Document({
  creator: "Mental Equilibrio",
  title: "Plan de monetización — Mental Equilibrio",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: "1F2A38" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "2C4A52" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 },
      },
      {
        id: "Heading3",
        name: "Heading 3",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "3E5641" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "•",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
          {
            level: 1,
            format: LevelFormat.BULLET,
            text: "◦",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } },
          },
        ],
      },
      {
        reference: "numbers",
        levels: [
          {
            level: 0,
            format: LevelFormat.DECIMAL,
            text: "%1.",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
        },
      },
      children: [
        ...cover,
        ...summary,
        ...phase0,
        ...phase1,
        ...phase2,
        ...phase3,
        ...dontDo,
        ...ranges,
        ...tech,
        ...cost,
        ...closing,
      ],
    },
  ],
});

const outDir = path.resolve(__dirname, "..");
const outPath = path.join(outDir, "Plan_Monetizacion.docx");
Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log("OK ->", outPath);
});
