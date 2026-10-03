# NoorLine — Small AI para acceso a atención primaria (Sector Salud)

> **Hackathon:** Small AI for Development · Hack-Nation × World Bank Youth Summit
> **Ventana:** 3–4 octubre 2026 · **Sector:** Annex A (Salud) · **Persona:** Noor (38 años, Ondera highlands, celular básico, sin Wi-Fi, 3G intermitente)
> **Estado de este documento:** plan de trabajo + arquitectura de referencia. Todo lo marcado como *[DEMO]* es lo que se construye en el fin de semana; *[ROADMAP]* es lo que se describe pero no se construye.

---

## 0. Resumen ejecutivo

**Problema.** La clínica de Noor está saturada, el personal no alcanza a dar atención individual y la carga de registros consume tiempo clínico. Noor no tiene smartphone propio de uso diario y no sabe "promptear" a una IA.

**Solución.** Un servicio por **llamada de voz o SMS** que funciona con el celular que Noor ya tiene. Un **nodo comunitario** (celulares reciclados) guarda todo localmente (store-and-forward) y sincroniza con un **servidor central** cuando hay red. Una **Small AI** (clasificación de intención + señales de alerta + traducción + generación de mensajes acotados) separa **urgencias** (humano inmediato) de **casos de rutina** (citas, recordatorios, seguimiento). **La IA nunca diagnostica ni decide: informa, prioriza y pregunta "no estoy seguro, que lo vea una persona".**

**Frase del problema (formato exigido por el video):**
> *Gracias a esta herramienta, [Noor y el personal de su clínica] podrán [pedir cita, recibir recordatorios y que los casos urgentes se prioricen] en [minutos en vez de días], algo que de otro modo [harían tarde o no harían]; lo sabemos porque [evidencia: SDI/WHO GHO/DHS, país y año a citar].*

**Alineación con el hackathon (checklist de reglas, sección 06 del concept note):**

| Regla | Cómo se cumple |
|---|---|
| Corre en un dispositivo que el usuario ya tiene | Teléfono básico de Noor (voz/SMS); cero apps que instalar |
| Función central funciona offline | Nodo comunitario atiende y encola sin internet (store-and-forward) |
| Modelos pequeños, side-loadable | Modelos cuantizados (int8/GGUF/ONNX) < ~500 MB en el nodo; clasificador < 50 MB |
| Interacción en lengua local | Elegir y **nombrar** una lengua (ver §2.6) + declarar qué pasa en una lengua menos soportada |
| Human-in-the-loop | Un humano toma toda decisión clínica; lista cerrada de respuestas |
| Evitar alucinaciones | **Fixed list of answers**: la IA no genera texto libre al paciente |
| Fail-safe | "No estoy seguro — que lo vea una persona" como salida por defecto ante baja confianza |

---

## 1. Arquitectura técnica recomendada

### 1.1 Vista general

```
 ┌──────────────┐   Voz (GSM)   ┌─────────────────────────────────────────────┐
 │ Teléfono de  │──────────────▶│  NODO COMUNITARIO (celular reciclado + hub) │
 │ Noor (básico)│◀──────────────│  • Pasarela SMS/Voz  • Cola store-and-fwd   │
 └──────────────┘     SMS       │  • SQLite cifrada (perfiles offline)        │
                                │  • Clasificador small AI (on-device)        │
 ┌──────────────┐               │  • Reglas de señales de alerta (offline)    │
 │ Otros nodos  │◀─ WiFi local─▶│  • Alerta local al personal (SMS/sirena)    │
 │ (celulares)  │   / MQTT      └───────────────┬─────────────────────────────┘
 └──────────────┘                               │  Sync cuando hay red (3G/2G/WiFi)
                                                ▼  (HTTPS/MQTT, cifrado, idempotente)
                              ┌───────────────────────────────────────────────┐
                              │  SERVIDOR CENTRAL (PC / mini-servidor)        │
                              │  • API (FastAPI) • Postgres cifrada           │
                              │  • Small AI: intención, traducción, resumen   │
                              │  • Motor de políticas por clínica             │
                              │  • Panel web de la clínica (bandeja HITL)     │
                              │  • Auditoría + consentimiento                 │
                              │  • Exportación a DHIS2 [ROADMAP]              │
                              └───────────────────────────────────────────────┘
```

### 1.2 Principio de diseño: **el nodo es autónomo, el servidor es opcional para sobrevivir**
Si el servidor central o la red caen, el nodo sigue: recibe, clasifica con modelos locales, aplica reglas de señales de alerta, avisa al personal local y encola lo demás. El servidor aporta capacidad extra (modelos más grandes, analítica, panel multiclínica), no es un punto único de falla para **urgencias**.

### 1.3 Componentes

