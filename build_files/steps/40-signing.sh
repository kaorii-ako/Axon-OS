#!/usr/bin/env bash
set -euo pipefail

KEY_SRC=/ctx/keys/cosign.pub
if [[ ! -s "${KEY_SRC}" ]]; then
  echo "::warning::keys/cosign.pub not committed; the image will not enforce signatures on updates"
  exit 0
fi

REGISTRY_SCOPE="ghcr.io/${IMAGE_VENDOR}"
KEY_DST="/etc/pki/containers/${IMAGE_VENDOR}-axon.pub"

install -Dm0644 "${KEY_SRC}" "${KEY_DST}"

POLICY=/etc/containers/policy.json
[[ -f "${POLICY}" ]] || echo '{"default":[{"type":"insecureAcceptAnything"}],"transports":{"docker":{}}}' > "${POLICY}"

TMP="$(mktemp)"
jq --arg scope "${REGISTRY_SCOPE}" --arg key "${KEY_DST}" \
  '.transports.docker[$scope] = [{
     "type": "sigstoreSigned",
     "keyPath": $key,
     "signedIdentity": {"type": "matchRepository"}
   }]' "${POLICY}" > "${TMP}"
install -m0644 "${TMP}" "${POLICY}"
rm -f "${TMP}"

install -d /etc/containers/registries.d
cat > "/etc/containers/registries.d/${IMAGE_VENDOR}-axon.yaml" <<EOF
docker:
  ${REGISTRY_SCOPE}:
    use-sigstore-attachments: true
EOF

jq -e --arg scope "${REGISTRY_SCOPE}" '.transports.docker[$scope][0].type == "sigstoreSigned"' "${POLICY}" >/dev/null
echo "Signature policy installed for ${REGISTRY_SCOPE}"
