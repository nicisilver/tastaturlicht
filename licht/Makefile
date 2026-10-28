# Makefile – Bau-Anleitung für den Licht-Treiber
obj-m += pink_tastatur.o

KDIR := /lib/modules/$(shell uname -r)/build
MOK  := /var/lib/shim-signed/mok

# "make" -> Treiber bauen
all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

# "make sign" -> Treiber mit meinem Schlüssel unterschreiben (braucht sudo)
sign:
	sudo kmodsign sha512 $(MOK)/MOK.priv $(MOK)/MOK.der pink_tastatur.ko

# "make clean" -> aufräumen
clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
