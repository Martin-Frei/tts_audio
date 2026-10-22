# tts_audio: Stufe clean

Stand: 22.10.2026, Phase 1 in Arbeit. Die Stufe clean ist gebaut und vollständig automatisch getestet. Als Nächstes folgt die Stufe normalize.

## Zweck der Stufe clean

Die Stufe clean ist das Putzen nach dem Wareneingang. Sie liest die `_raw.json` der Stufe fetch, entfernt aus Titel und Teaser jeder Meldung technischen Ballast und bringt Zeichen in eine einheitliche Form. Das Ergebnis ist eine Datei pro Lauf, die `_clean.json`.

clean hat genau eine Aufgabe: Text säubern. Gesäubert wird alles, was in keinem Fall in den Text gehört, unabhängig davon, ob er später vorgelesen, angezeigt oder an ein Sprachmodell gegeben wird. Alles, was nur für das Vorlesen nötig ist, gehört zur Stufe normalize.

Daraus ergibt sich eine einfache Testfrage für jede Regel: Würde man das auch entfernen, wenn der Text nie vorgelesen würde? Lautet die Antwort ja, gehört die Regel zu clean. Lautet sie nein, gehört sie zu normalize.

## Stellung in der Pipeline

```
fetch → clean → normalize → residue_check → tts_piper → postprocess
```

clean steht direkt hinter fetch. Die spätere Erkennung doppelter Meldungen (`dedup_check` und `dedup_apply`) wird hinter clean eingeschoben. Das hat einen Grund: Zwei gleiche Titel, einmal mit `+++` davor und einmal mit einem Leerzeichen am Ende, sehen für einen Vergleich verschieden aus. Erst nach clean sind sie vergleichbar.

`run.py` übergibt clean drei Angaben: den Pfad der `_raw.json`, den Pfad der `_clean.json` und die Lauf-ID. Kein Dateiname steht fest im Code. clean wird nur gestartet, wenn fetch fertig ist, also wenn die Datei existiert und ihr Status `ok` ist.

## Was clean verändert

clean bearbeitet nur die Felder `title` und `teaser`. Kennung, Quelle, Link und Veröffentlichungszeit bleiben unverändert.

| Regel | Beispiel vorher | nachher |
|---|---|---|
| HTML-Tags entfernen, Entities umwandeln | `<b>Eilmeldung</b> Brand &amp; Rauch` | `Eilmeldung Brand & Rauch` |
| typografische Anführungszeichen vereinheitlichen | `„Wir sind bereit“` | `"Wir sind bereit"` |
| Sonderbindestriche vereinheitlichen | `KI‑Strategie` mit geschütztem Bindestrich | `KI-Strategie` |
| wiederholte Symbole entfernen | `+++ Liveblog +++` | `Liveblog` |
| Leerräume zusammenfassen und an den Enden entfernen | `  Brand   in Beispielstadt ` | `Brand in Beispielstadt` |

HTML-Reste sind in den verwendeten Feeds selten, weil fetch nur das Feld ohne HTML übernimmt. Die Regel ist eine Absicherung.

Wiederholte Symbole sind Folgen von mindestens zwei **gleichen** Zeichen aus einer festen Liste, etwa `+++` oder `==`. Ein einzelnes Symbol bleibt, ebenso eine Folge verschiedener Zeichen wie `=>`. Punkte und Ausrufezeichen stehen bewusst nicht in der Liste.

## Was clean bewusst nicht tut

| Aufgabe | Warum nicht in clean | Wer stattdessen |
|---|---|---|
| Meldungen ohne Teaser löschen | Über die Brauchbarkeit einer Meldung entscheidet eine Stelle, nicht mehrere | die Stufe, die auswählt |
| doppelte Meldungen entfernen | Vergleich und Entscheidung sind eigene Aufgaben, getrennt in prüfend und ausführend | `dedup_check`, `dedup_apply` |
| Rubrik vor dem Doppelpunkt entfernen, etwa „Kommentar:“ | Die Rubrik zeigt, dass es eine Meinung ist. Diese Information braucht die Auswahl später | Entscheidung offen |
| Anführungszeichen entfernen, `&` als „und“ schreiben, URLs vorlesbar machen | nur für das Vorlesen nötig | `normalize` |

