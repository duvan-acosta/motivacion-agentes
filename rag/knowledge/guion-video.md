# Guion — arquitectura narrativa para video corto

Este documento alimenta al `VideoProducerAgent`. Define cómo se construye un
guion de 20-40 segundos para Reels, Shorts y TikTok que retenga la atención
hasta el final sin sacrificar la voz de la marca.

## Reglas fundamentales

1. **El primer plano gana o pierde el video.** Si en los primeros 3 segundos
   no hay una promesa, una imagen o una pregunta, el usuario hace swipe.
2. **Una sola idea por video.** Si tienes dos ideas, son dos videos.
3. **Cierre con eco, no con cliffhanger.** El nicho reflexivo se rompe con
   manipulación. El cierre devuelve al espectador a sí mismo.
4. **Cada frase es un plano.** Estructura el guion como una lista de frases
   cortas; cada una corresponde a un overlay de texto y a un beat de imagen.
5. **Cadencia de voz: 2.0-2.5 palabras por segundo.** Más rápido suena nervioso,
   más lento se cae el ritmo. 80-100 palabras para 35-40 segundos.

## Arquitectura estándar — 5 actos

Estructura recomendada para un video de 30-35 segundos. Cada acto incluye un
rango aproximado de duración y propósito.

### Acto 1 — Hook (0:00-0:03) | 1 frase
- Frase de apertura **silenciosa**: pregunta o afirmación contraintuitiva.
- Sin gritar. La marca no usa "PARA EN SECO" ni interpelaciones agresivas.
- Imagen: plano amplio de naturaleza lenta + título overlay grande.

Ejemplos:
- "Hay algo que rara vez nos decimos."
- "¿Y si lo que llamas pereza fuera información?"
- "No todo lo que se acaba, fracasa."

### Acto 2 — Apertura (0:03-0:08) | 1-2 frases
- Da contexto mínimo: ¿de qué estamos hablando?
- Aterriza la promesa del hook en una escena o ejemplo concreto.
- Imagen: corte a B-roll relacionado con el ejemplo.

### Acto 3 — Desarrollo (0:08-0:22) | 3-5 frases
- La idea central. Aquí va el cuerpo de la reflexión.
- Distinguir, comparar, ofrecer una mirada nueva.
- Imagen: 2-3 cortes B-roll que acompañen la reflexión sin distraer.

### Acto 4 — Giro / Implicación (0:22-0:30) | 1-2 frases
- El "y entonces…": qué cambia si tomas en serio lo dicho.
- Aquí puede aparecer una imagen contraintuitiva al hook.

### Acto 5 — Cierre (0:30-0:35) | 1 frase
- Frase corta que devuelve al espectador a su propia vida.
- No es CTA explícito (eso va en el caption). Es eco emocional.
- Imagen: plano final amplio + título de cierre o el handle de la marca.

## Estructura corta — 25-28 segundos

Para temas que no necesitan tanto desarrollo, comprimir a 3 actos:

1. **Hook** (3s): 1 frase.
2. **Cuerpo** (15-18s): 3-4 frases con una distinción clara.
3. **Cierre** (5-7s): 1 frase + plano amplio.

## Plantillas de guion

Las siguientes son **estructuras** parametrizables, no textos para copiar.

### Plantilla "Replanteo"
```
[HOOK]   Lo que llamamos {X} a veces no es {X}.
[OPEN]   Lo vemos {ejemplo cotidiano}.
[DEV]    Y eso pasa porque {distinción 1}.
         Pero {distinción 2}.
         No es {lo que parece}, es {lo que realmente es}.
[GIRO]   Cuando lo ves así, {consecuencia práctica}.
[CIERRE] Quizás hoy basta con {acción mínima}.
```

### Plantilla "Pregunta interior"
```
[HOOK]   ¿Cuándo fue la última vez que {acción olvidada}?
[OPEN]   No hablo de {versión grandilocuente}.
         Hablo de {versión cotidiana}.
[DEV]    Hay días en que {observación}.
         Y el problema no es {falsa causa},
         es {causa real}.
[GIRO]   Si lo miras así, {implicación}.
[CIERRE] Empieza por {acción mínima}.
```

