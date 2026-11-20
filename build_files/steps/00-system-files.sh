#!/usr/bin/env bash
set -euo pipefail

cp -a /ctx/system_files/. /

chmod 0755 /usr/bin/axon-gpu-doctor /usr/libexec/axon/*