Daraus folgt eine feste Regel: **clean entfernt nie eine ganze Meldung.** Die Anzahl der Meldungen in der `_clean.json` ist immer gleich der Anzahl in der `_raw.json`.

## Ausgabe: die Datei _clean.json

Die Datei hat denselben Aufbau wie die `_raw.json`: Metadaten, dann die Meldungen. Beispiel mit erfundenem Inhalt:

```json
{
  "run_id": "2026-10-21_0800",
  "stage": "clean",
  "created": "2026-10-21T08:00:15Z",
  "status": "ok",
  "reason": null,
  "items": [
    {
      "id": "m001",
      "source": "feed_a",
      "title": "Brand in Beispielstadt",
      "teaser": "Die Feuerwehr spricht von einem \"glimpflichen Ausgang\".",
      "link": "https://example.org/meldung-1",
      "published": "2026-10-21T05:31:49Z"
    },
    {
      "id": "m002",
      "source": "feed_b",
      "title": "Neue Brücke freigegeben",
      "teaser": null,
      "link": "https://example.org/meldung-2",
      "published": null
    }
  ]
}
```

Ein fehlender Teaser bleibt `null`. Die Anführungszeichen erscheinen in der Datei als `\"`, das ist JSON-Schreibweise und verschwindet beim Einlesen.

## Aufbau des Moduls

Das Modul `src/clean.py` trennt die Regeln voneinander. Jede Regel ist eine eigene kleine Funktion und dadurch einzeln testbar.

| Funktion | Aufgabe |
|---|---|
| `load_raw` | liest die Rohdatei und gibt sie als Dictionary zurück |
| `remove_html` | ersetzt HTML-Tags durch ein Leerzeichen, wandelt Entities um |
| `unify_quotes` | vereinheitlicht typografische Anführungszeichen |
| `unify_hyphens` | vereinheitlicht Sonderbindestriche |
| `remove_repeated_symbols` | entfernt Folgen gleicher Symbole wie `+++` |
| `tidy_whitespace` | fasst Leerräume zusammen und entfernt sie an den Enden |
| `clean_text` | wendet alle Regeln in fester Reihenfolge an |
| `clean_item` | putzt Titel und Teaser einer Meldung |
| `save_clean` | schreibt die Datei mit Metadaten |
| `clean` | führt den Ablauf der Stufe und meldet das Ergebnis an `run.py` |

## Reihenfolge der Regeln

Die Regeln laufen in fester Reihenfolge. Grundsatz: Erst Zeichen entfernen oder ersetzen, zum Schluss die Leerräume aufräumen.

Beispiel: Aus `+++ Brand in Beispielstadt +++ ` entsteht beim Entfernen der Symbole `" Brand in Beispielstadt "`. Die Leerzeichen, die neben den Symbolen standen, bleiben übrig. Erst die letzte Regel macht daraus `Brand in Beispielstadt`. Würde man die Leerräume zuerst aufräumen, blieben sie am Ende stehen.

Auch innerhalb einer Regel zählt die Reihenfolge. HTML-Tags werden vor den Entities behandelt. Andersherum würde aus dem Text `&lt;b&gt;` ein Tag entstehen und gelöscht, obwohl er als Text gemeint war.

## Fehlerbehandlung

| Fall | Verhalten |
|---|---|
| Meldung ohne Teaser oder Titel | Feld bleibt `null`, die Meldung bleibt erhalten |
| alle Teaser fehlen | Status `ok`; über die Brauchbarkeit urteilt die Auswahl, nicht clean |
| Rohdatei fehlt oder ist kein gültiges JSON | Status `abort` mit Grund, Datei mit leerer Liste |
| Rohdatei ohne Meldungen | Status `abort` mit Grund, Datei mit leerer Liste |

