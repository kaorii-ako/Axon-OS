#!/usr/bin/env bash
set -euo pipefail

for repo in /etc/yum.repos.d/_copr*axon*.repo; do
  [[ -f "${repo}" ]] && sed -i 's/^enabled=1/enabled=0/' "${repo}"
done

rm -rf /var/tmp/* 2>/dev/null || true

echo "Axon OS ${VERSION} (${IMAGE_NAME}) built on ${BASE_IMAGE}"
