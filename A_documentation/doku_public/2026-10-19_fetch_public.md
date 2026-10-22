# tts_audio: Stufe fetch

Stand: 21.10.2026, Phase 1 in Arbeit. Die Stufe fetch ist gebaut und vollständig automatisch getestet. Als Nächstes folgt die Stufe clean.

## Zweck der Stufe fetch

Die Stufe fetch ist der Wareneingang der Pipeline tts_audio. Sie lädt aktuelle Meldungen aus mehreren deutschen RSS-Feeds und hält pro Meldung nur Titel, Teaser, Link und Veröffentlichungszeit fest. Das Ergebnis ist eine einzige Datei pro Lauf, die `_raw.json`.

fetch hat genau eine Aufgabe: holen. Die Stufe prüft keine Inhalte, putzt keinen Text und sortiert nichts aus. Diese Aufgaben gehören zu späteren Stufen. So bleibt fetch einfach, einzeln testbar, und die `_raw.json` zeigt jederzeit unverfälscht, was die Quellen geliefert haben.

## Stellung in der Pipeline

Die Pipeline von tts_audio besteht aus Stufen, die jeweils eine Datei lesen und eine Datei schreiben. Welche Stufen laufen, steht in einem Profil, nicht im Code. Der Orchestrator `run.py` ruft die Stufen nacheinander auf.

```
fetch → clean → normalize → residue_check → tts_piper → postprocess
```

Das ist die Kette von Phase 1. fetch steht am Anfang und liefert die Rohdaten für alle folgenden Stufen. Später werden zwischen `clean` und `normalize` zwei Stufen zur Erkennung doppelter Meldungen eingeschoben. Dafür muss an fetch nichts geändert werden, weil `run.py` jeder Stufe ihre Eingabedatei vorgibt.

Namenskonvention: Stufen, die prüfen, enden auf `_check`, Stufen, die ein Urteil ausführen, auf `_apply`. So zeigt schon der Name, ob eine Stufe prüft oder verändert.

## Quellen

fetch liest derzeit drei deutschsprachige Nachrichten-Feeds im Format RSS 2.0. Die Liste steht in `config/feeds.yaml`, getrennt vom Code. Ein neuer Feed ist eine Zeile in dieser Datei, kein Eingriff in den Code. Beim ersten vollständigen Lauf kamen 111 Meldungen aus allen drei Feeds zusammen.

In der Konfiguration stehen die Zieladressen der Feeds, nicht ältere Adressen mit Umleitung. Eine Umleitung kann der Betreiber jederzeit abschalten, die Zieladresse pflegt er selbst.

Verwendet werden ausschließlich Titel und Teaser, keine Volltexte. Die erzeugten Audios aus fremden Nachrichten bleiben privat. Die Beispiele in dieser Dokumentation sind deshalb frei erfunden.

## Ausgabe: die Datei _raw.json

Jede Datei der Pipeline beginnt mit denselben Metadaten: Lauf-ID, Name der Stufe, Erstellungszeit, Status und gegebenenfalls ein Grund. Darauf folgen die Meldungen. Beispiel mit erfundenem Inhalt:

```json
{
  "run_id": "2026-10-19_0800",
  "stage": "fetch",
  "created": "2026-10-19T08:00:14Z",
  "status": "ok",
  "reason": null,
  "items": [
    {
      "id": "m001",
      "source": "feed_a",
      "title": "Beispielstadt eröffnet neue Stadtbibliothek",
      "teaser": "Nach drei Jahren Bauzeit öffnet die Bibliothek am Samstag ihre Türen.",
      "link": "https://example.org/meldung-1",
      "published": "2026-10-19T05:31:49Z"
    }
  ]
}
```

Jede Meldung erhält eine laufende Kennung über alle Feeds eines Laufs, von `m001` an. Zusammen mit der Lauf-ID ist sie eindeutig. Alle Zeiten stehen einheitlich in UTC, Umlaute im Klartext in UTF-8.

## Aufbau des Moduls

Das Modul `src/fetch.py` besteht aus sechs Funktionen mit jeweils einer Aufgabe:

| Funktion | Aufgabe |
|---|---|
| `load_feed_list` | liest die Feed-Liste aus der YAML-Datei |
| `fetch_feed` | lädt einen Feed mit Zeitlimit und erkennt Ausfälle |
| `to_utc` | wandelt eine Zeitangabe in einen einheitlichen UTC-Text |
| `parse_entry` | übernimmt aus einer Meldung die vier benötigten Felder |
| `save_raw` | schreibt die Datei mit Metadaten |
| `fetch` | führt den Ablauf und meldet das Ergebnis an `run.py` |

`fetch` bekommt von `run.py` nur drei Angaben: den Pfad zur Feed-Liste, den Pfad der Ausgabedatei und die Lauf-ID. Alles Weitere entsteht während des Laufs. Zurück gibt `fetch` den Status und den Pfad der geschriebenen Datei.

`run.py` setzt eine Stufe erst dann auf „fertig“, wenn die Datei existiert **und** ihr Status `ok` ist.

## Fehlerbehandlung

Ein Ausfall einzelner Quellen darf den Lauf nicht beenden. Erst wenn gar keine Meldung zusammenkommt, bricht fetch ab.

| Fall | Verhalten |
|---|---|
| Server unbekannt, Zeitlimit überschritten, Fehlerseite | Feed wird übersprungen, Warnung im Log |
| Feed liefert keine Meldungen | Feed wird übersprungen, Warnung im Log |
| Feed mit Formfehlern, aber lesbaren Meldungen | Feed wird genutzt, Warnung im Log |
| Teaser oder Zeitangabe fehlt | Feld wird `null`, die Meldung bleibt erhalten |
| Alle Feeds fallen aus | Status `abort`, Datei mit leerer Liste, `run.py` stoppt |

