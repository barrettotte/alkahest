# Pin the upstream image by manifest digest so a reused Quarto tag cannot change
# the base filesystem beneath this publishing toolchain.
FROM ghcr.io/quarto-dev/quarto-full:1.10.18@sha256:280aa58ecdb814dcced42066e4f64d1825020ce5822f2ca2749fc6396020d7de

# Keep every network-resolved bootstrap input visible in one place. These are
# intentionally ENV values, not build arguments: all developers and CI use the
# same source identities and the report command can inspect them at runtime.
ENV ALKAHEST_UBUNTU_SNAPSHOT="https://snapshot.ubuntu.com/ubuntu/20260816T000000Z" \
    ALKAHEST_CHROME_ARCHIVE_URL="https://storage.googleapis.com/chrome-for-testing-public/152.0.7977.42/linux64/chrome-headless-shell-linux64.zip" \
    ALKAHEST_CHROME_ARCHIVE_SHA256="129686a270d84ac4637c614802c554634aa827aa13214216f81e0a0b9410f8cf" \
    ALKAHEST_EPUBCHECK_ARCHIVE_URL="https://github.com/w3c/epubcheck/releases/download/v5.3.0/epubcheck-5.3.0.zip" \
    ALKAHEST_EPUBCHECK_ARCHIVE_SHA256="6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5" \
    ALKAHEST_TEXLIVE_REPOSITORY="https://texlive.info/tlnet-archive/2026/08/16/tlnet" \
    ALKAHEST_TEXLIVE_TLPDB_SHA256="a1b87eb64a6ffd2076f6bfc872e9ea0aa1e56ba7fe585636eed18a388d4adf8e"

USER root

