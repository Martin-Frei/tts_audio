# tts_audio: Stufe factcheck

Stand: 30.10.2026, Phase 2, Kette läuft bis factcheck_apply.

## Zweck der Stufe factcheck

Sobald ein Sprachmodell eigene Sätze schreibt, kann es sich irren, etwas weglassen oder etwas hinzufügen. factcheck prüft deshalb jeden Inhaltssatz des Skripts gegen **seine eigene** Quellmeldung und urteilt: belegt, nicht belegt oder widerspricht. Die Stufe urteilt nur. Sie verändert und streicht nichts; das übernimmt die nächste Stufe, factcheck_apply.

Begrüßung, Überleitungen, Quellenzeilen und KI-Hinweis werden nicht geprüft. Sie stammen vom Code.

## Zwei Prüfer mit getrennten Aufgaben

**Der Code prüft Zahlen.** Jede Zahl im Satz muss in Titel oder Teaser der Quelle vorkommen. Fehlt sie, wird ein „belegt“ zu „nicht belegt“. Der Code darf ein Urteil nur verschärfen, nie abschwächen: Ein „widerspricht“ des Modells bleibt stehen, auch wenn alle Zahlen stimmen. Im Ergebnis steht bei jedem Urteil, wer das letzte Wort hatte.

**Ein Sprachmodell prüft die Bedeutung.** Code sieht Zeichen, keine Bedeutung. Er erkennt nicht, dass „bleibt bei 14 Monaten“ etwas anderes sagt als „bleibt bei bis zu 14 Monaten“. Das kann nur ein Modell, und das ist zugleich seine Schwäche: Es ist nicht zuverlässig. Darum prüft der Code mit, wo er kann.

## Warum ein anderes Modell prüft

Schreibt und prüft dasselbe Modell, sind die Fehler gleichgerichtet. Was es beim Schreiben für eine treue Wiedergabe hielt, hält es beim Prüfen ebenfalls für treu. Der Prüfer sollte deshalb aus einer anderen Familie stammen und mindestens so stark sein wie der Schreiber. Ein schwächerer Prüfer, der Fehler übersieht und trotzdem den Prüfstempel setzt, ist schlimmer als gar keine Prüfung.

Geschrieben wird mit einem kleinen Gemini-Modell, geprüft mit Qwen 3.6, lokal über LM Studio. Welcher Anbieter prüft, steht im Profil. Wer das Projekt auf einem anderen Rechner startet, kann ebenso Gemini als Prüfer eintragen.

## Wann die Pipeline stoppt

Ein einziges „widerspricht“ stoppt die Kette: Ein solches Skript wird nie vertont. Bei „nicht belegt“ gibt es eine Schwelle im Profil, derzeit drei. Darunter läuft die Kette weiter, und die betroffenen Meldungen werden gestrichen. Ab drei Funden ist vermutlich etwas Grundsätzliches faul, und ein Mensch prüft die Urteile, bevor es weitergeht.

## Erkenntnisse aus dem Bau

**Bauchgefühl ist kein Prüfer.** Drei Sätze klangen nach Zusatzwissen des Modells. Der Vergleich mit der Quelle zeigte: Alle drei standen so im Teaser. Genau deshalb prüft der Fact-Check gegen die Quelle und nicht nach Eindruck.

**Ein Cloud-Modell hat Lieferzeiten.** Zur Mittagszeit lieferten mehrere Gemini-Modelle über eine Stunde lang nur Überlastmeldungen und Zeitüberschreitungen. Die Pipeline brach jedes Mal sauber mit Grund ab, kam aber nicht weiter. Der lokale Prüfer ist langsamer, rund vier Minuten pro Briefing, dafür immer erreichbar und ohne Daten nach außen.

**Eine kleine Prüflatte reicht für den Vergleich.** Drei Sätze aus echten Läufen mit bekannter richtiger Antwort, zwei mit fehlender Einschränkung, einer korrekt. Der lokale Prüfer traf alle drei, mit präzisen Begründungen. Jeder weitere Kandidat lässt sich mit denselben drei Sätzen messen.

**Der Prüfer kann auch zu streng sein.** Einmal meldete er einen Widerspruch, wo das Skript nur die Blickrichtung gewechselt hatte: aus „Zuwanderer“ im Zielland wurde „Auswanderer aus Deutschland“, dieselben Menschen. Ein zu strenger Prüfer kostet Zeit, ein zu nachsichtiger lässt Falsches durch. Die Schwelle und die Prüfung von Hand fangen das auf.

**Stimmen und wichtig sein sind zwei Fragen.** Der Fact-Check prüft, ob das Gesagte stimmt. Ob Wichtiges fehlt, ist ein Urteil über Gewichtung, und darüber würden Schreiber und Prüfer nur über Geschmack streiten.