#### A. Canal de entrada (paciente)
| Canal | Cómo entra | Tecnología recomendada | Notas |
|---|---|---|---|
| **SMS** | Noor manda un SMS a un número de la comunidad | App Android "SMS gateway" en el celular del nodo (o `Termux` + `termux-sms-*`) → webhook local | El más simple y robusto. **Es el canal principal de la DEMO.** |
| **Voz** | Noor llama; menú IVR por DTMF + voz corta | Opción 1 (DEMO): **simulador de llamada** (Asterisk/Twilio-free o grabación) ; Opción 2: **Asterisk/FreeSWITCH + módem GSM USB / gateway GSM**; Opción 3 [ROADMAP]: app de telefonía en Android del nodo | ⚠️ El SIM800L es **2G**: en muchos países la red 2G ya se apagó. Verificar cobertura; preferir módulo 4G (SIM7600) o un Android reciclado como pasarela. |
| **ASR / TTS** | Voz→texto y texto→voz | **ASR:** Whisper-tiny/base cuantizado o MMS-1B (Meta) para lenguas con pocos datos; **TTS:** MMS-TTS / Piper | Corre en el servidor o en el nodo si el hardware aguanta. Fallback: **IVR por DTMF** (marque 1, 2, 3) que no necesita ASR. |

> **Decisión de diseño clave:** el IVR **empieza con DTMF** (marcar dígitos) y solo usa voz libre para una frase corta ("¿qué le pasa?") con ASR + clasificador. DTMF es 100 % determinista y auditable → ideal para **consentimiento** y para el modo de falla.

#### B. Nodo comunitario (hardware ligero / Edge AI)
- **Hardware:** 1 celular Android reciclado "céntrico" por comunidad (mín. 3–4 GB RAM idealmente; si es menor, solo reglas + clasificador pequeño) + 1–2 celulares satélite opcionales. Batería + cargador solar/power bank para cortes de luz.
- **SO / runtime:** Android (versión vieja) con **Termux** (Python + SQLite + MQTT) **o** postmarketOS/Linux ligero en equipos compatibles. Documentar la versión exacta usada (los evaluadores lo valoran).
- **Red local entre nodos:** hotspot Wi-Fi del nodo + **MQTT (Mosquitto en Termux)** entre celulares; no requiere internet.
- **Almacenamiento:** **SQLite con cifrado (SQLCipher)** + cola de salida con estados `pendiente → enviado → confirmado`.
- **Store-and-forward:** cada evento tiene un `event_id` (UUID) para **idempotencia** (si se reenvía, el servidor no duplica). Reintentos con backoff exponencial; prioridad: **urgencias primero**.
- **Edge AI en el nodo (Small AI):**
  - Clasificador de intención (SMS/texto transcrito): modelo tipo DistilBERT/XLM-R-small o **fastText/TF-IDF + regresión logística** (baseline ligerísimo), exportado a **ONNX/TFLite**, cuantizado int8.
  - **Detector de señales de alerta:** reglas deterministas (lista cerrada configurada por la clínica) + el clasificador como segunda opinión. *Las reglas ganan sobre el modelo.*
  - Traducción on-device [ROADMAP]: NLLB-200-distilled-600M cuantizado (pesado) → en la DEMO corre en el servidor con cola.

#### C. Servidor central
- **Stack sugerido:** Python 3.11 + **FastAPI**, **PostgreSQL** (o SQLite en demo), **Redis/colas simples** opcional, **Mosquitto** para eventos. Panel web: **React/HTML + Tailwind** (o Streamlit para prototipar rápido).
- **Modelos (todo pequeño y open source):**
  | Función | Modelo recomendado | Dataset / benchmark |
  |---|---|---|
  | Intención | clasificador fine-tuned / baseline TF-IDF | **MASSIVE** (51 idiomas, por intención) |
  | Traducción | **NLLB-200 distilled** | **FLORES-200** para evaluar |
  | ASR | Whisper-small/MMS | **Common Voice**, **FLEURS** para evaluar |
  | TTS | MMS-TTS / Piper | — |
  | Resumen/pre-evaluación (solo para el humano) | LLM pequeño local (ej. clase 1–4B cuantizado) con **salida estructurada y plantillas** | — |
- **Motor de políticas por clínica:** archivo YAML/JSON versionado (ver §3). Es el "panel de personalización clínica".
- **Seguridad:** TLS, cifrado en reposo, secretos fuera del repo, RBAC (médico, enfermera, admin), **log de auditoría inmutable** (append-only con hash encadenado).

#### D. Interfaz del personal (la parte que mide el impacto en la clínica)
- **Bandeja de casos** ordenada por prioridad con: resumen, nivel de confianza, razón de la alerta ("detecté: *dificultad para respirar*"), y **botones de 1 clic**: ✅ Confirmar urgencia · ⬇️ Bajar a rutina · 📞 Llamar · ❓ Pedir aclaración.
- Alerta sonora/visual para Nivel Alto. Contador de "tiempo hasta atención humana".

### 1.4 Decisiones tecnológicas con alternativas (para el documento/video)

| Decisión | Elegida | Alternativa | Por qué |
|---|---|---|---|
| Canal primario | SMS + IVR DTMF | App/WhatsApp | Noor tiene teléfono básico; "si un SMS lo resuelve, no uses IA" → la IA entra donde SMS solo no alcanza (ver §1.5) |
| Sync | Store-and-forward + MQTT | REST en tiempo real | Conectividad intermitente |
| Datos en nodo | SQLCipher | Archivos planos | Teléfono perdido/compartido |
| IA al paciente | Lista cerrada de respuestas | LLM generativo libre | Evita alucinaciones |
| Evaluación IA | Benchmarks públicos + set propio | Sólo "se ve bien" | Puntaje de *Data grounding* y *Evidence it works* |

