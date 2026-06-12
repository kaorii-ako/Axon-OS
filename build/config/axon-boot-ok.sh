#!/bin/bash
# Axon OS — boot watchdog "all clear". Runs once the boot reaches the
# display manager and resets the GRUB boot-attempt counter on the ESP.
set -u

ENV_FILE=/boot/efi/axon/grubenv

# Live sessions / ext4 installs have no mounted ESP — nothing to do.
findmnt /boot/efi >/dev/null 2>&1 || exit 0
command -v grub-editenv >/dev/null 2>&1 || exit 0

mkdir -p /boot/efi/axon
[ -f "${ENV_FILE}" ] || grub-editenv "${ENV_FILE}" create
grub-editenv "${ENV_FILE}" set boot_attempts=0

# Surface a recovery notice when this boot came from the rollback snapshot.
if grep -q 'axon\.rollback=1' /proc/cmdline; then
    mkdir -p /var/lib/axon
    date +%s > /var/lib/axon/last-rollback
    echo "Axon OS booted from the factory rollback snapshot." \
        > /etc/motd.d/axon-rollback 2>/dev/null || true
fi
exit 0
