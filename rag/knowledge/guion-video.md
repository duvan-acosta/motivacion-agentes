# Guion — arquitectura para Reel/Short/TikTok motivacional

Este documento alimenta al `VideoProducerAgent`. Define cómo construir
un guion de 20-40 segundos en el tono **directo emocional** de la marca:
una voz que valida, abraza y deja al espectador con más esperanza que
cuando empezó el video.

## Reglas fundamentales

1. **El primer plano vende o pierde el video.** En los primeros 3 segundos
   tiene que haber una frase DIRECTA que conecte emocionalmente. Nada de
   ironías ni rodeos.
2. **Una sola idea por video.** Si tienes dos, son dos videos.
3. **Validar antes de animar.** Si el video va a alentar, primero reconoce
   lo difícil. "Hoy te pesa. Lo entiendo. Y aún así…"
4. **Cierre con esperanza activa, no cliffhanger.** La marca NO usa
   manipulación tipo "parte 2 en mi perfil".
5. **Cada frase es un overlay.** Estructura el guion como lista de frases
   cortas, una por línea, cada una se mostrará sincronizada con la voz.
6. **Cadencia 2.0-2.5 palabras/segundo.** Para 30-35 segundos = ~70-85
   palabras totales. Si excede, recortar al guionizar.

## Arquitectura motivacional — 5 actos

### Acto 1 — Hook directo (0:00-0:04) | 1 frase
Una afirmación, validación o pregunta que detenga el scroll.
**Es DIRECTO. No silencioso ni críptico.**

Ejemplos:
- "Hoy te tengo que decir algo importante."
- "¿Sabes qué te haría bien hoy?"
- "Si llegaste aquí, esto es para ti."
- "Está bien si hoy no puedes con todo."
- "Hoy quiero recordarte algo."

### Acto 2 — Validación (0:04-0:10) | 1-2 frases
Reconoce lo que el espectador siente o vive. Antes de animar, le dejas
saber que no está solo.

Ejemplos:
- "Estás cansada. Y nadie te lo está validando."
- "Has dado mucho. Más de lo que la gente ve."
- "El año ha sido pesado, lo sé."

### Acto 3 — El giro esperanzador (0:10-0:24) | 3-5 frases
La verdad cálida que viraliza el video. Aquí es donde le devuelves la
fuerza al espectador. Estructura típica:

> Y aún así…
> Sigues aquí.
> Eso ya dice mucho.
> Tú no eres tu cansancio.
> Eres lo que decides cuando estás cansada.

### Acto 4 — Acción pequeña (0:24-0:32) | 1-2 frases
Le das algo CONCRETO para hacer hoy. Algo que tome 5-30 segundos.

Ejemplos:
- "Hoy solo te pido una cosa: respira hondo tres veces antes de seguir."
- "Esta noche, antes de dormir, escribe una cosa que sí lograste hoy."
- "Mañana, al despertarte, di en voz alta: 'puedo con este día'."

### Acto 5 — Cierre cálido (0:32-0:38) | 1 frase
Un cierre amoroso. Sin CTA explícito del producto (eso va en el caption).
El espectador termina sintiéndose visto.

Ejemplos:
- "Vas a estar bien. Te lo digo de verdad."
- "Tú puedes con esto. Yo confío en ti."
- "Aquí estaré mañana para recordártelo."

## Estructura corta — 25-28 segundos

Para temas que no requieren mucho desarrollo, comprimir a 3 actos:

1. **Hook + validación** (5s): 1-2 frases.
2. **Giro esperanzador + acción** (15-18s): 3-4 frases.
3. **Cierre cálido** (5s): 1 frase.

## Plantillas de guion

### Plantilla A — "Si llegaste aquí"
```
[HOOK 0:00-0:04]
"Si llegaste aquí, esto es para ti."

[VALIDACIÓN 0:04-0:10]
"Sé que el día no fue como esperabas.
Sé que estás cansado."

[GIRO 0:10-0:24]
"Pero mira algo importante.
Estás aquí, viendo este video.
Eso es porque algo en ti todavía busca aliento.
Eso ya es ganancia.
Eso ya es valentía."

[ACCIÓN 0:24-0:32]
"Hoy te pido solo una cosa.
Cierra los ojos y respira hondo tres veces."

[CIERRE 0:32-0:36]
"Vas a estar bien. De verdad."
```