Auch beim Abbruch wird eine Datei geschrieben. Der Abbruch hinterlässt so eine Spur mit Grund, statt still zu verschwinden.

## Design-Entscheidungen: Daten

**fetch verwirft nichts.** Eine Meldung ohne Teaser oder Datum wird mit leerem Feld gespeichert. Ob sie später gebraucht wird, entscheidet die Stufe, die auswählt. So bleibt die Entscheidung nachvollziehbar und an einer Stelle.

**Laufende Kennung statt Feed-Kennung.** Die Feeds verwenden unterschiedliche Kennungen, mal eine UUID, mal eine Zahl, mal den Link. Eine selbst vergebene laufende Nummer fehlt nie und ist innerhalb eines Laufs nie doppelt.

**Zeiten in UTC.** Die Feeds liefern Zeiten in verschiedenen Zonen, etwa `+0200` und `GMT`. Ohne Umrechnung würden Meldungen beim Sortieren um Stunden verschoben. Mit dem Ende der Sommerzeit ändert sich die Zone zusätzlich. Die Zone steht in jeder einzelnen Zeitangabe und wird beim Einlesen berücksichtigt, nicht fest konfiguriert.

## Design-Entscheidungen: Technik

**Ausfall erkennen an fehlenden Meldungen.** Die Bibliothek `feedparser` setzt ein Warnsignal (`bozo`) sowohl bei echten Ausfällen als auch bei kleinen Formfehlern. Würde jedes Warnsignal als Ausfall gelten, ginge bei einem harmlosen Sonderzeichen ein ganzer Feed verloren. Entscheidend ist deshalb, ob Meldungen ankommen.

**Zeitlimit nur beim Abruf.** `feedparser` hat kein eigenes Zeitlimit. Statt eines globalen Zeitlimits für das ganze Programm lädt fetch die Feeds mit `requests` und einem Zeitlimit von zehn Sekunden. Ein globales Limit würde unbemerkt auch spätere Stufen treffen, etwa die Sprachsynthese, die deutlich länger braucht.

**Konfiguration statt Code.** Feed-Liste, Stufenfolge und Pfade kommen von außen. Nur `load_feed_list` kennt den Aufbau der YAML-Datei.

## Tests

Getestet wird ohne Internetzugriff. Ein Test soll den eigenen Code prüfen, nicht die Verfügbarkeit fremder Server. Jeder Test verwendet eine feste, selbst gewählte Eingabe mit vorher bekanntem Ergebnis. Geprüft wird, was eine Funktion liefert, nicht wie sie intern arbeitet. So bleiben die Tests bei einem Umbau grün, solange das Ergebnis gleich bleibt.

Kleine Funktionen ohne Dateien und Netz werden mit `doctest` direkt im Docstring getestet, alles andere mit `pytest`. Ein einziger Befehl führt beide aus.

| Funktion | geprüft wird |
|---|---|
| `to_utc` | Umwandlung in UTC-Text, fehlende Zeit |
| `parse_entry` | vollständige Meldung, Meldung ohne Teaser und Datum |
| `load_feed_list` | Rückgabe nur der Feeds, ohne äußere Ebene der YAML |
| `save_raw` | Datei existiert, Metadaten, Meldungen unverändert, Umlaute im Klartext |
| `fetch_feed` | Meldungen eines Feeds, Rückgabe `None` bei Netzfehler |
| `fetch` | alle Feeds erreichbar, ein Feed fällt aus, alle fallen aus |

Für Dateien stellt pytest pro Test einen temporären Ordner bereit, der danach wieder verschwindet. Den Netzzugriff ersetzt der Test durch eine eigene Funktion, die einen erfundenen Beispiel-Feed liefert oder gezielt einen Verbindungsfehler auslöst.

Stand: zehn Tests, alle bestanden, Laufzeit unter einer halben Sekunde.

## Erkenntnisse aus dem Bau

**Ein echter Ausfall am ersten Tag.** Wenige Minuten nachdem die Prüfung auf einen fehlenden Feed eingebaut war, lieferte ein Feed tatsächlich unlesbare Daten. fetch übersprang ihn wie vorgesehen. Eine Stunde später war der Feed wieder in Ordnung.

**Stille Fehler sind die gefährlichsten.** Ein vertippter Feldname führt mit `.get` zu keinem Absturz, sondern liefert still einen leeren Wert. Eine falsch zugeordnete Quelle erzeugt plausible, aber falsche Daten. Beides zeigt kein Fehlerlog. Deshalb prüfen die Tests, dass Felder gefüllt sind und zueinander passen.

**Dubletten gibt es schon innerhalb eines Feeds.** Ein Feed lieferte dieselbe Nachricht mehrfach, jeweils anders formuliert. Ein Abgleich über Link oder Kennung erkennt das nicht. Daraus folgt die Entscheidung für eine spätere Dubletten-Erkennung über inhaltliche Ähnlichkeit.

## Stand und nächste Schritte

Die Stufe fetch liefert aus drei Feeds eine vollständige `_raw.json` mit einheitlichem Format. Alle sechs Funktionen sind automatisch getestet, einschließlich der drei Ausfallszenarien des Gesamtablaufs.

Als Nächstes folgt die Stufe `clean`. Erste Beobachtungen dafür stammen bereits aus den echten Daten: Leerzeichen am Textende, Markierungen wie `+++`, Rubriken vor einem Doppelpunkt und typografische Sonderzeichen.

Geplant für später: Erkennung doppelter Meldungen über inhaltliche Ähnlichkeit, aufgeteilt in eine prüfende Stufe `dedup_check` und eine ausführende Stufe `dedup_apply`.