# Runtime libraries required by Chrome Headless Shell plus the Java and Poppler
# validation tools. The upstream `quarto-full` image contains TeX but not these
# stacks. Resolve them from an immutable Ubuntu archive view and pin each direct
# dependency so local and CI checks use identical parser versions.
RUN sed -i \
        -e "s|http://archive.ubuntu.com/ubuntu/|${ALKAHEST_UBUNTU_SNAPSHOT}/|g" \
        -e "s|http://security.ubuntu.com/ubuntu/|${ALKAHEST_UBUNTU_SNAPSHOT}/|g" \
        /etc/apt/sources.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        libasound2=1.2.2-2.1ubuntu2.5 \
        libatk-bridge2.0-0=2.34.2-0ubuntu2~20.04.1 \
        libatk1.0-0=2.35.1-1ubuntu2 \
        libatspi2.0-0=2.36.0-2 \
        libcairo2=1.16.0-4ubuntu1 \
        libcups2=2.3.1-9ubuntu1.9 \
        libdbus-1-3=1.12.16-2ubuntu2.3 \
        libdrm2=2.4.107-8ubuntu1~20.04.2 \
        libgbm1=21.2.6-0ubuntu0.1~20.04.2 \
        libglib2.0-0=2.64.6-1~ubuntu20.04.9 \
        libnspr4=2:4.35-0ubuntu0.20.04.1 \
        libnss3=2:3.98-0ubuntu0.20.04.2 \
        libpango-1.0-0=1.44.7-2ubuntu4 \
        libx11-6=2:1.6.9-2ubuntu1.6 \
        libxcb1=1.14-2 \
        libxcomposite1=1:0.4.5-1 \
        libxdamage1=1:1.1.5-2 \
        libxext6=2:1.3.4-0ubuntu1 \
        libxfixes3=1:5.0.3-2 \
        libxkbcommon0=0.10.0-1 \
        libxrandr2=2:1.5.2-0ubuntu1 \
        openjdk-11-jre-headless=11.0.27+6~us1-0ubuntu1~20.04 \
        poppler-utils=0.86.1-0ubuntu1.7 \
    && rm -rf /var/lib/apt/lists/*

# Quarto's diagram renderer needs a browser for non-HTML targets. Install the
# exact Chrome for Testing archive directly; both the archive and installed
# executable are checked so resolver drift and extraction drift fail loudly.
RUN test "$(dpkg --print-architecture)" = "amd64" \
    && curl --fail --location --silent --show-error \
        --output /tmp/chrome-headless-shell-linux64.zip \
        "${ALKAHEST_CHROME_ARCHIVE_URL}" \
    && echo "${ALKAHEST_CHROME_ARCHIVE_SHA256}  /tmp/chrome-headless-shell-linux64.zip" \
        | sha256sum --check \
    && unzip -q /tmp/chrome-headless-shell-linux64.zip -d /tmp/chrome-headless-shell \
    && mkdir -p /opt/chrome-headless-shell \
    && cp -a /tmp/chrome-headless-shell/chrome-headless-shell-linux64/. /opt/chrome-headless-shell/ \
    && chmod -R a+rX /opt/chrome-headless-shell \
    && rm -rf \
        /tmp/chrome-headless-shell \
        /tmp/chrome-headless-shell-linux64.zip

RUN echo "7e0227229e5d5d6050a743ec8c2954b2e7b90e84d73c6796ab6ae61a0dde9bce  /opt/chrome-headless-shell/chrome-headless-shell" \
    | sha256sum --check

ENV QUARTO_CHROMIUM=/opt/chrome-headless-shell/chrome-headless-shell

# Use the W3C EPUB conformance checker rather than maintaining a partial local
# interpretation of the EPUB specification. Verify both its distribution and
# executable JAR identities.
RUN curl --fail --location --silent --show-error \
        --output /tmp/epubcheck-5.3.0.zip \
        "${ALKAHEST_EPUBCHECK_ARCHIVE_URL}" \
    && echo "${ALKAHEST_EPUBCHECK_ARCHIVE_SHA256}  /tmp/epubcheck-5.3.0.zip" \
        | sha256sum --check \
    && unzip -q /tmp/epubcheck-5.3.0.zip -d /opt \
    && mv /opt/epubcheck-5.3.0 /opt/epubcheck \
    && rm /tmp/epubcheck-5.3.0.zip \
    && echo "f7f96617c929371821609b88c8484d6dc9f24fe916499863c46094c5fb778a65  /opt/epubcheck/epubcheck.jar" \
        | sha256sum --check \
    && java -jar /opt/epubcheck/epubcheck.jar --version

ENV EPUBCHECK_JAR=/opt/epubcheck/epubcheck.jar

# Normal renders have no network access. Verify and select a dated TeX Live
# repository, then declare packages here instead of letting Quarto discover
# and download them while compiling a manuscript.
RUN curl --fail --location --silent --show-error \
        --output /tmp/texlive.tlpdb.xz \
        "${ALKAHEST_TEXLIVE_REPOSITORY}/tlpkg/texlive.tlpdb.xz" \
    && echo "${ALKAHEST_TEXLIVE_TLPDB_SHA256}  /tmp/texlive.tlpdb.xz" \
        | sha256sum --check \
    && rm /tmp/texlive.tlpdb.xz \
    && tlmgr option repository "${ALKAHEST_TEXLIVE_REPOSITORY}" \
    && tlmgr update --self

# Keep manuscript-required packages in a separate layer. Adding one package
# does not invalidate the larger operating-system and browser installation.
RUN tlmgr install \
        babel-english \
        caption \
        koma-script

# Assert package revisions and exact font bytes used by the current specimen so
# a bad archive or lock update cannot silently change the typography.
RUN set -eu; \
    check_revision() { \
        actual="$(tlmgr info --only-installed "$1" | sed -n 's/^revision:[[:space:]]*//p')"; \
        test "${actual}" = "$2"; \
    }; \
    check_revision babel-english 77682; \
    check_revision caption 79618; \
    check_revision koma-script 77575; \
    check_revision lm 77682; \
    check_revision lm-math 67718; \
    echo "8c8b4894c328236143c9f57f690e2199482e0a4bed2567747e99ffbbf84ca3af  /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf" | sha256sum --check; \
    echo "cdad31bd653b7e7f14cc0671de5c05ec91661f2fa8ba9d4ed3c2c511c6a3ed03  /usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" | sha256sum --check; \
    echo "1aa18cfefa58132c52ce5de70db1fd1154201c19cd2b2cdaffba4906a33e6852  /opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-regular.otf" | sha256sum --check; \
    echo "102fe06c430a8b681b2bf6876b7cd967ae4d47b4b6b41d915eb7913b726d9fb1  /opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-bold.otf" | sha256sum --check; \
    echo "c1fce25075567bb8dbf2151658c3b442690041db17a2d49fc9e55905ea5b7169  /opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-italic.otf" | sha256sum --check; \
    echo "2f4ae1bd30d4203a1c74c61d61dddbd5e2c2d5a7001d456b1b98e08b7c47ffb9  /opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmmonolt10-bold.otf" | sha256sum --check; \
    echo "6075562b771f8b82f0c179e363389684f2dd09de30038269e2628e504bd7be0f  /opt/TinyTeX/texmf-dist/fonts/opentype/public/lm-math/latinmodern-math.otf" | sha256sum --check

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

# Rendering and validation run unprivileged even when the caller invokes the
# image directly instead of using the repository wrappers.
USER 10001:10001
