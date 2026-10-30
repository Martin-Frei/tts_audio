# tts_audio: Prüfung von Hand nach dem Fact-Check

Stand: 30.10.2026, Phase 2 in Arbeit.

## Zweck

Der automatische Fact-Check vergleicht jeden Satz des KI-geschriebenen Hörskripts mit der Quelle. Findet er eine widersprechende Aussage oder zu viele unbelegte Sätze, stoppt die Pipeline. An dieser Stelle entscheidet ein Mensch.

Dafür gibt es ein kleines Werkzeug für die Kommandozeile. Es ist bewusst keine Stufe der Pipeline: Es wird nur nach einem Stopp von Hand gestartet. Danach setzt die Pipeline an der Stelle wieder ein, an der die Urteile ausgeführt werden.

## Was man sieht

Für jeden markierten Satz zeigt das Werkzeug fünf Dinge nebeneinander: den Satz, das Urteil des Prüfers, seine Begründung, die Schlagzeile und den Teaser der Quelle.

Satz und Urteil kommen aus derselben Datei. Würde man den Satz aus dem aktuellen Skript nehmen, könnte es nach einem Neustart eine neue Formulierung sein, zu der die alte Begründung gar nicht mehr passt. Deshalb prüft das Werkzeug zuerst, ob Skript und geprüfter Stand übereinstimmen, und bricht sonst mit dem Hinweis ab, den Fact-Check neu laufen zu lassen.

## Zwei Tasten

Es gibt genau zwei Entscheidungen: **passt** oder **passt nicht**.

- **Passt:** Der Satz gilt als belegt. Weil man damit den Prüfer überstimmt, ist eine eigene Begründung Pflicht.
- **Passt nicht:** Das Urteil des Prüfers bleibt stehen, die Meldung fliegt im nächsten Schritt raus.

Das Urteil selbst wird nie eingetippt. Ein Tippfehler im Urteilswort wäre für den nächsten Schritt ein unbekanntes Wort, und dort würde etwas anderes passieren als gewollt.

Vor dem Speichern zeigt das Werkzeug eine Zählung aller Urteile und fragt nach Bestätigung. Wer abbricht, schreibt nichts, und der Stopp bleibt bestehen.

## Spur in zwei Dateien

Das ursprüngliche Urteil des Prüfers wird nie verändert. Die Entscheidungen des Menschen landen in einer eigenen Datei, die alle Urteile enthält, die geänderten markiert mit „human“. Wer später wissen will, wo eingegriffen wurde, sieht es dort. Wer wissen will, warum der Prüfer anders entschieden hatte, liest die Originaldatei.

## Erkenntnisse aus dem Bau

**Eine Schwelle ist für die Maschine, nicht für den Menschen.** Der Fact-Check stoppt ab einer bestimmten Zahl unbelegter Sätze, weil man dem Sprachmodell dann nicht mehr traut. Würde dieselbe Regel nach der Prüfung von Hand noch einmal angewendet, käme man aus dem Stopp nie heraus, obwohl der Mensch jeden Satz entschieden hat.

**Der ausführende Schritt muss sich selbst schützen.** Beim Bau fiel auf, dass der Schritt, der Meldungen streicht, nur unbelegte Sätze kannte, aber keine widersprechenden. Bisher kam ein Widerspruch dort nie an, weil der Fact-Check vorher stoppte. Mit der Prüfung von Hand hätte eine falsche Zahl den Weg in die Sendung gefunden. Jetzt streicht der Schritt beides, unabhängig davon, wer die Urteile vorher geschrieben hat, ob Werkzeug oder Hand im Editor. Zwei Tests halten genau diesen Fall fest.

**Eine weggelassene Einschränkung ist kein Detail.** Im ersten echten Lauf markierte der Prüfer einen Satz, der eine Bedingung der Quelle wegließ. Ohne sie klang die Aussage absoluter als in der Quelle. Solche Fälle sind der Grund, warum es den Prüfer gibt.
