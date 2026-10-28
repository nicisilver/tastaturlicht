#!/usr/bin/env bash
# deinstallieren.sh – Tastaturlicht wieder entfernen
# Die Tastaturfarbe bleibt im Chip, wie sie zuletzt war.

set -uo pipefail

VERSION="1.0"

[ "$(id -u)" -ne 0 ] || { echo "Bitte ohne sudo starten: ./deinstallieren.sh" >&2; exit 1; }

gnome-extensions disable tastaturlicht@nes 2>/dev/null
rm -rf ~/.local/share/gnome-shell/extensions/tastaturlicht@nes

sudo modprobe -r pink_tastatur 2>/dev/null
sudo dkms remove "pink_tastatur/$VERSION" --all 2>/dev/null
sudo rm -rf "/usr/src/pink_tastatur-$VERSION"
sudo rm -f /etc/modules-load.d/pink_tastatur.conf
sudo rm -f /etc/udev/rules.d/99-pink-tastatur.rules
sudo udevadm control --reload
sudo rm -f /usr/local/bin/tastaturlicht \
           /usr/local/share/applications/tastaturlicht.desktop \
           /usr/local/share/icons/hicolor/scalable/apps/tastaturlicht.svg

echo "♡ Tastaturlicht wurde entfernt. Die Gruppe 'tastaturlicht' bleibt (stört nicht)."
