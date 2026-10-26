# tts_audio: Stufe tts_piper

Stand: 26.10.2026, Phase 1 lauffähig.

## Zweck der Stufe tts_piper

Hier wird aus Text Ton. tts_piper vertont jede ausgewählte Meldung mit Piper, einer lokalen, quelloffenen Sprachsynthese, und schreibt pro Meldung eine WAV-Datei. Dazu kommt eine Liste der Dateien in Sendereihenfolge.

Die Stufe macht nur das. Gong, Lautheit und MP3 erledigt die nächste Stufe. So kann eine zweite Engine später dieselbe Weiterverarbeitung nutzen, ohne sie neu zu bauen.

## Wie Piper arbeitet

Piper wandelt Text in zwei Schritten in Sprache: zuerst in Lautschrift, dann in Klang. Die Lautschrift erzeugt ein Werkzeug, das alle deutschen Stimmen gemeinsam nutzen. Klingt ein Fremdwort bei jeder Stimme gleich falsch, liegt der Fehler deshalb in der Lautschrift, und eine andere Stimme hilft nicht. Korrigiert wird im Text davor, über das Aussprache-Lexikon.

Die Stimme wird einmal pro Lauf geladen, nicht für jede Meldung neu. Das Laden kostet die meiste Zeit.

Die Ausgabe hat 22.050 Messungen pro Sekunde, in Mono. Für Sprache genügt das, Musik bräuchte mehr.

## Satzzeichen steuern die Stimme

Titel und Teaser werden zu einem Text verbunden. Dazwischen kommt ein Punkt, damit die Stimme absetzt. Bewusst ein Punkt und kein Ausrufezeichen: Auch das Ausrufezeichen ist ein Signal für die Betonung und würde jede Schlagzeile aufgeregt klingen lassen.

Beim Hören fiel auf, dass Piper am Satzende nur kurz pausiert, fast wie bei einem Komma. Bei Teasern mit mehreren Sätzen verschwimmen diese dann. Die Lösung: Piper liefert den Ton Satz für Satz, und zwischen zwei Sätze wird eine kurze Stille eingefügt.

## Erkenntnisse aus dem Bau

**Das Ohr ist ein eigenes Prüfwerkzeug.** Alle automatischen Tests waren grün, und trotzdem fielen beim ersten Anhören falsch gelesene Fremdwörter, ausländische Namen und zu kurze Pausen auf. Keine Prüfung auf Textebene findet so etwas.

**Ordner und Reihenfolge sind zwei verschiedene Dinge.** Im Ordner stehen die Dateien nach ihrer Kennung sortiert. Gesendet wird aber in der Reihenfolge der Auswahl. Deshalb liest die nächste Stufe die Liste und nicht den Ordner.

**Varianten ausprobieren, bevor man sie einträgt.** Für ein falsch gelesenes Wort wurden mehrere Schreibweisen direkt mit Piper angehört. Erst die beste kam ins Lexikon, und nur, wenn sie die Bedeutung nicht veränderte.
