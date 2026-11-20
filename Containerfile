# Axon OS: a Bazzite-based bootc image.
#
# One Containerfile builds every variant. The workflow (and the Justfile)
# pass BASE_IMAGE, IMAGE_NAME and GPU_VENDOR; see variants.json.

ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-nvidia-open:stable

FROM scratch AS ctx
COPY build_files /build_files
COPY system_files /system_files
COPY keys /keys

FROM ${BASE_IMAGE}

ARG BASE_IMAGE
ARG IMAGE_NAME=axon-os-nvidia
ARG IMAGE_VENDOR=kaorii-ako
ARG IMAGE_TAG=stable
ARG GPU_VENDOR=nvidia
ARG DESKTOP=kde
ARG VERSION=dev

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=cache,dst=/var/cache \
    --mount=type=cache,dst=/var/log \
    --mount=type=tmpfs,dst=/tmp \
    BASE_IMAGE="${BASE_IMAGE}" \
    IMAGE_NAME="${IMAGE_NAME}" \
    IMAGE_VENDOR="${IMAGE_VENDOR}" \
    IMAGE_TAG="${IMAGE_TAG}" \
    GPU_VENDOR="${GPU_VENDOR}" \
    DESKTOP="${DESKTOP}" \
    VERSION="${VERSION}" \
    bash /ctx/build_files/build.sh

RUN bootc container lint
