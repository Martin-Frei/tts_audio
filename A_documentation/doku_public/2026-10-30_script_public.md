# tts_audio: Stufe script

Stand: 30.10.2026, Phase 2, Kette läuft bis factcheck_apply.

## Zweck der Stufe script

Schlagzeilen sind fürs Lesen geschrieben, nicht fürs Hören: Doppelpunkte, Zitate in Anführungszeichen, verkürzte Sätze. script macht aus den zehn ausgewählten Meldungen ein Briefing, das sich vorlesen lässt.

Dabei ist die Arbeit klar geteilt. Das Sprachmodell schreibt **nur** die Sätze zu jeder Meldung, ein bis drei pro Meldung. Alles andere setzt der Code: Begrüßung, Überleitungen zwischen den Rubriken, die Quellenangabe vor jeder Meldung, der Hinweis auf KI und die Verabschiedung. Was der Code schreibt, ist immer gleich und muss nie geprüft werden.

## Eine Satzliste statt eines Fließtexts

Das Ergebnis ist kein langer Text, sondern eine Liste, ein Eintrag pro Satz, in Vorlesereihenfolge. Jeder Eintrag hat eine Satz-ID, die Kennung seiner Meldung und eine Art: Begrüßung, Überleitung, Quelle, Inhalt, KI-Hinweis, Abschluss.

Diese Form trägt die ganze restliche Kette. Der Fact-Check urteilt über einzelne Sätze und verweist dabei auf ihre ID. Er vergleicht jeden Satz mit genau der Meldung, aus der er stammt. Und die Bereinigung kann eine Meldung samt ihrer Sätze gezielt entfernen.

Die IDs vergibt der Code, erst ganz am Ende. Das Modell vergibt keine Nummern, also kann es sie auch nicht durcheinanderbringen.

## Regeln für das Modell

Der Prompt liegt als Datei in `prompts/`, mit Versionsnummer. Die wichtigsten Regeln: nur Fakten aus Titel und Teaser, kein Zusatzwissen; Zahlen bleiben exakt und als Ziffern, denn Runden und Ausschreiben ist Aufgabe einer späteren Stufe; kurze Sätze; keine Quellenangabe, das ergänzt der Code; und jede Einschränkung und Zuschreibung der Quelle bleibt erhalten.

Der Code prüft die Antwort: Jede Meldung muss genau einmal vorkommen, keine fremde Kennung, kein leerer Satz. Ein Satz über zwanzig Wörter ist nur eine Warnung, kein Fehler. Ein langer Satz leidet an Qualität, nicht an Wahrheit.

## Erkenntnisse aus dem Bau

**Das Modell kürzt an den falschen Stellen.** Ein Vergleich Satz für Satz mit der Quelle zeigte ein klares Muster: Weggelassen wurden genau die Wörter, die eine Nachricht vorsichtig machen. Aus „bei bis zu 14 Monaten“ wurde „bei 14 Monaten“, aus „dürften verfehlt haben“ eine Tatsache, „Einem Bericht zufolge“ verschwand ganz. Eine Regel, die diese Fallen beim Namen nennt und längere Sätze ausdrücklich erlaubt, senkte diese Fehler im Fact-Check von fünf auf null.

**Die Quellenangabe gehört dem Code.** Solange das Modell „Wie das Handelsblatt berichtet“ selbst schrieb, meldete der Prüfer bei neun Sätzen, der Name stehe nicht in der Quelle. Seit der Code diese Zeile aus einer Liste einsetzt, gibt es diese Fehlalarme nicht mehr.

**Die Datei ist die Wahrheit, nicht die Anzeige.** Beim Lesen im Terminal schienen Wörter zusammenzukleben. Eine Suche in der Datei zeigte: Alles war richtig, die Konsole hatte bei achtzig Zeichen umgebrochen. Hätte man den Prompt deshalb geändert, hätte man einen Fehler bekämpft, den es nicht gibt.

**Hören zeigt, was Lesen verbirgt.** Zwei Fassungen derselben Geschichte aus zwei Quellen fallen in einer Liste kaum auf, im Briefing klingen sie wie ein Fehler der Sendung. Die Erkennung von Dubletten bleibt deshalb auf dem Plan.
