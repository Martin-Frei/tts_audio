# tts_audio: Stufe select_items

Stand: 26.10.2026, Phase 1 lauffähig.

## Zweck der Stufe select_items

Drei Nachrichtenfeeds liefern über hundert Meldungen. Vorgelesen wären das rund zwanzig Minuten. Die Stufe select_items wählt deshalb aus: die neuesten brauchbaren Meldungen, in der Pipeline derzeit zwanzig. Die Zahl steht im Profil, nicht im Code.

Die Stufe entscheidet nur, **welche** und **wie viele** Meldungen gesprochen werden. Sie verändert keinen Text.

## Was als brauchbar gilt

Eine Regel ist bisher eingebaut, aus einer Beobachtung beim Hören: **Eine Frage ohne Teaser ist keine Nachricht.** Eine Schlagzeile, die etwas aussagt, funktioniert auch allein. Eine Schlagzeile, die nur eine Frage stellt, lässt den Hörer ohne Antwort zurück.

Aussortiert wird vor dem Abzählen. Fällt eine Meldung heraus, rückt die nächste nach, und alle Plätze bleiben besetzt.

## Sortieren ohne Datumslogik

Sortiert wird nach Veröffentlichungszeit, die neueste zuerst. Weil alle Zeiten seit der ersten Stufe einheitlich in UTC und als ISO-Text gespeichert sind, etwa `2026-10-26T09:00:00Z`, ergibt die einfache Textsortierung bereits die richtige zeitliche Reihenfolge. Eine Entscheidung vom ersten Tag zahlt sich hier aus.

Meldungen ohne Zeitangabe kommen ans Ende.

## Erkenntnisse aus dem Bau

**Wo eine Stufe sitzt, ist eine Abwägung.** Früh auswählen spart Arbeit, weil spätere Stufen weniger Meldungen verarbeiten. Spät auswählen heißt, das fertig vorbereitete Stück zu sehen. Gewählt wurde die späte Position, mit dem Vermerk, sie neu zu prüfen, sobald eine spätere Stufe Meldungen streichen kann. Weil die Reihenfolge der Stufen in einer Konfigurationsdatei steht, ist das eine Zeile.

**Namen können kollidieren.** Die Stufe sollte zuerst `select` heißen, genau wie ein eingebautes Python-Modul. Solche Konflikte zeigen sich oft erst später und sind schwer zu finden.

**Die echten Daten zeigen, was fehlt.** Im ersten Lauf standen zwei Fassungen derselben Meldung unter den zwanzig. Das bestätigt die geplante Dubletten-Erkennung, und zwar vor der Auswahl.
