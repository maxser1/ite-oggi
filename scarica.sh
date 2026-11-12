#!/bin/sh
# Scarica la rassegna del giorno da GitHub e la mette nel sito. Da eseguire con cron alle 7 (ora italiana).
# Uso: sh scarica.sh /home/UTENTE/public_html
DEST="$1"; [ -z "$DEST" ] && { echo "indica la cartella del sito"; exit 1; }
RAW="https://raw.githubusercontent.com/maxser1/ite-oggi/main"
D=$(TZ=Europe/Rome date +%F)
TMP=$(mktemp -d)
ok=1
for f in "it/oggi/$D.html" "today/$D.html" "de/heute/$D.html" "it/oggi/index.html" "today/index.html" "de/heute/index.html" "oggi/ultima.json"; do
  mkdir -p "$TMP/$(dirname "$f")"
  if curl -fsS -m 60 "$RAW/$f" -o "$TMP/$f"; then :; else ok=0; echo "non trovato: $f"; fi
done
if [ "$ok" = 1 ]; then
  for f in "it/oggi/$D.html" "today/$D.html" "de/heute/$D.html" "it/oggi/index.html" "today/index.html" "de/heute/index.html" "oggi/ultima.json"; do
    mkdir -p "$DEST/$(dirname "$f")"; cp "$TMP/$f" "$DEST/$f"
  done
  echo "rassegna del $D pubblicata"
else
  echo "rassegna del $D non completa: sito lasciato com'era"
fi
rm -rf "$TMP"
