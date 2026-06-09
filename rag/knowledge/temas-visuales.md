# Dirección visual — Mental Equilibrio

Documento de referencia para `VisualDesignerAgent`. Define paleta, tipografía,
composición y selección de fondos para que el contenido se vea como una marca
**cálida, motivacional y editorial moderna**: lejos del Canva genérico y lejos
del Tumblr filosófico-frío.

## Identidad visual

- **Estilo:** editorial cálido. Foto fotográfica auténtica de Pexels +
  tipografía serif moderna + caja sutil para contraste + color de texto crema.
- **Atributos:** acogedor, claro, esperanzador, humano, contemporáneo.
- **Lo que NO somos:**
  - Saturado de stickers, emojis grandes o gradientes neón.
  - Filosófico frío estilo "tumblr aesthetic".
  - Genérico de plantilla Canva con bordes de hojas y mariposas.
  - Stock corporativo (sonrisas plásticas, "team building" americano).

## Tipografía

- **Mensaje principal:** **Vollkorn** (serif moderna alemana, humanista,
  cálida). Instalada vía `fonts-vollkorn` en el contenedor.
- **Fallback display:** DejaVu Serif.
- **Pie de marca y soporte:** **Cabin** (humanist sans, clara y amigable).
- **Fallback sans:** DejaVu Sans.

### Jerarquía tipográfica para 1080×1080 (feed/post)

| Elemento | Tamaño aprox. | Notas |
|----------|---------------|-------|
| Mensaje principal (Vollkorn Bold) | 48-72 px | adaptativo según largo |
| Pie de marca (Cabin SemiBold) | 22-28 px | esquina inferior |

### Jerarquía tipográfica para 2160×3840 (wallpaper)

| Elemento | Tamaño aprox. | Notas |
|----------|---------------|-------|
| Mensaje principal (Vollkorn Bold) | 94-182 px | adaptativo |
| Pie de marca (Cabin SemiBold) | 58 px | safe zone inferior |

### Reglas tipográficas

- Máximo **6 líneas** por lienzo. Si no entra, reescribir más corto.
- Color del texto: **crema cálido `#FAF3E7`** sobre caja semi-transparente,
  no blanco puro.
- Stroke negro 2px en 4 direcciones (legibilidad sobre cualquier fondo).
- Interlineado 1.20-1.25.
- Alineación centrada para feed cuadrado e imagen vertical; izquierda para
  twitter 16:9 cuando aplique.

## Paletas por tema (HEX)

Cada tema tiene una paleta cálida o serena coherente. Se aplica al gradiente
de fondo procedural cuando Pexels no devuelve foto.

### Temas reflexivos (mantenidos del catálogo anterior)

| Tema | Dominante | Acento | Sombra | Atmósfera |
|------|-----------|--------|--------|-----------|
| Resiliencia | `#1F2A38` azul tormenta | `#C29A55` ocre | `#0B1117` | Cielo después de la tormenta |
| Calma | `#2C4A52` verde azulado | `#A8C5C0` salvia | `#10202A` | Niebla sobre agua |
| Claridad | `#E6C893` dorado suave | `#FFFFFF` blanco | `#3B2F1F` | Amanecer |
| Propósito | `#3E5641` verde bosque | `#D7B27B` arena | `#1A2519` | Camino entre árboles |
| Gratitud | `#C57B57` terracota | `#F5E6CA` crema | `#5C3A28` | Luz cálida de tarde |
| Presencia | `#2A2D34` carbón | `#9BA9B4` plata | `#13151B` | Lluvia tranquila |
| Coraje | `#3C1F2B` vino profundo | `#D88C5A` cobre | `#1A0C13` | Vendaval contenido |
| Sabiduría | `#1A2238` azul noche | `#9DAAF2` violeta tenue | `#0A0E1A` | Cielo estrellado |

### Temas motivacionales nuevos (paletas cálidas y empáticas)

| Tema | Dominante | Acento | Sombra | Atmósfera |
|------|-----------|--------|--------|-----------|
| Esperanza | `#E89B5A` naranja amanecer | `#FFE4C7` crema | `#5C3520` | Amanecer cálido |
| Amor propio | `#D17A8F` rosa terra | `#F8E0DD` rosa pálido | `#5A2A36` | Luz de vela, ternura |
| Empezar de nuevo | `#E6B466` dorado suave | `#FFF4DA` marfil | `#4A331A` | Nuevo amanecer |
| Ansiedad cotidiana | `#5E7A8C` azul ahumado | `#C9D6DE` cielo pálido | `#1F2E38` | Cielo nocturno calmo |
| Autoestima | `#B26B4F` cobre | `#F0D2BB` durazno | `#3D1F12` | Luz de tarde cálida |
| Soledad saludable | `#4A6373` azul slate | `#B7C8D2` plata azul | `#1A2730` | Habitación tranquila |
| Límites | `#7D4A4A` rojo tierra | `#E0B8B8` rosa polvo | `#2E1818` | Puerta cerrada al sol |

