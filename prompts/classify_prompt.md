

# classify_prompt v1

Du ordnest Nachrichtenmeldungen Rubriken zu.

Regeln:
1. Jede Meldung aus der Liste bekommt genau einen Eintrag. Lass keine weg und erfinde keine.
2. Prüfe die Rubriken in der angegebenen Reihenfolge. Die erste passende Rubrik gilt.
3. Entscheide nur nach Titel und Teaser, ohne eigenes Zusatzwissen.
4. Nenne im Feld `evidence` als Beleg ein bis drei einzelne Wörter, die wörtlich in Titel oder Teaser stehen. Forme sie nicht um.
5. Bewerte nicht, wie wichtig eine Meldung ist.
6. Trage im Feld `id` die Meldungs-ID ein, z. B. `m001`. Trage im Feld `category` genau eine Rubrik-ID aus der Liste ein, z. B. `sports`.

Rubriken in Prüfreihenfolge:
{{CATEGORIES}}

Meldungen:
{{ITEMS}}
