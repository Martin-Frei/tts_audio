# tts_audio: Stufe postprocess

Stand: 27.10.2026, Phase 1 fertig.

## Zweck der Stufe postprocess

Nach der Sprachsynthese liegt eine Audiodatei pro Meldung vor. postprocess macht daraus eine fertige Sendung: alle Meldungen in Sendereihenfolge, ein kurzer Gong dazwischen, gleichmäßige Lautheit und am Ende eine einzige MP3-Datei.

Alles geschieht mit ffmpeg, einem freien Werkzeug für Audio und Video, in einem einzigen Aufruf.

## Ein Gong ohne Aufnahme

Zwischen zwei Meldungen soll der Hörer merken: Jetzt kommt etwas Neues. Statt eine fremde Aufnahme zu verwenden und deren Lizenz zu klären, erzeugt ffmpeg den Ton selbst aus zwei reinen Tönen, sanft ein- und ausgeblendet und leiser als die Stimme.

Ausgewählt wurde er per Hörtest zwischen zwei Varianten. Ein fröhlicher Dreiklang war zu schnell und hätte zu ernsten Meldungen nicht gepasst. Ein ruhiger Zweiklang passt zu allem.

## Lautheit wie im Podcast

Lautheit wird in LUFS gemessen. Die Einheit bildet ab, wie laut ein Mensch etwas empfindet, nicht wie hoch die Ausschläge der Tonwelle sind. Für Podcasts hat sich ein Zielwert von −16 LUFS eingebürgert. Hält jede Folge diesen Wert, klingt sie im Player so laut wie andere Podcasts.

Die Reihenfolge der Arbeitsschritte ist bewusst gewählt: erst zusammenfügen, dann die Lautheit über die ganze Sendung angleichen, zuletzt in MP3 umwandeln. Der Zielwert gilt für die Folge, nicht für jede einzelne Meldung. Und MP3 ist ein verlustbehaftetes Format, jede Bearbeitung danach würde Qualität kosten.

## Erkenntnisse aus dem Bau

**Formate müssen zusammenpassen.** Audiodateien lassen sich nur dann sauber aneinanderhängen, wenn Abtastrate und Kanalzahl gleich sind. Der Gong wird deshalb direkt im Format der Stimme erzeugt.

**Die Reihenfolge kommt aus einer Liste, nicht aus dem Ordner.** Im Ordner stehen die Dateien nach ihrer Kennung sortiert. Gesendet wird in der Reihenfolge der Auswahl, die die Stufe davor festhält.

**Externe Programme brauchen eigene Fehlerfälle.** Fehlt ffmpeg auf einem Rechner oder scheitert ein Aufruf, bricht die Stufe sauber mit Grund ab, statt abzustürzen. Das wird in Phase 5 wichtig, wenn alles in einem Container läuft.

**Wohin eine Aufgabe gehört, zeigt die Zukunft.** Der Gong gehört nicht zur Sprachsynthese, sondern zur Verpackung. Sonst müsste ihn jede weitere Sprach-Engine noch einmal mitbringen.

## Stand

Die Stufe läuft seit dem ersten vollständigen Durchlauf ohne Änderung und ohne Fehler, mit echten Nachrichten ebenso wie mit dem festen Testsatz. Damit ist Phase 1 abgeschlossen: Ein Befehl erzeugt aus aktuellen Feeds eine fertige, normalisierte MP3.

Offen ist ein automatischer Test für die ganze Stufe. Ab Phase 3 kommt eine zweite Sprach-Engine mit anderer Abtastrate dazu. Dann muss der Gong im passenden Format entstehen.
