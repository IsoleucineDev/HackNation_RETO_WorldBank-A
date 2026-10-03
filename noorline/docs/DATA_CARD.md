# DATA CARD (completar antes de entregar)

## Tipo 1 - evidencia del problema (fuente, anio, pais) -> COMPLETAR
| Evidencia | Fuente | Pais/Anio | Cifra | Nota (modelada/sintetica?) |
|---|---|---|---|---|
| Ausentismo/equipo en clinicas | Service Delivery Indicators (World Bank) | ? | ? | |
| Densidad de personal de salud | WHO Global Health Observatory | ? | ? | |
| Telefono basico vs smartphone | GSMA Mobile Gender Gap Report | ? | ? | |
| Cobertura de red | OpenCelliD | ? | ? | |

## Tipo 2 - datos con los que se construye
| Dataset | Fuente | Licencia | Tamano | Uso | Lo que NO cubre |
|---|---|---|---|---|---|
| synthetic_sms.csv | Escrito por el equipo (`scripts/make_data.py`) | propia | 144 frases (6 intenciones x es/en/sw) | clasificador de intencion | **Sintetico**; no son mensajes reales; suajili sin validacion nativa; sin ruido ortografico ni code-switching |
| (opcional) MASSIVE | Amazon | verificar | ~1M enunciados | ampliar intencion | Dominio asistente virtual, no salud rural |
| (opcional) Common Voice / FLEURS | Mozilla / Google | verificar | segun lengua | ASR (roadmap) | Habla leida; sin ruido de campo |

## Evaluacion medida (reproducible: `make test`)
- Validacion cruzada 5-fold del clasificador: ~0.72 accuracy (frases no vistas). Es un piso bajo a proposito: por eso reglas y humano prevalecen.
- Recall en el set ilustrativo de senales de alerta: 100% (tests/test_core.py::ALERT_SET). **No es validacion clinica.**
- Medidas pendientes: latencia SMS->alerta local, recall por lengua.