### 1.5 ¿Por qué IA y no solo SMS/hoja de cálculo? (criterio 15 % "Value proposition for AI")
Esto **hay que defenderlo explícitamente** en el video. Propuesta de argumentación:
- Un **SMS con menú** resuelve citas y recordatorios → **eso no necesita IA y lo decimos con honestidad**.
- La IA aporta donde el menú falla: **(1)** entender texto/voz libre en lengua local y mapearlo a una **intención** sin obligar a Noor a aprender comandos; **(2)** **priorizar** mensajes con señales de alerta entre decenas de mensajes para un personal saturado; **(3)** **traducir/resumir** para el personal; **(4)** reducir captura manual de registros (documentación asistida revisada por humano).
- Medir con un experimento: *menú SMS puro* vs *menú + IA* en tasa de mensajes mal encaminados y tiempo hasta atención de urgencias.

---

## 2. User Journey (de la llamada/SMS a la resolución)

### 2.1 Flujo principal

```
[1] Noor contacta → [2] Identificación → [3] Consentimiento → [4] Captura de motivo
        → [5] Clasificación + reglas → [6] Bifurcación → [7] Resolución → [8] Seguimiento → [9] Cierre/Auditoría
```

| # | Paso | Qué ocurre | Dónde corre | Modo sin red |
|---|---|---|---|---|
| 1 | **Contacto** | Noor llama o manda SMS al número de la comunidad | Nodo | ✅ |
| 2 | **Identificación** | Reconocer número → perfil pseudónimo (`patient_id` hash). Si es nuevo, alta mínima (idioma preferido, comunidad). **No** se pide nombre completo por SMS | Nodo | ✅ |
| 3 | **Consentimiento** | IVR/SMS: *"Para ayudarle guardamos sus datos de forma segura. Marque 1 si acepta, 2 si no."* Se registra `consent_id, timestamp, versión del texto, canal, hash`. Sin consentimiento → solo derivación humana, sin guardar contenido clínico | Nodo | ✅ (auditable, DTMF) |
| 4 | **Motivo** | Menú DTMF: 1 cita · 2 resultados/seguimiento · 3 "me siento mal" · 4 hablar con una persona. Opción 3 admite frase libre corta (voz→texto o SMS) | Nodo (+ASR) | ✅ (DTMF) / parcial (ASR) |
| 5 | **Clasificación** | (a) **Reglas de señales de alerta** → (b) clasificador de intención → (c) puntuación de confianza | Nodo | ✅ |
| 6 | **Bifurcación** | Según política de la clínica (ver §3): **Alto / Medio / Bajo** | Nodo + política | ✅ |
| 7a | **Alto – Urgencia** | Alerta inmediata al personal de guardia (SMS prioritario/local); Noor recibe mensaje fijo: *"Hemos avisado a una persona. Si es grave, vaya ya a la clínica / llame a emergencias."* La IA **no** intenta resolver | Nodo → Servidor | ✅ alerta local |
| 7b | **Medio – Duda** | La IA genera pre-resumen para el humano + **una pregunta de aclaración** de lista cerrada; el humano valida con 1 clic | Nodo/Servidor + panel | Cola hasta tener red; el nodo hace la primera pregunta |
| 7c | **Bajo – Rutina** | Cita/recordatorio/FAQ de **lista cerrada**; la cita se **propone** y la confirma la clínica o se auto-confirma si la política lo permite | Nodo/Servidor | ✅ (cola) |
| 8 | **Seguimiento** | Recordatorios por SMS (hora/lugar), recordatorio de seguimiento; si no responde → marca para humano (no insiste indefinidamente) | Servidor/Nodo | ✅ (programados localmente) |
| 9 | **Cierre** | Estado `resuelto/derivado/sin respuesta`; se registran métricas y auditoría; el registro puede exportarse a DHIS2 [ROADMAP] | Servidor | Sync diferido |

### 2.2 Guion de ejemplo (para la demo)

**Caso A – Rutina (SMS):**
1. Noor: `quiero cita para mi hijo la proxima semana`
2. Sistema: consentimiento ya registrado → intención `agendar_cita` (confianza 0.93) → Nivel Bajo.
3. Sistema → Noor: *"Le propongo martes 10:00. Responda 1 para confirmar, 2 para otra hora."*
4. Noor: `1` → cita creada, recordatorio programado 24 h antes.

**Caso B – Urgencia (voz/SMS):**
1. Noor: `mi esposa no puede respirar bien`
2. Regla de alerta (`dificultad_respirar`) → **Nivel Alto sin importar la confianza del modelo**.
3. Alerta inmediata al personal de guardia + mensaje fijo a Noor + registro de hora de alerta y de respuesta humana.

**Caso C – Duda (baja confianza):**
1. Noor: `me duele y no se qué es`
2. Intención ambigua (confianza 0.48) → Nivel Medio → pregunta de aclaración cerrada: *"¿Es un dolor muy fuerte? 1 = sí, 2 = no"*.
3. Resumen al panel; el humano decide con 1 clic. Si no hay respuesta en X minutos → **escala a Nivel Alto por seguridad**.