### Plantilla "Imagen ampliada"
```
[HOOK]   {Metáfora natural concreta — agua, raíz, viento}.
[OPEN]   {Desarrollo de la metáfora}.
[DEV]    Igual {analogía con la vida},
         no por {atributo equivocado},
         sino por {atributo real}.
[GIRO]   Tal vez la cuestión no es {falsa pregunta},
         sino {pregunta real}.
[CIERRE] Y eso, hoy, alcanza.
```

## Calibración del texto a leer

- **Palabras por segundo**: 2.0 a 2.5. Cuenta el total y divide.
- **Frase máxima por overlay**: 9-12 palabras (cabe en 2 líneas a 48 px).
- **Pausas naturales**: marca con punto, no con coma, cualquier corte donde
  quieres que el TTS respire.
- **Sin números compuestos hablados** ("treinta y siete") en el guion: el TTS
  los entrega mal en español; reescribe.

## Reglas de overlay (texto sobre el video)

1. Cada frase del guion → un overlay separado.
2. Sincronización: el overlay aparece **0.2s antes** de que la voz lo lea, y
   sale **0.5s después** de que termine.
3. Posición: zona central-baja (`y=900` a `y=1500` en lienzo 1080×1920).
4. Estilo: Inter Bold 44-50 px, blanco, con sombra negra suave o caja
   semitransparente (`rgba(0,0,0,0.35)`).
5. Animación: fade-in 200ms, fade-out 200ms. Nada de "type-on" carácter a
   carácter ni efectos TikTok.

## Voz y TTS

- **Voz**: femenina o neutra adulta, registro grave, ritmo pausado. Voces que
  encajan: OpenAI `nova` (default), ElevenLabs voces serie "calm" o
  "narrator". Evitar voces juveniles o con vibrato.
- **Pausas**: dejar 300-500 ms entre actos. El silencio es parte del ritmo.
- **Música de fondo** (opcional): instrumental ambient, BPM ≤80, sin batería
  electrónica. Volumen 5-10% del nivel de voz.

## B-roll — selección y ritmo

- **Duración mínima por plano**: 3 segundos. Cortes más rápidos rompen tono.
- **Movimiento**: cámara lenta (dolly, pan suave). Sin handheld nervioso.
- **Contenido**: naturaleza lenta (agua, hojas, nubes, lluvia, montaña), manos
  haciendo algo cotidiano (escribir, servir té, abrir libro), siluetas
  caminando lejos. Sin rostros frontales en primer plano.
- **Continuidad**: si el guion habla de agua, no cambies a montaña; si habla
  de pausa, no metas movimiento rápido. El video es una sola atmósfera.

## Anti-patrones — lo que rompe la marca

- Sonidos trending de TikTok que no encajan con el tono.
- Texto que aparece carácter a carácter o con bounce.
- Subtítulos auto-generados sin editar (errores, frases cortadas en mal sitio).
- Transiciones con flash o swipe forzado.
- Pop-ups de "sígueme", flechas dibujadas, círculos rojos: ese lenguaje
  pertenece al growth-hack agresivo y arruina la credibilidad.
- Cierres con cliffhanger forzado ("parte 2 en mi perfil").
- Videos cortados a 8 segundos por la moda; nuestra marca respeta la pausa.

## Ejemplo completo — 32 segundos

Tema: presencia.

```
[HOOK 0:00-0:03]
"Hay algo que rara vez nos decimos."

[OPEN 0:03-0:08]
"Que estar presente no es relajante.
Casi siempre es incómodo."

[DEV 0:08-0:22]
"Porque cuando dejas de huir al teléfono,
aparece lo que pospones.
Una conversación pendiente.
Un sentimiento que no nombraste.
Una decisión que no quisiste mirar."

[GIRO 0:22-0:28]
"La presencia no calma. Aclara.
Y a veces lo que aclara, primero molesta."

[CIERRE 0:28-0:32]
"Pero después, asienta."
```

Conteo: 70 palabras, 32 segundos a 2.2 p/s. Encaja.
