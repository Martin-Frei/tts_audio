# tts_audio: Stufe preprocess_piper

Stand: 30.10.2026, gebaut, Tests und erster Lauf ausstehend.

## Zweck

Seit Phase 2 schreibt ein Sprachmodell das Hörskript Satz für Satz, und jeder Satz trägt eine Kennung und einen Verweis auf seine Meldung. Die Sprachsynthese braucht aber keine Einzelsätze, sondern Stücke, die am Stück gesprochen werden.

`preprocess_piper` schneidet die geprüften Sätze in solche Stücke, hier Segmente genannt. Ein Segment ist eine ganze Meldung mit allen ihren Sätzen, oder eine einzelne Zeile ohne Meldung: Begrüßung, Überleitung zwischen Rubriken, KI-Hinweis. Jedes Segment wird später zu einer Audiodatei.

Die Stufe verbindet nur Texte. Sie fügt keine Wörter hinzu und streicht nichts. Fehlt einem Satz das Satzzeichen am Ende, bekommt er einen Punkt, damit die Stimme absetzt.

## Warum Segmente und nicht Einzelsätze

Einzeln vertonte Sätze klingen abgehackt, weil jeder Satz für die Stimme neu anfängt. Innerhalb einer Meldung soll der Fluss erhalten bleiben. Der Nachteil, dass man nur ganze Meldungen neu vertonen kann, wiegt bei einer lokalen Synthese wenig: Ein ganzes Briefing ist in Sekunden neu gesprochen.

Bei einer Cloud-Synthese, die pro Zeichen kostet, kann die Rechnung anders ausfallen. Deshalb trägt die Stufe den Namen der Engine. Eine andere Engine bekommt ihre eigene Vorbereitung, die Pipeline-Profile wählen die passende.

## Warum vor der Endkontrolle

Die Endkontrolle vor der Sprachsynthese sucht nach allem, was nicht mehr im Text stehen darf: Ziffern, Kürzel, Sonderzeichen. Sie steht direkt vor der Synthese, hinter dieser Stufe. So prüft sie genau das, was gesprochen wird.

Stünde sie davor, wäre alles, was beim Zusammenfügen schiefgeht, ungeprüft. Ein typischer Fehler wäre, statt der verbundenen Sätze die ganze Liste als Text einzufügen, mit eckigen Klammern und Anführungszeichen. Die Endkontrolle findet die Klammern und stoppt, bevor die Stimme sie vorliest.

Im Bild eines Verarbeitungsbetriebs: erst portionieren, dann die Endkontrolle, dann garen.

## Erkenntnisse aus der Planung

**Ein Feldname muss sagen, was drin ist.** Naheliegend wäre gewesen, die Sätze in die alten Felder für Schlagzeile und Teaser zu schreiben, damit die Sprachsynthese unverändert weiterläuft. Dann stünde aber in einem Feld namens Schlagzeile ein beliebiger Satz. Stattdessen heißt die Liste dessen, was in die Engine geht, für jede Engine gleich, und die Endkontrolle liest immer diese Liste.

**Grüne Tests heißen nicht, dass die Kette hält.** Jede Stufe hatte ihre Tests bestanden, mit selbst gebauten Eingaben im alten Format. Dass die Stufen nach dem Umbau nicht mehr zusammenpassten, zeigte erst der Blick darauf, was jede Stufe tatsächlich liest. Jede Stufe prüft deshalb jetzt, ob die erwartete Liste überhaupt da ist, und bricht sonst mit einem klaren Grund ab, statt still mit einer leeren Liste weiterzumachen.
