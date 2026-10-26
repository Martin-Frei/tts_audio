# tts_audio: Stufe residue_check

Stand: 26.10.2026, Phase 1 lauffähig.

## Zweck der Stufe residue_check

residue_check ist die Endkontrolle vor der Sprachsynthese. Sie prüft den vorlesbar gemachten Text auf alles, was dort nicht mehr stehen darf: Ziffern, Kürzel in Großbuchstaben, Sonderzeichen und Webadressen. Jeder Fund bedeutet, dass die Stufe davor etwas übersehen hat.

Die Stufe hat genau eine Aufgabe: finden. Sie verändert nichts und gibt keinen Text weiter. Ihr Ergebnis ist ein Prüfprotokoll mit Status und Fundstellen. Die Sprachsynthese liest danach den Text der Stufe davor, aber nur, wenn das Protokoll grünes Licht gibt.

Satzzeichen wie Punkt, Komma, Frage- und Ausrufezeichen sind ausdrücklich keine Reste. Sie steuern, wo die Stimme Pausen macht und wie sie betont.

## Null Toleranz, alle Funde auf einmal

Schon ein einziger Fund stoppt den Lauf. Gesucht wird trotzdem bis zum Ende, damit alle Funde in einer Runde behoben werden können. Beim ersten Lauf mit echten Nachrichten waren es 62 Funde, aber nur 21 verschiedene Kürzel. Nach einer Runde Pflege blieb ein einziger Fund, nach der zweiten keiner mehr.

Jeder Fund folgt demselben Kreislauf: Eintrag im Aussprache-Lexikon, Fall in den festen Testsatz, Neustart ab der Stufe, die das Lexikon verwendet. So wird jeder Fehler genau einmal behoben und bleibt danach dauerhaft abgesichert.

## Was die Prüfung nicht kann

Eine ehrliche Grenze gehört dazu: Die Prüfung findet **Reste**, aber keine **falschen Umwandlungen**. Wird eine Ordnungszahl zu „siebzehn.“ mit einem Punkt, der als Satzende vorgelesen wird, ist keine Ziffer mehr übrig. Klingt ein Fremdwort falsch, ebenfalls nicht. Solche Fehler findet nur das Ohr.

Deshalb gibt es zwei Prüfungen: die automatische für jeden Lauf und einen festen Testsatz, der nach jeder Änderung angehört wird.

## Erkenntnisse aus dem Bau

**Prüfen und Verändern gehören getrennt.** Würde die Prüfung Funde selbst reparieren, hätte sie zwei Aufgaben, und niemand wüsste mehr, was die Stufe davor eigentlich geleistet hat.

**Eine Regel, die sich unsicher ist, soll laut scheitern.** Die Stufe davor lässt unklare Fälle bewusst stehen, damit diese Prüfung anschlägt. Ein still falsch umgewandeltes Wort würde dagegen in jeder Sendung landen.

**Die Zählung ist wichtiger als die Zahl.** 62 Funde klingen nach viel Arbeit. Gruppiert und gezählt waren es 21 Einträge, angeführt von einem Kürzel, das 18-mal vorkam.