**Caso D – Sin red:**
1. El servidor no está accesible. El nodo atiende A, B y C localmente, **alerta localmente** y encola. Al volver la red: sync con `event_id` idempotente.

### 2.3 Estados de error (parte del *fail-safe*)
- ASR no entiende → repetir una vez → luego **transferir a persona** (nunca adivinar).
- Idioma no detectado/no soportado → mensaje fijo bilingüe + ruta humana.
- Sin consentimiento → no se almacena contenido clínico; solo se ofrece contacto humano.
- Corte de energía durante la llamada → el evento parcial se guarda con estado `incompleto` y se reintenta contacto por SMS.

### 2.4 Qué NO hace el sistema (límites duros — lo dice el concept note)
- **No diagnostica**, no interpreta imágenes ni estudios, no recomienda tratamientos ni dosis.
- No cierra por sí mismo un caso clínico ni cancela una urgencia.
- No genera texto libre dirigido al paciente (solo plantillas aprobadas por la clínica).

### 2.5 Evaluación de la experiencia de Noor (inclusión)
Frases cortas, número de pasos ≤ 4 antes de resolución, DTMF como alternativa a voz, repetición con tecla `*`, y opción `0` = hablar con una persona **en cualquier momento**.

### 2.6 Lengua local (requisito obligatorio)
- **Decisión pendiente del equipo (resolver en las primeras 2 h):** nombrar **una** lengua de la interacción. Criterio: elegir una que **el equipo pueda validar** con hablantes y que tenga datos (Common Voice / FLEURS / FLORES-200 / MMS).
- Sugerencia: usar una lengua con datos abiertos como **proxy** (por ejemplo, **suajili**) para demostrar el pipeline, **declarando abiertamente** que Ondera es ficticia y que la lengua real requeriría validación comunitaria.
- **Preparar la respuesta a "¿y en una lengua menos soportada?":** degradación escalonada → (1) menú DTMF con audios grabados por la comunidad (no requiere ASR/TTS), (2) clasificador por palabras clave reunidas con la comunidad, (3) ruta humana. Las contribuciones de grabaciones pueden devolverse a **Common Voice** (Mozilla).

---

## 3. Matriz de personalización y reglas de decisión clínica (Human-in-the-Loop)

### 3.1 Niveles de autonomía configurables por clínica

| Nivel | Nombre | Qué hace la IA | Qué hace el humano | Latencia objetivo |
|---|---|---|---|---|
| **A0** | Solo enrutar | Clasifica y encola. Nada al paciente salvo acuse fijo | Todo | según clínica |
| **A1** | Asistente (default) | Rutina: propone cita/recordatorio. Duda: pre-resumen + pregunta. Urgencia: alerta | Aprueba citas y casos Medio; atiende Alto | Alto: inmediata |
| **A2** | Autónomo en rutina | Rutina 100 % automatizada (citas/recordatorios/FAQ de lista cerrada) | Revisa muestreos y atiende Medio/Alto | Rutina: automática |

> **Regla irrenunciable en todos los niveles:** Urgencia (Nivel Alto) **siempre** requiere humano. La clínica puede subir la autonomía en rutina, **nunca** en urgencias.

### 3.2 Matriz de bifurcación por nivel de riesgo

| Nivel | Disparador | Acción automática | Acción humana | Canal de alerta | Escalamiento si no hay respuesta |
|---|---|---|---|---|---|
| 🔴 **Alto** | Regla de señal de alerta **o** modelo con prob. de urgencia ≥ `umbral_alto` | Mensaje fijo a paciente + alerta prioritaria | Llamar/atender de inmediato; confirmar o bajar | SMS prioritario + alerta local sonora + panel | Reintento cada *N* min → siguiente contacto de guardia → director |
| 🟡 **Medio** | Confianza < `umbral_confianza` **o** prob. de urgencia entre `umbral_medio` y `umbral_alto` | Pre-evaluación para el humano + 1 pregunta cerrada al paciente | Valida con 1 clic (confirmar urgencia / bajar a rutina / pedir aclaración) | Panel + notificación normal | Tras *M* min **sube a Alto** (fail-safe) |
| 🟢 **Bajo** | Intención de rutina con confianza ≥ `umbral_rutina` y sin señales de alerta | Cita, recordatorio, FAQ (lista cerrada) | Revisión por muestreo (según A1/A2) | Panel (sin alarma) | Si el paciente responde algo inesperado → pasa a Medio |

### 3.3 Archivo de política por clínica (ejemplo)

