#!/bin/sh
# Rassegna "Oggi in Italia": scarica da GitHub le pagine del giorno e le mette nel sito.
# Uso: sh rassegna.sh /percorso/della/cartella/del/sito
# Sicuro da lanciare piu' volte: se la rassegna del giorno non e' ancora pronta non tocca nulla,
# se e' gia' stata pubblicata esce senza scrivere niente.
DEST="$1"; [ -z "$DEST" ] && { echo "indica la cartella del sito"; exit 1; }
[ -d "$DEST" ] || { echo "cartella non trovata: $DEST"; exit 1; }
RAW="https://raw.githubusercontent.com/maxser1/ite-oggi/main"
D=$(TZ=Europe/Rome date +%F)
FILES="it/oggi/$D.html today/$D.html de/heute/$D.html it/oggi/index.html today/index.html de/heute/index.html oggi/ultima.json"
LOG="$(dirname "$0")/rassegna.log"
ORA=$(TZ=Europe/Rome date '+%Y-%m-%d %H:%M')
# gia' pubblicata oggi? (il file del giorno c'e' e l'indice lo cita)
if [ -f "$DEST/it/oggi/$D.html" ] && grep -q "$D" "$DEST/oggi/ultima.json" 2>/dev/null; then exit 0; fi
TMP=$(mktemp -d); ok=1
for f in $FILES; do
  mkdir -p "$TMP/$(dirname "$f")"
  curl -fsS -m 60 "$RAW/$f?$(date +%s)" -o "$TMP/$f" || { ok=0; echo "$ORA non ancora disponibile: $f" >> "$LOG"; break; }
done
if [ "$ok" = 1 ]; then
  for f in $FILES; do mkdir -p "$DEST/$(dirname "$f")"; cp "$TMP/$f" "$DEST/$f"; done
  echo "$ORA pubblicata la rassegna del $D" >> "$LOG"
fi
rm -rf "$TMP"
