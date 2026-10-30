# tts_audio: Stufe classify

Stand: 30.10.2026, Phase 2, Kette läuft bis factcheck_apply.

## Zweck der Stufe classify

Die Feeds liefern über hundert Meldungen ohne verlässliche Rubrik. Für ein Briefing braucht es aber Ordnung: Politik zusammen, Wirtschaft zusammen, Sport ans Ende, und Rauschen wie Lottozahlen gar nicht.

classify ordnet **jeder** Meldung genau eine Rubrik aus einer festen Liste zu und hält fest, **warum**: mit Belegwörtern, die wörtlich in Titel oder Teaser stehen. Die Stufe markiert nur. Sie bewertet nicht, wie wichtig eine Meldung ist, und sie sortiert nichts aus. Das Aussortieren übernimmt die nächste Stufe, select_items.

Die Zuordnung macht ein Sprachmodell. Alles drumherum macht Code: Eingabe vorbereiten, Antwort prüfen, Ergebnis schreiben.

## Die Rubrikenliste

Die Liste liegt in `config/categories.json`, nicht im Code. Zehn Rubriken, jede mit Beschreibung, Abgrenzungen („Nicht: … gehört zu …“) und einer gesprochenen Überleitung. Die Abgrenzungen sind der wichtigste Teil: Sie sagen dem Modell, wo die Grenze zwischen zwei Rubriken liegt.

Einige Grenzen ließen sich nur über Merkmale im Text ziehen:

- **Naturereignisse:** Nicht die Ursache entscheidet, sondern die Folgen. Nennt die Meldung Tote, Verletzte, Evakuierung oder zerstörte Häuser, gehört sie zur Sicherheit, sonst zu Umwelt und Klima.
- **Sicherheit:** Der Ort entscheidet. Inland oder Ausland.
- **Politik:** Entscheidet oder verhandelt eine deutsche politische Stelle, ist es Inlandspolitik, auch wenn es um andere Staaten geht. Bloßes Bestätigen zählt nicht.

Die Liste hat zwei Reihenfolgen: eine **Prüfreihenfolge** vom Speziellen zum Allgemeinen, und eine **Briefing-Reihenfolge**, in der die Rubriken später vorgelesen werden.

## Belege statt Begründungen

Das Modell schreibt keine Begründung in Sätzen, sondern nennt ein bis drei Wörter aus der Meldung. Der Grund: Eine Begründung kann Code nicht prüfen, ein Wort schon. Der Code schaut nach, ob jedes Belegwort wirklich im Text steht, ohne Groß- und Kleinschreibung.

Ein Belegwort, das nicht im Text steht, wird gestrichen und als Warnung festgehalten. Bleibt danach kein echter Beleg übrig, ist die Zuordnung nicht nachvollziehbar, und die Stufe bricht ab. Alle Fehler werden über alle Meldungen gesammelt; der Abbruch kommt erst am Ende, damit alle Probleme in einer Runde sichtbar sind.

## Technischer Ablauf

Die Meldungen gehen in Paketen zu fünf an das Modell, mit fünf Sekunden Pause dazwischen, weil der kostenlose Tarif höchstens fünfzehn Anfragen pro Minute erlaubt. Ans Modell gehen nur Kennung, Titel und Teaser. Ein Antwortschema erzwingt gültiges JSON. Die Meldung selbst kopiert der Code unverändert in die Ausgabe und hängt nur Rubrik und Belege an. So kann das Modell den Text nicht unbemerkt verändern, auf den sich später der Fact-Check stützt.

## Erkenntnisse aus dem Bau

**Ein Sprachmodell würfelt.** Vier Läufe mit null Toleranz scheiterten an vier verschiedenen Meldungen, jedes Mal aus einem anderen Grund: ein selbst gebautes Wort, ein Beleg aus der Nachbarmeldung, Zusatzwissen, ein Tippfehler. Ein Prompt-Satz gegen alle vier gibt es nicht. Erst ein Filter, der falsche Belege streicht, statt abzubrechen, machte die Stufe lauffähig.

**„Der erste Treffer gilt“ ist für ein Modell eine Bitte, kein Algorithmus.** Das Rauschen steht in der Prüfreihenfolge ganz oben, trotzdem landete ein Auswanderer-Ratgeber bei Wirtschaft: Das Modell wählt, was thematisch passt und sich belegen lässt. Was sicher gelten muss, gehört in Code.

**Ein Merkmal muss eindeutig sein.** Ein Versuch, Ratgeber über Floskeln wie „Diese Länder“ oder „Warum“ zu erkennen, sortierte auch Erklärstücke aus, und eine echte Nachricht wie „Polen und Deutschland arbeiten zusammen. Diese Länder …“ wäre ebenfalls im Rauschen gelandet. Eine fehlende Nachricht wiegt schwerer als ein Ratgeber zu viel. Der Versuch wurde zurückgenommen und bleibt in der Versionsgeschichte stehen.

**Eine Einstellung zählt erst, wenn sie im Aufruf ankommt.** Zwei Vergleichsläufe galten als „mit Temperatur null“, der Wert erreichte den Aufruf aber nie. Seitdem gilt: Parameter im Profil und im Aufruf prüfen, bevor verglichen wird.
