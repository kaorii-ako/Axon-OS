#!/usr/bin/env bash
set -euo pipefail

mapfile -t WANTED < <(grep -vE '^\s*(#|$)' /ctx/build_files/packages.txt)

MISSING=()
for pkg in "${WANTED[@]}"; do
  rpm -q "${pkg}" >/dev/null 2>&1 || MISSING+=("${pkg}")
done

if ((${#MISSING[@]})); then
  dnf5 -y install --setopt=install_weak_deps=False "${MISSING[@]}"
else
  echo "All packages already present in the base image."
fi
