# Responsible AI
- **Human-in-the-loop:** la IA clasifica y pregunta; toda decision clinica la toma una persona. Bajar un caso exige actor humano (auditado).
- **Fail-safe:** baja confianza -> "una persona revisara su mensaje"; Medio sin atender en 20 min sube a Alto.
- **Sin alucinaciones:** lista cerrada de respuestas (`REPLIES`), filtrada por politica de la clinica.
- **Datos:** nodo con cifrado de campo (Fernet; SQLCipher en roadmap), telefono pseudonimizado (hash con sal), sin contenido clinico sin consentimiento, revocacion con tecla 9 borra texto pendiente, auditoria con hash encadenado sin texto clinico.
- **Telefono perdido/compartido:** el telefono del paciente no guarda datos; SMS sin informacion sensible; la clave del nodo vive fuera de la base (env/archivo 0600). Borrado remoto: roadmap.
- **Sesgo/limites:** datos sinteticos y suajili proxy; lengua real requiere co-diseno; medir error por subgrupo con datos reales.
