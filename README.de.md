# tts_audio

[English](README.md) | **Deutsch**

tts_audio ist eine Python-Pipeline, die aktuelle Schlagzeilen und Teaser aus RSS-Feeds in ein hörbares Nachrichten-Briefing verwandelt. Eine Restprüfung stoppt den Lauf, sobald im Text noch Ziffern, Abkürzungen oder Sonderzeichen stehen, die die Stimme falsch vorlesen würde.

Das Projekt ist ein Lernprojekt in Arbeit. **Phase 1 ist lauffähig:** Ein Befehl macht aus den aktuellen Feeds eine MP3 mit lokaler Sprachausgabe über Piper. Offen für Phase 1 ist noch ein fester Testsatz, der ohne einen einzigen Aussprachefehler durchläuft. Spätere Phasen bringen ein Hörskript per LLM mit Fact-Check gegen die Quellen, Gemini TTS und einen Podcast-Feed (siehe Fahrplan).

## Pipeline (Phase 1)

```
fetch → clean → normalize → residue_check → select_items → tts_piper → postprocess
```

| Stufe | Eine Aufgabe |
|---|---|
| fetch | Schlagzeilen und Teaser aus RSS-Feeds holen |
| clean | HTML-Reste entfernen, Anführungs- und Bindestriche vereinheitlichen, Leerzeichen ordnen |
| normalize | Text vorlesbar machen: Zahlen, Datum, Uhrzeit, Einheiten, Zeichen, Lexikon; runden nur, wo eine Whitelist es erlaubt |
| residue_check | übrige Ziffern, Kürzel, Zeichen und URLs finden; ein Fund stoppt den Lauf |
| select_items | die neuesten brauchbaren Meldungen behalten (Standard 20) |
| tts_piper | eine WAV pro Meldung mit Piper, Pause zwischen den Sätzen |
| postprocess | Meldungen mit Gong verbinden, Lautheit auf −16 LUFS, eine MP3 schreiben |

Jede Stufe liest die Datei der Stufe davor und schreibt ihre eigene. Prüfende und verändernde Stufen sind getrennt. Welche Stufen laufen, steht in einem Profil, nicht im Code.

## Schnellstart (Windows, PowerShell)

Voraussetzungen: Python 3.11, [ffmpeg](https://ffmpeg.org/) im PATH (zum Beispiel `winget install Gyan.FFmpeg`) und eine deutsche Piper-Stimme.

```powershell
git clone https://github.com/Martin-Frei/tts_audio.git
cd tts_audio
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Die Stimme `de_DE-thorsten-high` von den [offiziellen Piper-Stimmen](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md) laden und beide Dateien (`.onnx` und `.onnx.json`) nach `voices/` legen. Stimmen sind Modelldateien, keine Python-Pakete, und liegen nicht im Repository.

Pipeline starten:

```powershell
python run.py --profile news_piper
```

Das Ergebnis liegt in `data/runs/news/<run_id>/`, die run_id ist die Startzeit (`JJJJ-MM-TT_HHMM`). Stoppt eine Stufe, die Ursache beheben und ab dieser Stufe neu starten:

```powershell
python run.py --profile news_piper --from normalize
```

## Konfiguration

| Datei | Inhalt |
|---|---|
| `config/pipelines.yaml` | Profile: Stufen, Reihenfolge, Einstellungen |
| `config/feeds.yaml` | RSS-Feeds |
| `config/rundung_whitelist.json` | welche Zahlen gerundet werden dürfen, und wie |
| `config/aussprache_lexikon.json` | Aussprache von Namen und Kürzeln |

Das Lexikon wächst aus echten Daten: Jeder Fund der Restprüfung wird einmal behoben und in den Testsatz aufgenommen.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

Kleine Funktionen werden mit doctest im Docstring getestet, Stufen mit pytest und temporären Ordnern. Kein Test nutzt das Internet oder die echten Konfigurationsdateien.

## Fahrplan

1. **Piper:** holen und lokal vorlesen. *Lauffähig, Testsatz in Arbeit.*
2. **Hörskript:** ein LLM schreibt aus den Schlagzeilen ein Skript, eine eigene Stufe prüft jede Aussage gegen die Quelle. *Geplant.*
3. **Gemini TTS:** dasselbe Skript in höherer Qualität. *Geplant.*
4. **Stiltests:** wie Stil-Anweisungen Tempo und Ton verändern, gemessen. *Geplant.*
5. **Docker Compose und Podcast-Feed.** *Geplant.*

## Hinweise

- Verwendet werden nur Titel und Teaser, nie ganze Artikel. Briefings aus fremden Nachrichten bleiben privat und werden nicht veröffentlicht.
- Jedes Audio wird als KI-erzeugt gekennzeichnet (ab Phase 2 im Skript).
- Die Lizenzen von Piper (GPL-3.0) und der Stimme werden vor einer Veröffentlichung des Repositorys geprüft.

Dokumentation der einzelnen Stufen: `A_documentation/doku_public/`.
