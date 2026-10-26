# tts_audio: Stufe normalize

Stand: 26.10.2026, Phase 1 lauffähig. Die Stufe normalize ist gebaut, automatisch getestet und mit echten Daten gelaufen.

## Zweck der Stufe normalize

Eine Sprachsynthese liest, was dasteht. Aus „2,8 %“ wird dann „zwei Komma acht Prozent“, aus einem Datum ein Zahlensalat, aus einem Kürzel ein Buchstabenrätsel. Die Stufe normalize macht Texte deshalb **vorlesbar**: Sie schreibt alle Zahlen, Einheiten, Zeichen und Abkürzungen als gesprochene Wörter aus und rundet Zahlen, wo es inhaltlich erlaubt ist.

Ausgeschrieben wird alles, auch was eine Stimme schon richtig liest. Zwei Gründe: Dasselbe Skript soll später auch mit einer anderen Engine vertont werden, und jede Engine hat andere interne Regeln. Und ob gerundet werden darf, ist eine inhaltliche Entscheidung, die keine Engine trifft.

normalize verändert, prüft aber nicht. Ob etwas übrig geblieben ist, prüft die nächste Stufe, `residue_check`.

## Sechs Durchgänge in fester Reihenfolge

Jeder Text läuft durch sechs Durchgänge:

| Durchgang | Beispiel vorher | nachher |
|---|---|---|
| Aussprache-Lexikon | „Dr. Muster“ | „Doktor Muster“ |
| Datum | „am 3.5.“ | „am dritten Mai“ |
| Uhrzeit | „um 9:15 Uhr“ | „um neun Uhr fünfzehn“ |
| Zahl mit Einheit | „Marktanteil 2,8 %“ | „Marktanteil knapp drei Prozent“ |
| übrige Zahlen | „1.250 Besucher“ | „eintausendzweihundertfünfzig Besucher“ |
| Zeichen | „Muster & Söhne“ | „Muster und Söhne“ |

Die Reihenfolge folgt einer Regel: **das Besondere vor dem Allgemeinen.** Liefe der Durchgang für alle Zahlen vor dem Datum, würde er „3.5.“ als zwei einzelne Zahlen lesen, und das Datum wäre verloren. Kein Absturz, keine Warnung, nur ein falscher Satz.

Das Lexikon läuft zuerst, weil Einträge wie „F&E“ oder ein Name mit Ziffern sonst von späteren Durchgängen zerlegt würden.

## Runden nur auf ausdrückliche Erlaubnis

Gerundet wird ausschließlich, was in einer Whitelist steht. Ein Eintrag nennt die Einheit, Schlüsselwörter, die im Satz stehen müssen, die Stelle, auf die gerundet wird, und einen Mindestbetrag.

Drei Prüfungen müssen bestehen: Es gibt einen Eintrag für die Einheit, ein Schlüsselwort steht im Satz, und die Zahl ist groß genug. Aus „Marktanteil 2,8 %“ wird so „knapp drei Prozent“. Eine Umfrage mit 4,6 % bleibt „vier Komma sechs Prozent“: Bei Umfragen ist der Abstand zur Fünfprozenthürde die eigentliche Nachricht.

Bewusst nie gerundet werden Messwerte, Kurse, Geldbeträge, Quoten und alle Bezeichner wie Datum und Uhrzeit. Aus −0,4 Grad würde sonst „null Grad“, und die Glättewarnung wäre verschwunden.

Gerundet wird kaufmännisch. Pythons eingebautes `round()` rundet das genaue Halbe zur nächsten geraden Zahl, aus 2,5 würde 2.

## Das Aussprache-Lexikon

Manche Wörter erkennt keine Regel: Kürzel, die man als Wort spricht, Namen, Fremdwörter. Dafür gibt es ein Lexikon in einer Konfigurationsdatei, Schreibweise links, Aussprache rechts.

Die Einträge stammen aus echten Daten, nicht aus einer Liste aus dem Kopf. Die Prüfstufe meldet, was übrig bleibt, das Ohr meldet, was falsch klingt. Beides landet im Lexikon und als fester Fall im Testsatz.

Das Lexikon darf nur ändern, **wie** ein Wort klingt, nie **was** gesagt wird. Ein Eintrag, der ein Wort weglässt, wäre eine stille Inhaltsänderung, die keine Prüfung findet.

## Erkenntnisse aus dem Bau

**Laute Fehler sind besser als stille.** Zuerst hängte normalize die ausgeschriebene Zahl an Buchstaben direkt an: Aus einem Kürzel mit Ziffer wurde ein unaussprechliches Wort, still und ohne Warnung. Jetzt bleibt eine Zahl, die an einem Buchstaben klebt, stehen. Die Prüfstufe stoppt den Lauf, der Fall wird einmal bewusst gelöst und ist danach dauerhaft richtig.

**Keine Ziffer übrig heißt nicht richtig.** Eine Ordnungszahl wie „17.“ wird zu „siebzehn.“, und der Punkt wird als Satzende vorgelesen. Das findet keine automatische Prüfung, nur das Ohr.

**Konfiguration darf scheitern, ohne dass die Kette abstürzt.** Ein überzähliges Komma in der Konfigurationsdatei führt zu einem sauberen Abbruch mit Grund statt zu einem Absturz.

**Tests lesen nie die echte Konfiguration.** Sie bringen ihre eigenen kleinen Einträge mit. Sonst würde eine geänderte Datei einen Test rot machen, obwohl der Code stimmt.

## Stand

normalize ist mit doctest und pytest getestet, jeder Weg durch die Hauptfunktion hat einen eigenen Test. Beim ersten Lauf mit echten Daten blieben nach normalize keine Ziffern und keine Sonderzeichen übrig, nur Kürzel, die anschließend ins Lexikon kamen.

Offen sind Ordnungszahlen im Satz, Jahreszahlen vor 2000, Datumsangaben mit Jahr und Bereiche wie „2020 bis 2024“.