```yaml
clinic_id: clinica_ondera_01
autonomy_level: A1            # A0 | A1 | A2
language_default: sw          # lengua nombrada en la demo (proxy)
thresholds:
  alto_urgencia: 0.70         # prob. de urgencia para Nivel Alto
  medio_urgencia: 0.35
  confianza_minima: 0.60      # debajo de esto -> Medio, nunca respuesta automática
red_flags:                    # lista cerrada, definida/validada por personal clínico
  - id: dificultad_respirar
    keywords_sw: ["...", "..."]   # a completar con hablante nativo
    nivel: alto
  - id: sangrado_intenso
    nivel: alto
  - id: embarazo_complicacion
    nivel: alto
escalation:
  alto:  {retry_min: 3, chain: [guardia_1, guardia_2, director]}
  medio: {timeout_min: 20, on_timeout: subir_a_alto}
allowed_patient_replies: [cita_propuesta, recordatorio, derivar_persona, mensaje_urgencia_fijo, faq_horarios]
data_retention_days: 365
```

> ⚠️ **La lista de señales de alerta NO la inventamos nosotros.** En la demo se usa una lista **ilustrativa y rotulada como tal**; en un despliegue real la define y valida el personal clínico (usar guías oficiales de triaje como base). Decirlo en el video suma en "Responsible AI".

### 3.4 Reglas de decisión (pseudocódigo)

```python
def decidir(evento, politica):
    if not evento.consentimiento:
        return derivar_humano(evento, motivo="sin_consentimiento")

    if hay_red_flag(evento.texto, politica.red_flags):      # reglas ganan al modelo
        return Nivel.ALTO

    intencion, conf, p_urg = clasificador(evento.texto)

    if conf < politica.confianza_minima:
        return Nivel.MEDIO                                    # "no estoy seguro — que lo vea una persona"
    if p_urg >= politica.alto_urgencia:
        return Nivel.ALTO
    if p_urg >= politica.medio_urgencia:
        return Nivel.MEDIO
    if intencion in INTENCIONES_RUTINA:
        return Nivel.BAJO
    return Nivel.MEDIO                                        # ante la duda, humano
```

Principios: **(1)** ante la duda, subir de nivel; **(2)** nunca bajar un caso sin un humano; **(3)** nunca responder texto libre al paciente; **(4)** toda decisión se registra con su razón.

### 3.5 Privacidad, consentimiento y seguridad (criterio *pass/fail*)

| Tema | Medida |
|---|---|
| **Dónde están los datos** | Nodo: SQLCipher (cifrado en reposo). Servidor: Postgres cifrada. Declarar explícitamente |
| **Quién puede leerlos** | RBAC: personal clínico autorizado por clínica; admin técnico **sin** acceso a contenido clínico; logs de acceso |
| **Teléfono perdido o compartido** | Datos del nodo cifrados con clave derivada de PIN del operador; **borrado remoto** al reconectar; el teléfono de Noor **no almacena** datos clínicos; SMS al paciente **sin información sensible** (ej.: "Su cita es el martes 10:00" sin diagnóstico) |
| **Consentimiento** | DTMF "1 = acepto" + registro auditable (id, versión de texto, timestamp, canal). Revocable con "marque 9" |
| **Minimización** | Identificador pseudónimo; guardar solo lo necesario; retención configurable |
| **Sesgo** | Declarar que los datos de entrenamiento no cubren la lengua/dialecto real; medir error por subgrupo (lengua/género de voz si hay datos); plan de revisión humana de falsos negativos |
| **Auditoría** | Log append-only: entrada, decisión, razón, humano que actuó, tiempos |
| **Ciberseguridad** | TLS, rotación de claves, sin secretos en repo, actualización de nodos; riesgo conocido: SMS no es canal cifrado → no enviar datos clínicos por SMS |

### 3.6 Riesgos y mitigaciones

| # | Riesgo | Prob. | Impacto | Mitigación | Dueño |
|---|---|---|---|---|---|
| R1 | **Falso negativo en urgencia** (la IA no detecta un caso grave) | Media | **Crítico** | Reglas deterministas > modelo; umbrales conservadores; Medio sube a Alto por timeout; ruta `0 = persona`; medir **recall de urgencias** | ML + clínico |
| R2 | Falsa alarma masiva → fatiga del personal | Media | Alto | Umbrales configurables por clínica; botón "bajar a rutina" con retroalimentación; métrica de precisión | Producto |
| R3 | Alucinación | Baja (diseño) | Alto | Lista cerrada de respuestas; sin generación libre al paciente | ML |
| R4 | ASR falla en la lengua local | **Alta** | Alto | DTMF primero; ASR solo apoyo; degradación escalonada §2.6 | Voz |
| R5 | Hardware reciclado inestable/sin batería | Alta | Medio | Watchdog, reinicio automático, cola persistente en disco, power bank | HW |
| R6 | 2G apagado → módem GSM inútil | Media | Alto | Verificar red antes; módem 4G o Android como pasarela | HW |
| R7 | Fuga de datos de salud | Baja | **Crítico** | Cifrado, minimización, sin datos clínicos por SMS, RBAC, borrado remoto | Seguridad |
| R8 | Datos de entrenamiento no representativos | **Alta** | Alto | Declarar "lo que los datos no cubren"; sets de prueba locales; humano en el lazo | Datos |
| R9 | Sin registro/ID de pacientes ni institución receptora (precondición) | Media | Alto | Alta mínima por teléfono; **integración DHIS2** como camino [ROADMAP]; piloto con una clínica aliada | Producto |
| R10 | **Alcance excesivo en 48 h** | **Alta** | Alto | Congelar alcance en H+4; demo con simulador; todo lo demás va a "Roadmap" | PM |
| R11 | Lengua local no validada con hablantes | Alta | Medio | Declararlo; usar proxy con datos abiertos; plan de co-diseño | Equipo |
| R12 | Licencias de datasets | Media | Medio | Verificar términos antes de usar (el concept note lo exige); registrar licencia y tamaño en tabla de datos | Datos |