### Plantilla B — "Hoy te quiero recordar"
```
[HOOK 0:00-0:04]
"Hoy te quiero recordar algo importante."

[VALIDACIÓN 0:04-0:08]
"Sé que sientes que ya no puedes más."

[GIRO 0:08-0:24]
"Pero recuerda esto:
Ya pasaste por días peores y aquí estás.
Eres más fuerte de lo que crees.
Solo que se te olvida cuando todo pesa."

[ACCIÓN 0:24-0:32]
"Date permiso para descansar hoy.
No tienes que merecerlo. Lo necesitas."

[CIERRE 0:32-0:36]
"Tú puedes con esto. Confío en ti."
```

### Plantilla C — "Está bien sentirte así"
```
[HOOK 0:00-0:04]
"Está bien sentirte así."

[VALIDACIÓN 0:04-0:10]
"No tienes que estar siempre fuerte.
No tienes que sonreír cuando no quieres."

[GIRO 0:10-0:24]
"Lo que sientes es real.
Y también es pasajero.
Hoy te pesa, mañana respiras distinto.
Pero solo si te das permiso de sentirlo hoy."

[ACCIÓN 0:24-0:32]
"Escribe en una nota lo que estás sintiendo.
Sin filtro. Solo para ti."

[CIERRE 0:32-0:36]
"Yo te leo. Aquí estoy."
```

## Calibración del texto

- **Palabras por segundo:** 2.0 a 2.5. Para 35 segundos = 70-85 palabras.
- **Frase máxima por overlay:** 9-12 palabras (cabe en 2 líneas).
- **Pausas naturales:** marcadas con punto, no coma. El TTS respira ahí.
- **Sin números compuestos hablados.** Mejor escribir "tres" que "37".
- **Sin ironías ni dobles sentidos** que el oyente podría malinterpretar.

## Reglas de overlay

1. Cada frase del guion → un overlay independiente.
2. Sincronización: aparece 0.2s antes de que la voz lo lea, sale 0.5s
   después de que termine.
3. Posición: zona central-baja (y=900 a y=1500 en 1080×1920).
4. Estilo: Vollkorn Bold 44-50 px, crema `#FAF3E7`, caja semi-transparente
   adaptativa con stroke negro 2px.
5. Animación: fade-in 200ms, fade-out 200ms. NUNCA type-on carácter a
   carácter ni efectos TikTok nativos.

## Voz y TTS

- **Voz:** femenina cálida adulta, registro medio-grave, ritmo pausado pero
  no lento. Voces que encajan:
  - OpenAI `nova` o `shimmer` (por default).
  - ElevenLabs voces multilingüe v2 (Valentina, Sarah, Bella).
- **Pausas:** 300-500 ms entre actos. Los silencios cargan emoción.
- **Música de fondo** (opcional): instrumental cálido (piano suave,
  guitarra acústica), BPM ≤80, volumen 5-8% del nivel de voz.

## B-roll — selección y ritmo

- **Duración mínima por plano:** 3 segundos.
- **Movimiento:** cámara lenta (dolly suave, paneo). Sin handheld.
- **Contenido recomendado:** escenas cotidianas latinas y universales:
  - Café de la mañana.
  - Persona caminando por una calle tranquila.
  - Manos escribiendo en un cuaderno.
  - Ventana con luz de tarde.
  - Persona mirando al horizonte.
  - Sonrisa suave de persona mayor.
  - Niño jugando, perro acompañando.
- **Continuidad:** mantener la misma atmósfera cromática. Si el video
  habla de calma, no metas escenas de movimiento rápido.

## Anti-patrones — lo que rompe la marca

- Sonidos trending de TikTok que no encajan con el tono.
- Texto que aparece carácter a carácter o con bounce.
- Subtítulos auto-generados sin editar.
- Transiciones flash, zoom in agresivo o swipe forzado.
- Pop-ups de "sígueme", flechas dibujadas, círculos rojos.
- Cliffhangers manipuladores ("parte 2 en mi perfil").
- Voice clone de famosos.
- Música épica tipo trailer de Hollywood.

## Ejemplo completo — 35 segundos

Tema: amor propio.

```
[HOOK 0:00-0:04]
"Si te cuesta cuidarte, esto es para ti."

[VALIDACIÓN 0:04-0:10]
"Sé que llevas mucho.
Que pones a otros antes que a ti."

[GIRO 0:10-0:25]
"Pero escúchame.
Tu paz también cuenta.
Tu descanso también es trabajo.
Tu salud también es prioridad.
Decir 'no' no te hace egoísta.
Te hace humano."

[ACCIÓN 0:25-0:32]
"Hoy escoge una cosa para ti.
Aunque sea quince minutos sin hacer nada."

[CIERRE 0:32-0:36]
"Te lo mereces. Te lo digo de verdad."
```

Conteo: ~75 palabras, 36 segundos a 2.1 p/s. Encaja perfecto.
