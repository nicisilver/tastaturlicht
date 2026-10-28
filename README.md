# 💜 Tastaturlicht für MECHREVO Jiaolong

Ein selbstgeschriebener Linux-Treiber, mit dem die **RGB-Tastaturbeleuchtung** vom
**MECHREVO Jiaolong** (Mainboard `X6xR55xK`) unter Linux die Farbe wechseln kann.
Mit Farb-Programm und Knopf im GNOME-Schnellmenü. 🌈

> Gebaut an einem Abend, um die Tastatur endlich **pink** zu machen.
> Am Ende ist es dann doch **lila** geworden. 💜

## ✨ Was dabei ist

| Teil | Ordner | Was es macht |
|---|---|---|
| 🐧 **Treiber** | `licht/` | Redet über die Uniwill-WMI-Schnittstelle mit dem Embedded Controller und legt `/sys/class/leds/pink_tastatur::kbd_backlight/` an |
| 🔁 **DKMS** | `dkms/` | Baut den Treiber bei jedem Linux-Update automatisch neu und lädt ihn beim Start |
| 🔓 **udev-Regel** | `regeln/` | Mitglieder der Gruppe `tastaturlicht` dürfen die Farbe ohne Passwort ändern |
| 🎨 **Farb-Programm** | `app/` | Fenster mit Farbwähler, Helligkeit und Lieblingsfarben (Python + GTK4/libadwaita) |
| ⚡ **Schnellmenü** | `erweiterung/` | GNOME-Erweiterung: an/aus, Farbpunkte und Helligkeit oben rechts |

## ⚠️ Passt das zu meinem Laptop?

Nur, wenn **beides** stimmt:

```bash
cat /sys/class/dmi/id/board_vendor /sys/class/dmi/id/board_name
```
→ muss **`MECHREVO`** und etwas mit **`X6xR55xK`** zeigen.

Außerdem getestet mit: **Ubuntu 26.04**, **Linux 7.0**, **GNOME 50**, **Secure Boot an**.

Der Treiber prüft das selbst und **verweigert** auf anderen Laptops den Start,
weil die Register dort etwas ganz anderes bedeuten könnten (z. B. Lüfter oder Akku!).

## 📦 Installieren

```bash
git clone <LINK-ZU-DIESEM-PROJEKT> tastaturlicht
cd tastaturlicht
./installieren.sh
```

Das Skript fragt nach deinem Passwort und erledigt alles.
**Bei Secure Boot** wird beim ersten Mal ein eigener Schlüssel angelegt.
Dann musst du **neu starten** und im **blauen Bildschirm** bestätigen:

1. `Press any key` → schnell eine Taste drücken
2. **Enroll MOK** → **Continue** → **Yes**
3. Das Einmal-Passwort eingeben (⚠️ amerikanische Tastatur: Y und Z sind vertauscht!)
4. **Reboot**

Danach **einmal ab- und wieder anmelden** und:
```bash
gnome-extensions enable tastaturlicht@nes
```

## 🌈 Benutzen

- **App „Tastaturlicht“** im App-Menü
- **Schnellmenü** oben rechts → Knopf **„Tastatur“**
- Oder ganz direkt (Farbe je 0–50, Helligkeit 0–4):
  ```bash
  echo "30 0 50" > /sys/class/leds/pink_tastatur::kbd_backlight/multi_intensity
  echo 4 > /sys/class/leds/pink_tastatur::kbd_backlight/brightness
  ```
  Die Farbe wird erst übernommen, wenn danach `brightness` geschrieben wird.

## 🗑️ Entfernen

```bash
./deinstallieren.sh
```

## 🔍 Wie es funktioniert (Kurzfassung)

- Die Tastatur hängt am **Embedded Controller (EC)** eines Uniwill-Barebones.
- Erreichbar über die WMI-Methode `WMBC` (GUID `ABBC0F6F-8EA1-11D1-00A0-C90629100000`),
  Funktion 4, mit einem 40-Byte-Päckchen: Adresse (2 Bytes), Wert, Byte 5 = 0 schreiben / 1 lesen.
- Register: `0x0769`/`0x076A`/`0x076B` = Rot/Grün/Blau (je **0–50**),
  `0x0767` Bit `0x20` = Farbe übernehmen, `0x078C` Bits 5–7 = Helligkeit (0–4), Bit `0x10` = übernehmen.
- Die Register-Adressen stammen aus den [tuxedo-drivers](https://gitlab.com/tuxedocomputers/development/packages/tuxedo-drivers)
  (gleiche Uniwill-Technik) und wurden auf diesem Laptop durch Auslesen bestätigt.
- Ab **Linux 7.3** soll der offizielle Treiber `uniwill-laptop` das auch können.
  Dann wird dieses Projekt vermutlich überflüssig. 🎉

## ⚖️ Lizenz & Haftung

GPL-2.0, siehe [LICENSE](LICENSE).
Benutzung auf eigene Gefahr: Der Treiber schreibt in den Embedded Controller.
Er ist vorsichtig gebaut, aber nur auf einem Laptop getestet. 💜