Ein Abbruch ist bei clean nur aus technischen Gründen vorgesehen. Im Normalbetrieb kommt eine Rohdatei ohne Meldungen gar nicht an, weil fetch dann selbst abbricht. Die Prüfung sichert einen Start von Hand ab. Auch beim Abbruch wird eine Datei geschrieben, damit der Abbruch eine Spur mit Grund hinterlässt.

## Design-Entscheidungen

**Vereinheitlichen statt löschen.** Anführungszeichen zeigen, dass etwas ein Zitat ist und keine Tatsachenbehauptung. Diese Information soll erhalten bleiben. Ein gelöschter Bindestrich würde zwei Wörter verbinden, aus `KI-Strategie` würde `KIStrategie`. Einheitliche Zeichen machen gleiche Meldungen außerdem vergleichbar.

**Ein fehlender Wert bleibt fehlend.** `clean_text` gibt für einen fehlenden Text sofort wieder einen fehlenden Wert zurück. Ohne diese Prüfung bräche die erste Regel bei der ersten Meldung ohne Teaser ab.

**Kopie statt Veränderung.** `clean_item` arbeitet mit einer Kopie der Meldung. Die eingelesenen Rohdaten bleiben unverändert.

**Nur bauen, was in echten Daten vorkommt.** Regeln für URL-Parameter, Werbezeilen oder Grenzfälle wie `...` kommen erst hinzu, wenn sie in den Feeds tatsächlich auftauchen.

## Tests

Getestet wird wie bei fetch ohne Internetzugriff und mit festen, selbst gewählten Eingaben. Die Erwartung steht immer als fester Wert im Test.

Die fünf Regeln sowie `clean_text` und `clean_item` bekommen einen kurzen Text und geben einen kurzen Text zurück. Sie werden mit `doctest` direkt im Docstring getestet, insgesamt sieben doctests. Die Funktionen mit Dateien und der Gesamtablauf werden mit `pytest` in einem temporären Ordner getestet.

| Funktion | geprüft wird |
|---|---|
| jede Regel | typischer Fall, bei `remove_repeated_symbols` auch ein einzelnes Symbol, das stehen bleibt |
| `clean_text` | Reihenfolge am Beispiel `+++`, fehlender Text |
| `load_raw` | Rückgabe als Dictionary |
| `save_clean` | Datei existiert, Metadaten, Meldungen unverändert, Umlaute im Klartext |
| `clean` | Text geputzt, Anzahl der Meldungen gleich, andere Felder unverändert, fehlender Teaser bleibt fehlend, Rohdatei fehlt, Rohdatei ohne Meldungen |

Stand: 22 Tests für fetch und clean zusammen, alle bestanden, Laufzeit etwa 0,3 Sekunden.

## Bekannte Grenzen

Beim Durchgehen jeder Regel sind einige Grenzfälle aufgefallen. Sie sind bewusst noch nicht gelöst, weil sie in den echten Daten bisher nicht vorkamen.

- Die Regel für wiederholte Symbole trifft auch Namen wie `C++`, daraus würde `C`.
- Eine Folge wie `==>` verliert nur `==`, das `>` bleibt stehen.
- Besteht ein Titel nur aus Symbolen, wird er zu einem leeren Text statt zu einem fehlenden Wert.
- Vergleichszeichen mit Text dazwischen, etwa `a < b > c`, sehen für die HTML-Regel wie ein Tag aus.

Jeder dieser Fälle wird zu einem Test, sobald er in echten Daten auftaucht.

## Stand und nächste Schritte

Die Stufe clean liefert aus der `_raw.json` eine `_clean.json` mit gleicher Anzahl Meldungen und einheitlich gesäubertem Text. Alle Funktionen sind automatisch getestet.

Als Nächstes folgt die Stufe `normalize`. Sie macht den Text vorlesbar: Zahlen runden nach einer festen Liste erlaubter Fälle, alle Zahlen ausschreiben, Zeichen und Abkürzungen ersetzen, Namen über ein Aussprache-Lexikon. Geprüft wird sie gegen einen festen Testsatz.
