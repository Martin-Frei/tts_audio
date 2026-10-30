# tts_audio: Stufe factcheck_apply

Stand: 30.10.2026, Phase 2, Kette läuft bis factcheck_apply.

## Zweck der Stufe factcheck_apply

factcheck urteilt, factcheck_apply führt aus. Die Stufe entfernt jede Meldung, zu der der Fact-Check einen Satz als „nicht belegt“ gewertet hat, und räumt danach die Überleitungen auf, die ohne Inhalt dastehen. Sie fällt selbst kein Urteil und nutzt kein Sprachmodell. Darum ist sie vollständig mit selbst gebauten Daten testbar.

Zwischen Urteil und Ausführung liegt immer eine Datei. So bleibt nachvollziehbar, was der Prüfer gesagt hat und was daraus gemacht wurde.

## Die ganze Meldung, nicht der einzelne Satz

Streicht man nur den beanstandeten Satz, hängen die übrigen Sätze derselben Meldung oft in der Luft. Beispiel: Fliegt „Das Elterngeld bleibt bei bis zu 14 Monaten“, bleibt „Eine geplante Kürzung auf zwölf Monate wird nicht umgesetzt“ stehen, ohne Thema. Deshalb fliegt die ganze Meldung: ihre Quellenzeile und alle ihre Sätze. Das Briefing wird kürzer, aber alles Gesagte ist vollständig und belegt.

## Überleitungen ohne Inhalt

Eine Überleitung bleibt nur, wenn die nächste Zeile zu einer Meldung gehört. Die Reihenfolge ist entscheidend: **erst** die Meldungen entfernen, **dann** die Überleitungen prüfen. Andersherum stünde eine Überleitung noch vor ihrer Meldung, würde behalten, und nach dem Entfernen der Meldung bliebe sie verwaist zurück. Ein Test hält diese falsche Reihenfolge ausdrücklich fest, damit niemand sie später umdreht.

Die Satz-IDs bleiben erhalten, auch wenn Lücken entstehen. Jede ID zeigt weiterhin auf denselben Satz wie im Urteil des Fact-Checks. Neu durchnummerieren würde diese Spur zerstören.

## Freigabe nach einer Prüfung von Hand

Stoppt der Fact-Check, prüft ein Mensch die Urteile und speichert seine Entscheidung in einer **eigenen** Datei neben dem Original. Das Urteil des Modells bleibt als Spur erhalten. factcheck_apply nimmt die geprüfte Datei, wenn es sie gibt, sonst das Original, aber nur mit Status „ok“. Ein ungeprüfter Stopp kommt nie durch.

In der Ausgabe steht, welche Datei angewendet wurde, und zu jeder entfernten Meldung die Begründung des Prüfers.

## Erkenntnisse aus dem Bau

**Kleine Wörter, große Folgen.** Zwei typische Fehler hätten die Stufe still unbrauchbar gemacht. Ein falsch geschriebenes Urteilswort hätte bewirkt, dass nie etwas gestrichen wird. Und ein Vergleich mit `is` statt `in` hätte alle Zeilen entfernt und ein leeres Briefing erzeugt. Beides wäre ohne Fehlermeldung durchgelaufen. Tests für den Normalfall, nicht nur für Fehlerfälle, decken genau das auf.

**Der Fact-Check fand, was die Einteilung übersah.** Im ersten Lauf entfernte die Stufe genau zwei Meldungen: einen Auswanderer-Ratgeber und einen Text über finanzielle Unabhängigkeit. Beide hatte classify nicht als Rauschen erkannt. Ratgeber stecken voller Einschränkungen, die ein Skript gern weglässt, und fallen deshalb im Fact-Check auf.
