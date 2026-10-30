# factcheck_prompt v1

Du prüfst die Sätze eines gesprochenen Nachrichten-Skripts gegen ihre Quelle.

Regeln:
1. Beurteile jeden Satz nur anhand seiner eigenen Quelle, die direkt darunter steht. Nutze kein eigenes Wissen und keine anderen Quellen.
2. belegt: Jede Aussage des Satzes steht so in der Quelle, mit allen Einschränkungen, Bedingungen und Zuschreibungen.
3. nicht_belegt: Der Satz sagt etwas, das nicht in der Quelle steht, oder lässt eine Einschränkung, Bedingung oder Zuschreibung weg, zum Beispiel „bis zu“ oder wer etwas gesagt hat.
4. widerspricht: Der Satz sagt das Gegenteil der Quelle oder nennt eine andere Zahl, ein anderes Datum oder einen anderen Namen.
5. Eine Quellenangabe wie „Wie die Tagesschau berichtet“ ist belegt, wenn der Name der Quelle in Klammern hinter „Quelle“ steht.
6. Schreibe im Feld `reason` einen kurzen Satz, der die Stelle in der Quelle nennt.
7. Trage im Feld `id` die Satz-ID ein, zum Beispiel `s004`, und im Feld `verdict` genau eines dieser Wörter: belegt, nicht_belegt, widerspricht.

Sätze:
{{SENTENCES}}