---

## 4. Datos: qué usamos, qué prueba el problema y qué NO cubre

> El concept note puntúa explícitamente (a) citar fuente/año/país del problema y (b) declarar **qué NO cubren** los datos. Llenar esta tabla **durante** el hackathon.

### 4.1 Datos que **demuestran el problema** (Tipo 1)
| Evidencia | Fuente | País/Año | Cómo se usa |
|---|---|---|---|
| Ausentismo y falta de equipo/medicinas en clínicas | **Service Delivery Indicators (World Bank)** | *(elegir país + año)* | Cifra del problema en la frase del video |
| Densidad de personal de salud / brechas | **WHO Global Health Observatory** | *(país, año)* | Escala de la escasez |
| Distancia/tiempo a la clínica | **Malaria Atlas Project travel-time**, **healthsites.io** | *(país, año)* | Por qué importa el nodo comunitario |
| Teléfono básico vs smartphone (brecha de género) | **GSMA Mobile Gender Gap Report** | *(país, año)* | Por qué voz/SMS |
| Cobertura de red | **OpenCelliD** | — | Mapa de zonas sin señal |
| Inclusión financiera/móvil | **Global Findex** | — | Contexto de acceso móvil |

> Si una cifra viene de **datos sintéticos o modelados** (p. ej., superficies de tiempo de viaje), **indicarlo**, como pide el documento.

### 4.2 Datos con los que **construimos** (Tipo 2)
| Dataset | Fuente | Licencia | Tamaño | Uso | **Qué NO cubre** |
|---|---|---|---|---|---|
| MASSIVE | Amazon | *(verificar)* | ~1 M enunciados, 51 idiomas | Entrenar/evaluar intención | No son mensajes de salud rural reales; dominio de asistente virtual |
| Common Voice | Mozilla | CC0 | *(según lengua)* | ASR | Voces voluntarias, no ruido de campo ni acentos locales completos |
| FLEURS | Google | *(verificar)* | ~100 idiomas | Evaluación ASR | Habla leída, no espontánea |
| FLORES-200 / NLLB-200 | Meta | *(verificar)* | 200 idiomas | Traducción y evaluación | Vocabulario médico limitado |
| Datos sintéticos propios (SMS de ejemplo) | Equipo | propia | *(N)* | Prueba de clasificador | **Sintéticos — etiquetados así**; no reflejan lenguaje real |

> **Nota de alcance:** el sector Salud **no lista datasets de imágenes médicas o diagnóstico a propósito** (interpretarlos está fuera de límites). Este proyecto **no** hace diagnóstico por imagen.

### 4.3 Evaluación mínima que sí podemos mostrar
- Clasificador de intención: **accuracy/F1 macro** en MASSIVE (idioma elegido) + set sintético propio.
- **Recall en el conjunto de señales de alerta** (métrica prioritaria): objetivo declarado ≥ 0.95 en el set ilustrativo, **con la advertencia** de que no es validación clínica.
- Latencia: tiempo SMS→alerta local sin red (objetivo: < 5 s).
- Prueba de **modo sin conexión**: video con el servidor apagado.

---

## 5. Plan de trabajo por fases — fin de semana del hackathon

> **Ventana:** sábado 3 – domingo 4 octubre 2026. Las horas son **relativas (H+n)** desde el arranque de tu equipo; ajustar a la hora límite real de entrega indicada en la plataforma de Hack-Nation.
> **Meta:** al final del fin de semana existe un **flujo de extremo a extremo funcionando** (SMS/IVR → nodo → clasificación → alerta/cita → panel humano → sync) + **video de 2–5 min** + **repo/enlace**.

### Roles sugeridos (equipo de 3–5)
| Rol | Responsabilidad |
|---|---|
| **PM / Clínico-Producto** | Alcance, política clínica ilustrativa, guion del video, evidencia/datos |
| **Edge/Hardware** | Nodo (Android/Termux), pasarela SMS/voz, store-and-forward |
| **IA/Datos** | Clasificador, reglas, evaluación, datasets y tabla de "lo que no cubre" |
| **Backend/Panel** | API, base de datos, panel HITL, auditoría/consentimiento |
| **Demo/Video** | Grabación, slides, narrativa, "tu visión" de localizar la IA |

### Fase 0 — Alineación y congelamiento de alcance (H+0 → H+2)
- [ ] Leer concept note y **Annex A** completos (rúbrica §09, entregables §08).
- [ ] Fijar **lengua local**, país/contexto de evidencia (SDI/GHO), y **un solo flujo** a demostrar de punta a punta.
- [ ] Definir **MVP vs Roadmap** (ver §6). Congelar alcance en **H+4**.
- [ ] Crear repo, tablero, convenciones; elegir stack final.
- **Salida:** documento de alcance de 1 página + repositorio.