**Regla:** una sola publicación = una sola paleta. Nada de combinar.

## Composición — reglas activas

1. **Foto fotográfica de Pexels** como base siempre que sea posible.
2. **Texto centrado** sobre caja semi-transparente oscura adaptativa.
3. **Caja sin bordes redondeados** (look editorial moderno, no chat-bubble).
4. **Opacidad adaptativa de la caja:** se mide la luminance del fondo en la
   zona del texto y se ajusta automáticamente:
   - Fondo claro (lum > 150) → caja α=140 (visible)
   - Fondo medio (80-150) → caja α=100 (sutil)
   - Fondo oscuro (< 80) → caja α=60 (apenas perceptible)
5. **Texto en crema cálido `#FAF3E7`** con stroke negro fino.
6. **Pie de marca** "Mental Equilibrio" siempre presente, esquina inferior,
   también con color adaptativo (claro u oscuro según el fondo).
7. **Espacio negativo respirado:** texto + pie ocupan máximo 60% del área.

## Anti-patrones (no hacer)

- Texto sobre rostro frontal en primer plano.
- Stock con sonrisas exageradas o team-building corporativo.
- Marcos, sombras paralelas grandes, banners decorativos.
- Tipografías "manuscritas" tipo Lobster, Pacifico, Brush Script. NUNCA.
- Filtros saturados estilo "feed naranjado Instagram 2014".
- Foto + emoji grande encima.

## Selección de fondos (Pexels)

### Criterios para aceptar un fondo

- **Una sola idea visual** (taza, ventana, persona en una sola acción).
- **Resolución mínima 1920×1080**.
- **Iluminación natural cálida o suave**, no de estudio.
- **Sin rostros frontales en primer plano** que compitan con el texto.
- **Profundidad fotográfica** (primer plano + fondo).
- **Color compatible con la paleta del tema**.
- **Sin texto incrustado** (logos de marcas, letreros).

### Keywords Pexels por tema

| Tema | Keywords primarias | Alternativas |
|------|--------------------|--------------|
| Resiliencia | mountain peak fog, storm clearing | rocky coast, lone tree wind |
| Calma | calm lake mist, foggy forest dawn | still water reflection, slow river |
| Claridad | sunrise horizon, golden hour field | open sky, fresh snow |
| Propósito | forest path morning, distant lighthouse | country road, mountain trail |
| Gratitud | warm sunset, wildflowers backlit | tea morning, hands warm light |
| Presencia | raindrops window, single tree field | zen garden, hands cup tea |
| Coraje | ocean storm waves, eagle flight | climber silhouette, fire embers |
| Sabiduría | starry sky milky way, ancient tree | old books, observatory night |
| **Esperanza** | sunrise dawn light, warm morning sky | fresh start road, hopeful horizon |
| **Amor propio** | self care moment, warm bath light | candle morning, mirror gentle |
| **Empezar de nuevo** | sunrise road, open field morning | fresh path, new beginning sky |
| **Ansiedad cotidiana** | evening sky calm, hand on heart | soft breath person, calming light |
| **Autoestima** | confident portrait sunset, woman looking up | self portrait warm light |
| **Soledad saludable** | person reading window, solo coffee morning | quiet apartment soft light, kitchen alone calm |
| **Límites** | closed window light, open hand stop | boundary fence sunset, door soft light |

### Fallback procedural (sin Pexels)

Cuando Pexels no devuelve resultado, generar gradiente con Pillow usando dos
colores de la paleta del tema (sombra → dominante) en diagonal a 135°. Añadir
grano sutil (ruido 2-3%) para textura editorial.

## Composición para video vertical (Reel/Short/TikTok)

- **Aspect ratio:** 9:16, 1080×1920.
- **Subtítulos sincronizados** en zona central-baja (y≈1100), caja semi-
  transparente adaptativa.
- **Frame inicial del video** = primer cue del subtítulo + plano amplio.
- **B-roll:** naturaleza lenta + manos haciendo algo cotidiano + cocina/casa
  acogedora. Cada plano dura ≥3 segundos.
- **Subtítulos:** Vollkorn Bold sobre caja `rgba(0,0,0,0.40)` con stroke
  negro. Texto crema `#FAF3E7`. 6-12 palabras por cue máx.
- **Pie de marca** discreto en la esquina inferior derecha durante todo el video.

## Validación visual antes de aprobar

1. ¿Se lee el mensaje en 2 segundos sobre una pantalla pequeña?
2. ¿La caja garantiza contraste sobre el fondo elegido?
3. ¿El mensaje está dentro de safe zone (no tapado por UI nativa)?
4. ¿La paleta del tema y el color general del fondo se conversan?
5. ¿Es reconocible como Mental Equilibrio sin ver el pie de marca?

Si alguno falla, descartar y regenerar.
