#!/bin/bash
#
# Installe (ou retire) la collecte quotidienne de la cote d'Abidjan.
#
# Le gabarit porte des chemins absolus, que launchd exige et qui dépendent
# de l'endroit où le dépôt est cloné. Ce script les substitue, pour éviter
# d'avoir à éditer du XML à la main.
#
#   ./launchd/installer.sh            installe et démarre
#   ./launchd/installer.sh --retirer  désinstalle
#   ./launchd/installer.sh --etat     dit si la tâche tourne
#
set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ETIQUETTE="app.tayyib.collecte"
CIBLE="$HOME/Library/LaunchAgents/$ETIQUETTE.plist"
DOMAINE="gui/$(id -u)"

case "${1:-}" in
  --retirer)
    launchctl bootout "$DOMAINE/$ETIQUETTE" 2>/dev/null || true
    rm -f "$CIBLE"
    echo "Collecte quotidienne retirée."
    exit 0
    ;;
  --etat)
    if launchctl print "$DOMAINE/$ETIQUETTE" >/dev/null 2>&1; then
      echo "Installée. Prochaine collecte à 16 h 30."
      echo "Journal : $RACINE/cache/collecte.log"
    else
      echo "Non installée."
    fi
    exit 0
    ;;
esac

if [ ! -x "$RACINE/.venv/bin/python" ]; then
  echo "Environnement absent : lancez d'abord" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$RACINE/cache"
sed "s|__RACINE__|$RACINE|g" "$RACINE/launchd/$ETIQUETTE.plist" > "$CIBLE"

# `bootout` avant `bootstrap` : sans lui, une réinstallation échoue sur un
# service déjà chargé, et l'erreur ne dit pas laquelle des deux a raison.
launchctl bootout "$DOMAINE/$ETIQUETTE" 2>/dev/null || true
launchctl bootstrap "$DOMAINE" "$CIBLE"

echo "Collecte quotidienne installée — 16 h 30, et au démarrage de session."
echo "  journal   : $RACINE/cache/collecte.log"
echo "  état      : ./launchd/installer.sh --etat"
echo "  retirer   : ./launchd/installer.sh --retirer"