### Fase 1 — Esqueleto técnico (H+2 → H+8)
- [ ] Nodo: recibir SMS (gateway Android o simulador) → guardar en SQLite → cola store-and-forward.
- [ ] Servidor: API `/events` idempotente + Postgres/SQLite + login básico.
- [ ] IVR simulado (DTMF) con consentimiento **registrado**.
- [ ] Panel mínimo: lista de casos por prioridad.
- **Salida (demo interna):** SMS entra y aparece en el panel; apagar el servidor no pierde el mensaje.

### Fase 2 — IA + reglas de decisión (H+8 → H+16)
- [ ] Reglas de señales de alerta (lista ilustrativa) + pruebas unitarias.
- [ ] Clasificador de intención (baseline TF-IDF/LogReg → opcional modelo pequeño) con **umbrales y confianza**.
- [ ] Motor de políticas YAML por clínica; niveles A0/A1/A2.
- [ ] Respuestas de **lista cerrada** + plantillas en la lengua elegida.
- [ ] Fail-safe: "no estoy seguro — que lo vea una persona".
- **Salida:** los 4 casos del guion (A, B, C, D) producen el nivel esperado.

### Fase 3 — Validación de datos y evidencia (H+14 → H+22, en paralelo)
- [ ] Tabla Tipo 1 (problema) con **fuente, año, país** completa.
- [ ] Tabla Tipo 2 (datos de construcción) con **licencia, tamaño y "qué NO cubre"**.
- [ ] Métricas: F1, **recall de urgencias**, latencia, prueba offline.
- [ ] Revisión de sesgos y límites; redactar sección Responsible AI (consentimiento, privacidad, teléfono perdido).
- [ ] Verificar términos de uso de cada dataset.
- **Salida:** `DATA_CARD.md` + gráfica/tabla de resultados.

### Fase 4 — Integración, resiliencia y pulido (H+20 → H+30)
- [ ] Prueba de extremo a extremo con **corte de red simulado**.
- [ ] Panel: botones de 1 clic, alerta sonora, métricas simples (tiempo hasta atención).
- [ ] Voz: ASR/TTS **solo si hay tiempo**; si no, demo con DTMF + audio pregrabado (declararlo).
- [ ] Hardening mínimo: cifrado SQLCipher, RBAC, log de auditoría.
- **Salida:** build estable y *feature freeze* en **H+30**.

### Fase 5 — Demo y entregables (H+30 → H+40, antes de la hora límite)
- [ ] Guion del video (2–5 min) — plantilla en §7.
- [ ] Grabación de pantalla del flujo A→D + diapositiva de arquitectura.
- [ ] README con instrucciones de ejecución + enlace al prototipo/código.
- [ ] Subir a la plataforma: **prototipo + video** (sin video no pasa a la shortlist).
- [ ] Ensayo de la narración con cronómetro.
- **Salida:** entrega enviada con margen (≥ 2 h antes del límite).

### Buffer
Reservar al menos **15 % del tiempo** como colchón; las fases 4–5 siempre se comprimen.

### Hitos de control (go/no-go)
| Hito | Criterio | Si falla |
|---|---|---|
| H+4 | Alcance congelado | Recortar a un solo flujo |
| H+8 | SMS→nodo→panel funciona | Simular entrada con scripts y seguir |
| H+16 | Reglas + clasificador clasifican los 4 casos | Reducir a reglas + baseline |
| H+22 | Tablas de datos completas | Prioridad sobre ASR/TTS |
| H+30 | Feature freeze | Solo bugs críticos y video |

---

## 6. Alcance: MVP del hackathon vs Roadmap

| Componente | MVP (se construye) | Roadmap (se describe) |
|---|---|---|
| Canal SMS | ✅ gateway Android o simulador | Integración con operador/short code |
| Canal voz | ✅ IVR por DTMF simulado | Módem/pasarela GSM real; ASR/TTS en lengua local |
| Nodo comunitario | ✅ 1 celular (o emulación) con SQLite + cola | Malla de varios nodos, OTA |
| Store-and-forward | ✅ con idempotencia | Compresión, priorización avanzada |
| Small AI | ✅ reglas + clasificador de intención | Traducción on-device, resumen con LLM pequeño |
| Motor de políticas | ✅ YAML con 3 niveles | Editor visual para la clínica |
| Panel HITL | ✅ bandeja + 1 clic | App móvil para el médico |
| Consentimiento/auditoría | ✅ DTMF + log | Firma/consentimiento verbal grabado |
| DHIS2 | ❌ | ✅ exportación de resumen a DHIS2 |

---

## 7. Guion del video (2–5 min) — mapeado a la rúbrica

