#!/usr/bin/env bash
# installieren.sh – Tastaturlicht für MECHREVO Jiaolong (X6xR55xK) installieren 💜
#
# Als normaler Benutzer ausführen (NICHT mit sudo davor):
#   ./installieren.sh
# Das Skript fragt selbst nach dem Passwort, wenn es Chef-Rechte braucht.

set -euo pipefail

VERSION="1.0"
HIER="$(cd "$(dirname "$0")" && pwd)"
MOK=/var/lib/shim-signed/mok

hinweis() { printf '\n\e[38;2;203;166;247m♡ %s\e[0m\n' "$*"; }
fehler()  { printf '\n\e[38;2;243;139;168m✗ %s\e[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || fehler "Bitte ohne sudo starten: ./installieren.sh"

# --- 1. Passt der Laptop? ---
BOARD="$(cat /sys/class/dmi/id/board_vendor 2>/dev/null) $(cat /sys/class/dmi/id/board_name 2>/dev/null)"
if [[ "$BOARD" != *MECHREVO*X6xR55xK* ]]; then
	printf 'Dein Mainboard: %s\n' "$BOARD"
	fehler "Der Treiber ist nur für MECHREVO Jiaolong (X6xR55xK) gebaut und lädt auf anderen Laptops nicht."
fi

# --- 2. Werkzeuge ---
hinweis "Installiere Bau-Werkzeuge (dkms, Kernel-Header) …"
sudo apt-get install -y dkms build-essential "linux-headers-$(uname -r)"

# --- 3. Secure-Boot-Schlüssel ---
NEUSTART_NOETIG=0
if mokutil --sb-state 2>/dev/null | grep -q enabled; then
	if [ ! -f "$MOK/MOK.der" ]; then
		hinweis "Erstelle deinen eigenen Secure-Boot-Schlüssel …"
		sudo update-secureboot-policy --new-key
	fi
	if ! mokutil --test-key "$MOK/MOK.der" 2>/dev/null | grep -q "already enrolled"; then
		hinweis "Melde den Schlüssel an. Wähle ein Einmal-Passwort (nur Kleinbuchstaben ohne y/z + Zahlen!):"
		sudo mokutil --import "$MOK/MOK.der" || true
		NEUSTART_NOETIG=1
	fi
fi

# --- 4. Treiber über DKMS ---
hinweis "Baue und installiere den Treiber mit DKMS …"
sudo mkdir -p "/usr/src/pink_tastatur-$VERSION"
sudo cp "$HIER/licht/pink_tastatur.c" "$HIER/licht/Makefile" "$HIER/dkms/dkms.conf" "/usr/src/pink_tastatur-$VERSION/"
if ! dkms status "pink_tastatur/$VERSION" 2>/dev/null | grep -q pink_tastatur; then
	sudo dkms add "pink_tastatur/$VERSION"
fi
sudo dkms install "pink_tastatur/$VERSION" -k "$(uname -r)" --force
sudo cp "$HIER/dkms/pink_tastatur.conf" /etc/modules-load.d/

# --- 5. Erlaubnis: Gruppe + udev-Regel ---
hinweis "Richte die Erlaubnis ein (Gruppe 'tastaturlicht') …"
sudo groupadd -f tastaturlicht
sudo usermod -aG tastaturlicht "$USER"
sudo cp "$HIER/regeln/99-pink-tastatur.rules" /etc/udev/rules.d/
sudo udevadm control --reload

# --- 6. Farb-Programm ---
hinweis "Installiere das Farb-Programm …"
sudo install -Dm755 "$HIER/app/tastaturlicht.py" /usr/local/bin/tastaturlicht
sudo install -Dm644 "$HIER/app/tastaturlicht.desktop" /usr/local/share/applications/tastaturlicht.desktop
sudo install -Dm644 "$HIER/app/tastaturlicht.svg" /usr/local/share/icons/hicolor/scalable/apps/tastaturlicht.svg

# --- 7. Schnellmenü-Erweiterung (nur für dich) ---
hinweis "Installiere die Schnellmenü-Erweiterung …"
mkdir -p ~/.local/share/gnome-shell/extensions
cp -r "$HIER/erweiterung/tastaturlicht@nes" ~/.local/share/gnome-shell/extensions/

# --- 8. Jetzt schon laden? ---
if [ "$NEUSTART_NOETIG" -eq 0 ]; then
	sudo modprobe -r pink_tastatur 2>/dev/null || true
	sudo modprobe pink_tastatur && hinweis "Treiber läuft! 💜"
fi

# --- Fertig ---
hinweis "Fertig! Was jetzt noch fehlt:"
if [ "$NEUSTART_NOETIG" -eq 1 ]; then
	cat <<-EOF
	  1. NEU STARTEN. Im blauen Bildschirm: Enroll MOK → Continue → Yes → Passwort → Reboot
	  2. Nach dem Start im Terminal:  gnome-extensions enable tastaturlicht@nes
	EOF
else
	cat <<-EOF
	  1. Einmal ABMELDEN und wieder anmelden (für die Gruppe und die Erweiterung)
	  2. Dann im Terminal:  gnome-extensions enable tastaturlicht@nes
	EOF
fi
echo "  Danach: App 'Tastaturlicht' oder Schnellmenü oben rechts → 'Tastatur' 🌈"
