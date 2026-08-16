FROM ghcr.io/quarto-dev/quarto-full:1.10.18@sha256:280aa58ecdb814dcced42066e4f64d1825020ce5822f2ca2749fc6396020d7de

USER root

# Runtime libraries required by Chrome Headless Shell. The upstream
# `quarto-full` image contains TeX but deliberately does not include a browser
# stack, so these remain part of our explicit publishing environment.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libcairo2 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libglib2.0-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-6 \
        libxcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Quarto's diagram renderer needs a browser for non-HTML targets. Install the
# Quarto-pinned Chrome Headless Shell, then place its complete distribution in
# a location readable by the rootless runtime user.
RUN quarto install chrome-headless-shell --no-prompt \
    && browser="$(find /root /opt/quarto -type f -name chrome-headless-shell -print -quit)" \
    && test -n "${browser}" \
    && mkdir -p /opt/chrome-headless-shell \
    && cp -a "$(dirname "${browser}")/." /opt/chrome-headless-shell/ \
    && chmod -R a+rX /opt/chrome-headless-shell

ENV QUARTO_CHROMIUM=/opt/chrome-headless-shell/chrome-headless-shell

# Normal renders have no network access. Declare TeX packages here instead of
# letting Quarto discover and download them while compiling a manuscript.
# Keep the manager update in its own layer so adding a package is inexpensive.
RUN tlmgr update --self
RUN tlmgr install \
        babel-english \
        caption \
        koma-script

# Provide a safe default identity for direct `podman run` use. The project
# wrapper overrides this with the invoking host UID/GID so bind-mounted build
# artifacts remain owned by the developer, but never asks the container to run
# as root.
RUN groupadd --gid 10001 alkahest \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --create-home \
        --shell /usr/sbin/nologin \
        alkahest \
    && install --directory --owner=10001 --group=10001 /workspace

ENV HOME=/home/alkahest
WORKDIR /workspace
USER 10001:10001
