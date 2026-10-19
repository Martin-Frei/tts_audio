# Entwicklungsnotiz 2026-10-16: Setup und erster Piper-Test

## Stand

Phase 1 hat begonnen: lokale Sprachausgabe mit Piper. Die Arbeitsumgebung steht, ein erster Test der Stimme ohne Textnormalisierung ist gelaufen. Als Nächstes wird `fetch.py` geplant, die Stufe, die Schlagzeilen und Teaser aus RSS-Feeds holt.

## Umgebung

| Komponente | Version |
|---|---|
| Python | 3.11.7 |
| feedparser | 6.0.14 |
| num2words | 0.5.14 |
| piper-tts | 1.8.0 |
| PyYAML | 6.0.3 |
| ffmpeg | 9.0.2 (Systemprogramm, nicht über pip) |
| Stimme | `de_DE-thorsten-high` |

Alle Python-Pakete sind in `requirements.txt` exakt gepinnt, getrennt nach direkt gewählten Paketen und ihren Abhängigkeiten. Die Python-Version steht dort als Kommentar, weil pip kein Python installiert.

## Repo-Konventionen

- Nicht im Repo: virtuelle Umgebung, Stimmenmodelle (`voices/`), Laufergebnisse (`data/runs/`), Logs und die `.env`.
- Interne Arbeitsdokumente bleiben lokal. Ins Repo gehen nur Notizen unter `A_documentation/doku_public/`.
- Git erfasst keine leeren Ordner. Ordner, in die der Code schreibt, legt der Code deshalb selbst an.
- Commit-Nachrichten auf Englisch.
- README auf Englisch (`README.md`) und Deutsch (`README.de.md`), gegenseitig verlinkt.

## Erster Test: Piper ohne Normalisierung

Testsatz: „Am 16.10. stieg der DAX um 2,8 % auf 19.450 Punkte, so die ARD.“

| Stelle | Piper sagt | Richtig wäre |
|---|---|---|
| 16.10. | sechzehn Punkt zehnte | sechzehnten Oktober |
| DAX | buchstabiert | Dax, als Wort |
| 2,8 % | zwei Komma acht Prozent | im Briefing gerundet: knapp drei Prozent |
| 19.450 | neunzehntausendvierhundertfünfzig | korrekt |
| ARD | buchstabiert | korrekt |

Zusätzlich auf der Piper-Beispielseite beobachtet: Das Fremdwort „Phänomen“ klingt bei allen deutschen Stimmen falsch betont.

## Folgerungen für normalize

- **Piper hat eingebaute Regeln, aber ihr Verhalten ist nicht vorhersagbar.** Der Tausenderpunkt klappt, das Datum nur halb. Deshalb wird `normalize` gegen einen festen Testsatz geprüft, statt sich auf die Engine zu verlassen.
- **Alles wird ausgeschrieben, auch was Piper schon richtig liest.** Dasselbe Skript soll später auch mit Gemini TTS vertont werden, und jede Engine hat eigene interne Regeln. Die Aussprache liegt damit im eigenen, testbaren Code.
- **Abkürzungen gleicher Form werden unterschiedlich gesprochen** (DAX gegen ARD). Das löst ein Aussprache-Lexikon, keine allgemeine Regel.
- **Fehler, die bei allen Stimmen gleich auftreten**, entstehen bei der Umwandlung von Text in Lautschrift, die alle deutschen Piper-Stimmen gemeinsam nutzen. Eine andere Stimme hilft dann nicht; korrigiert wird im Text davor.
- **Der Testsatz** bekommt neben Datum, Abkürzungen und Zahlen auch Fremdwörter.

## Nächste Schritte

1. `fetch.py` planen: Funktionen, Format der Rohdaten, Sonderfälle wie fehlender Teaser oder doppelte Meldungen.
2. Feed-Auswahl treffen und Adressen prüfen.
3. Ablage der Läufe und Teststrategie festlegen.
4. Testsatz schreiben.
