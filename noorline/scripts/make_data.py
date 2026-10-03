"""Genera data/synthetic_sms.csv. DATOS SINTETICOS (escritos por el equipo), NO son mensajes reales.
Las frases en suajili son ilustrativas y requieren validacion por hablantes nativos."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = {
 "agendar_cita": {
  "es": ["quiero una cita", "necesito cita para mi hijo", "me pueden dar cita la proxima semana", "quisiera agendar una consulta", "cita para manana por favor", "puedo ir a consulta el lunes", "necesito turno con la enfermera", "quiero reservar una cita"],
  "en": ["i want an appointment", "need an appointment for my son", "can i get an appointment next week", "i would like to book a visit", "appointment for tomorrow please", "can i come in on monday", "need to see the nurse", "book me a visit"],
  "sw": ["nataka miadi", "naomba miadi kwa mtoto wangu", "nahitaji kuona daktari wiki ijayo", "naomba miadi kesho", "ningependa kupanga miadi", "naweza kuja kliniki jumatatu", "nataka kuweka miadi", "miadi tafadhali"]},
 "recordatorio": {
  "es": ["recuerdeme mi cita", "a que hora es mi cita", "cuando es mi cita", "mandeme recordatorio de mi cita", "olvide la hora de mi cita", "que dia me toca la consulta", "recordatorio de la vacuna", "confirmar mi cita"],
  "en": ["remind me of my appointment", "what time is my appointment", "when is my appointment", "send me a reminder for my appointment", "i forgot my appointment time", "which day is my visit", "vaccine reminder", "confirm my appointment"],
  "sw": ["nikumbushe miadi yangu", "miadi yangu ni saa ngapi", "miadi yangu ni lini", "tuma ukumbusho wa miadi", "nimesahau saa ya miadi", "nikumbushe chanjo", "thibitisha miadi yangu", "ni siku gani ya miadi"]},
 "seguimiento": {
  "es": ["ya me tome la medicina como sigo", "quiero reportar como sigo despues de la consulta", "mi seguimiento del mes pasado", "ya estoy mejor quiero avisar", "resultados de mi examen", "llegaron mis resultados", "control de mi embarazo", "seguimiento de mi tratamiento"],
  "en": ["i finished my medicine what now", "results of my test", "did my results arrive", "i am better want to report", "follow up on my treatment", "pregnancy follow up", "i took the medicine how am i doing", "update after my visit"],
  "sw": ["nimemaliza dawa naendeleaje", "matokeo ya vipimo vyangu", "yamefika matokeo yangu", "nimepona nataka kuwaambia", "ufuatiliaji wa matibabu yangu", "ufuatiliaji wa ujauzito wangu", "nimekunywa dawa nifanye nini", "habari za ufuatiliaji"]},
 "malestar": {
  "es": ["me duele mucho la cabeza", "tengo fiebre y vomito", "me siento muy mal", "mi hijo tiene fiebre alta", "me duele el pecho", "tengo mareos y dolor", "no me siento bien desde ayer", "mi bebe no quiere comer y esta caliente"],
  "en": ["i have a bad headache", "i have fever and vomiting", "i feel very sick", "my child has a high fever", "my chest hurts", "i feel dizzy and in pain", "not feeling well since yesterday", "my baby will not eat and feels hot"],
  "sw": ["naumwa sana kichwa", "nina homa na kutapika", "najisikia vibaya sana", "mtoto wangu ana homa kali", "kifua kinaniuma", "nina kizunguzungu na maumivu", "sijisikii vizuri tangu jana", "mtoto hataki kula ana joto"]},
 "faq_horarios": {
  "es": ["a que hora abre la clinica", "donde queda la clinica", "cual es el horario de atencion", "cuanto cuesta la consulta", "esta abierta hoy la clinica", "hay vacunas hoy", "que dias atienden", "donde esta la clinica mas cercana"],
  "en": ["what time does the clinic open", "where is the clinic", "what are the opening hours", "how much does a visit cost", "is the clinic open today", "are there vaccines today", "which days are you open", "where is the nearest clinic"],
  "sw": ["kliniki inafunguliwa saa ngapi", "kliniki iko wapi", "masaa ya kazi ni yapi", "bei ya kuona daktari ni ngapi", "kliniki imefunguliwa leo", "kuna chanjo leo", "mnafanya kazi siku gani", "kliniki ya karibu iko wapi"]},
 "hablar_persona": {
  "es": ["quiero hablar con una persona", "pasame con el doctor", "necesito hablar con la enfermera", "llamenme por favor", "hablar con alguien", "no entiendo quiero una persona", "comunicame con un humano", "que me llame alguien"],
  "en": ["i want to talk to a person", "connect me to the doctor", "need to speak with the nurse", "please call me", "talk to someone", "i do not understand i want a person", "connect me to a human", "have someone call me"],
  "sw": ["nataka kuzungumza na mtu", "niunganishe na daktari", "nahitaji kuongea na nesi", "nipigieni simu tafadhali", "naomba kuongea na mtu", "sielewi nataka mtu", "niunganishe na binadamu", "mtu anipigie"]},
}

if __name__ == "__main__":
    out = ROOT / "data" / "synthetic_sms.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "intent", "lang", "source"])
        for intent, langs in D.items():
            for lang, phrases in langs.items():
                for p in phrases:
                    w.writerow([p, intent, lang, "synthetic"])
    print(f"OK {out} ({sum(len(p) for l in D.values() for p in l.values())} filas, SINTETICAS)")