| Tiempo | Bloque | Contenido | Criterio que cubre |
|---|---|---|---|
| 0:00–0:30 | **Problema** | La frase de una oración + 1–2 cifras con fuente/año/país | Relevancia (20 %), Data grounding (15 %) |
| 0:30–1:15 | **Qué hace la IA y por qué no basta un SMS** | Dónde entra la IA, dónde NO; guardrails (lista cerrada, humano decide, fail-safe) | Valor de la IA (15 %), Responsible AI (pass/fail) |
| 1:15–3:15 | **Demo end-to-end** | Casos A (rutina), B (urgencia), C (duda), D (sin red) | Solución construida (25 %), Evidencia (15 %) |
| 3:15–4:00 | **Dónde vive en el día de Noor + stack** | Cuándo marca, qué pasa después; stack técnico | Claridad/inclusividad |
| 4:00–4:30 | **Escalabilidad y qué sigue** | Otras comunidades, DHIS2, otras lenguas | Escalabilidad (10 %) |
| 4:30–5:00 | **Tu visión: ¿qué significa localizar el desarrollo de IA?** | Reflexión honesta: oportunidades **y riesgos** | Pregunta central del hackathon |

**Ideas para la reflexión "localizar la IA" (borrador):**
- Localizar es **co-diseñar** con la comunidad (lengua, audios, señales de alerta validadas por personal local), no solo traducir.
- Es elegir **tecnología proporcionada**: celulares reciclados y modelos pequeños en lugar de depender de infraestructura inexistente.
- Es aceptar límites: la IA **prioriza y pregunta**; la decisión es de una persona.
- Riesgo candoroso: los datos disponibles no representan la lengua/dialecto real; lo declaramos y proponemos el camino para mejorar (contribuir grabaciones a Common Voice, evaluación con hablantes).

---

## 8. Estructura sugerida del repositorio

```
noorline/
├── README.md                      # cómo correr la demo
├── docs/
│   ├── ARQUITECTURA.md
│   ├── DATA_CARD.md               # tablas Tipo 1 y Tipo 2 + "qué no cubre"
│   ├── RESPONSIBLE_AI.md          # consentimiento, privacidad, sesgo, límites
│   └── POLITICA_CLINICA.md        # niveles A0/A1/A2 + YAML ejemplo
├── node/                          # nodo comunitario (Termux/Android)
│   ├── gateway_sms.py
│   ├── ivr_dtmf.py
│   ├── queue_store_forward.py
│   ├── redflags.py                # reglas deterministas
│   └── intent_model/              # modelo cuantizado (ONNX/TFLite)
├── server/
│   ├── api/                       # FastAPI: /events, /consent, /cases
│   ├── policy_engine/
│   ├── models/                    # traducción, resumen (opcional)
│   └── audit/
├── panel/                         # bandeja HITL
├── data/
│   ├── synthetic_sms.csv          # etiquetado como SINTÉTICO
│   └── eval/
├── policies/
│   └── clinica_ondera_01.yaml
└── tests/                         # reglas, umbrales, idempotencia, modo offline
```

---

## 9. Checklist final de entrega

**Entregables obligatorios**
- [ ] Prototipo funcionando + código o enlace
- [ ] **Video 2–5 min** (obligatorio para shortlist) con: problema, IA y guardrails, demo, brecha/stack, tu visión

**Reglas del concept note**
- [ ] Funciona en un dispositivo que el usuario ya tiene
- [ ] Función central **offline**
- [ ] Modelos pequeños/side-loadables (declarar tamaños)
- [ ] **Una interacción en lengua local nombrada** + respuesta sobre lengua menos soportada
- [ ] Human-in-the-loop + lista cerrada + fail-safe visible en la demo
- [ ] Evitar alucinaciones (sin texto libre al paciente)

**Datos y responsabilidad**
- [ ] Fuentes citadas (fuente, año, país; marcar si son modeladas/sintéticas)
- [ ] Datasets con nombre, fuente, **licencia, tamaño** y **qué NO cubren**
- [ ] Dónde están los datos, quién los lee y qué pasa si se pierde/comparte el teléfono
- [ ] Consentimiento auditable y revocable
- [ ] Sin diagnóstico ni interpretación de estudios médicos

---

## 10. Preguntas probables del jurado (preparar respuesta de 20 s)

1. **¿Por qué IA y no un menú de SMS?** → Texto/voz libre en lengua local, priorización de mensajes, resumen para un personal saturado; y lo que no necesita IA, no la usa.
2. **¿Qué pasa si la IA se equivoca en una urgencia?** → Reglas deterministas > modelo; duda sube de nivel; temporizador escala; `0 = persona`; medimos recall.
3. **¿Y sin internet?** → Nodo autónomo + store-and-forward; demo con servidor apagado.
4. **¿Y en una lengua menos soportada?** → Degradación escalonada: DTMF con audios comunitarios → palabras clave → persona.
5. **¿Qué pasa si roban el celular del nodo?** → SQLCipher, PIN, borrado remoto, sin datos clínicos en el teléfono del paciente.
6. **¿Quién valida las señales de alerta?** → Personal clínico local; en la demo es una lista ilustrativa declarada como tal.
7. **¿Cómo escala?** → Política YAML por clínica, nodos replicables con hardware reciclado, exportación a DHIS2.
8. **¿Qué datos NO cubren?** → Tabla §4.2, dicha explícitamente en el video.

---

*Fin del documento. Mantener este archivo como fuente única de verdad del equipo durante el hackathon; actualizar §6 (MVP vs Roadmap) y §4 (datos) a medida que se tomen decisiones.*
