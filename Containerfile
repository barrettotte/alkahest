# Pin the upstream image by manifest digest so a reused Quarto tag cannot change
# the base filesystem beneath this publishing toolchain.
FROM ghcr.io/quarto-dev/quarto:1.10.18@sha256:3c10521544c4f182eb5edf3c807f99c5ddad93869b233052fa13cf7cdba13572

# Keep fixed network inputs and their archive checksums together. They are ENV
# values rather than build arguments so developers and CI cannot override them.
ENV ALKAHEST_UBUNTU_SNAPSHOT="https://snapshot.ubuntu.com/ubuntu/20260816T000000Z" \
    ALKAHEST_CHROME_ARCHIVE_URL="https://storage.googleapis.com/chrome-for-testing-public/152.0.7977.42/linux64/chrome-headless-shell-linux64.zip" \
    ALKAHEST_CHROME_ARCHIVE_SHA256="129686a270d84ac4637c614802c554634aa827aa13214216f81e0a0b9410f8cf" \
    ALKAHEST_EPUBCHECK_ARCHIVE_URL="https://github.com/w3c/epubcheck/releases/download/v5.3.0/epubcheck-5.3.0.zip" \
    ALKAHEST_EPUBCHECK_ARCHIVE_SHA256="6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5" \
    ALKAHEST_LIBERTINUS_ARCHIVE_URL="https://github.com/alerque/libertinus/releases/download/v7.051/Libertinus-7.051.zip" \
    ALKAHEST_LIBERTINUS_ARCHIVE_SHA256="4d9be29b5cb380c35af8ba967abcc752ad1e07be1f738a9789c33e0dd7478c92" \
    ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_URL="https://github.com/adobe-fonts/source-code-pro/releases/download/2.042R-u%2F1.062R-i%2F1.026R-vf/OTF-source-code-pro-2.042R-u_1.062R-i.zip" \
    ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_SHA256="754a2e3ebb945ae905d720ac5896b3b34acc9546dd6551ef9536869788629dae" \
    ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_URL="https://github.com/adobe-fonts/source-code-pro/releases/download/2.042R-u%2F1.062R-i%2F1.026R-vf/WOFF2-source-code-pro-2.042R-u_1.062R-i_1.026Rvf.zip" \
    ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_SHA256="2184c1f2bac48f4f7d952b0147dc0e48069fd1fb4a8c31b869b708efc978d365" \
    ALKAHEST_SOURCE_CODE_PRO_LICENSE_URL="https://raw.githubusercontent.com/adobe-fonts/source-code-pro/d3f1a5962cde503f9409c21e58527611d4a19ef1/LICENSE.md" \
    ALKAHEST_SOURCE_CODE_PRO_LICENSE_SHA256="7c940e28a5388e9bba866cf0e408edda45fe0899ba98665b8f6ab31dc5e4b8ff" \
    ALKAHEST_UV_ARCHIVE_URL="https://github.com/astral-sh/uv/releases/download/0.12.5/uv-x86_64-unknown-linux-gnu.tar.gz" \
    ALKAHEST_UV_ARCHIVE_SHA256="68a509da24b06b4223a1c0175fb5eb5bc79342b76cbeff0cfe51ac3f5b17b6b2"

USER root

# Runtime libraries required by Chrome Headless Shell plus Java and Poppler.
# The immutable Ubuntu archive view fixes the complete dependency solution
# without repeating distribution-specific package versions here. The minimal
# base omits CA roots, so the first signed-snapshot transaction disables only
# TLS peer checking while it installs ca-certificates; normal verification is
# required immediately afterward.
RUN sed -i \
        -e "s|http://archive.ubuntu.com/ubuntu/|${ALKAHEST_UBUNTU_SNAPSHOT}/|g" \
        -e "s|http://security.ubuntu.com/ubuntu/|${ALKAHEST_UBUNTU_SNAPSHOT}/|g" \
        /etc/apt/sources.list \
    && apt-get -o Acquire::https::Verify-Peer=false update \
    && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::https::Verify-Peer=false install --yes --no-install-recommends ca-certificates \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        curl \
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
        openjdk-11-jre-headless \
        poppler-utils \
        unzip \
        xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Quarto's diagram renderer needs a browser for non-HTML targets.
RUN test "$(dpkg --print-architecture)" = "amd64" \
    && curl --fail --location --silent --show-error --output /tmp/chrome-headless-shell-linux64.zip "${ALKAHEST_CHROME_ARCHIVE_URL}" \
    && echo "${ALKAHEST_CHROME_ARCHIVE_SHA256}  /tmp/chrome-headless-shell-linux64.zip" | sha256sum --check \
    && unzip -q /tmp/chrome-headless-shell-linux64.zip -d /tmp/chrome-headless-shell \
    && mkdir -p /opt/chrome-headless-shell \
    && cp -a /tmp/chrome-headless-shell/chrome-headless-shell-linux64/. /opt/chrome-headless-shell/ \
    && chmod -R a+rX /opt/chrome-headless-shell \
    && rm -rf /tmp/chrome-headless-shell /tmp/chrome-headless-shell-linux64.zip

ENV QUARTO_CHROMIUM=/opt/chrome-headless-shell/chrome-headless-shell

# Use the W3C EPUB conformance checker rather than a partial local validator.
RUN curl --fail --location --silent --show-error --output /tmp/epubcheck-5.3.0.zip "${ALKAHEST_EPUBCHECK_ARCHIVE_URL}" \
    && echo "${ALKAHEST_EPUBCHECK_ARCHIVE_SHA256}  /tmp/epubcheck-5.3.0.zip" | sha256sum --check \
    && unzip -q /tmp/epubcheck-5.3.0.zip -d /opt \
    && mv /opt/epubcheck-5.3.0 /opt/epubcheck \
    && rm /tmp/epubcheck-5.3.0.zip \
    && java -jar /opt/epubcheck/epubcheck.jar --version

ENV EPUBCHECK_JAR=/opt/epubcheck/epubcheck.jar

# Install one versioned, OFL-licensed font stack for every output. Keep
# WOFF2 siblings beside it so the later web/EPUB theme can use identical source
# releases without introducing another network-resolved build input.
RUN curl --fail --location --silent --show-error --output /tmp/libertinus.zip "${ALKAHEST_LIBERTINUS_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error --output /tmp/source-code-pro-otf.zip "${ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error --output /tmp/source-code-pro-woff2.zip "${ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error --output /tmp/source-code-pro-ofl.md "${ALKAHEST_SOURCE_CODE_PRO_LICENSE_URL}" \
    && echo "${ALKAHEST_LIBERTINUS_ARCHIVE_SHA256}  /tmp/libertinus.zip" | sha256sum --check \
    && echo "${ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_SHA256}  /tmp/source-code-pro-otf.zip" | sha256sum --check \
    && echo "${ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_SHA256}  /tmp/source-code-pro-woff2.zip" | sha256sum --check \
    && echo "${ALKAHEST_SOURCE_CODE_PRO_LICENSE_SHA256}  /tmp/source-code-pro-ofl.md" | sha256sum --check \
    && unzip -q /tmp/libertinus.zip -d /tmp/libertinus \
    && unzip -q /tmp/source-code-pro-otf.zip -d /tmp/source-code-pro-otf \
    && unzip -q /tmp/source-code-pro-woff2.zip -d /tmp/source-code-pro-woff2 \
    && install -d \
        /usr/local/share/fonts/alkahest/libertinus \
        /usr/local/share/fonts/alkahest/source-code-pro \
        /usr/local/share/doc/fonts/libertinus \
        /usr/local/share/doc/fonts/source-code-pro \
        /opt/alkahest/fonts/web/libertinus \
        /opt/alkahest/fonts/web/source-code-pro \
    && install -m 0644 /tmp/libertinus/Libertinus-7.051/static/OTF/*.otf /usr/local/share/fonts/alkahest/libertinus/ \
    && install -m 0644 /tmp/libertinus/Libertinus-7.051/static/WOFF2/*.woff2 /opt/alkahest/fonts/web/libertinus/ \
    && install -m 0644 /tmp/libertinus/Libertinus-7.051/OFL.txt /usr/local/share/doc/fonts/libertinus/OFL.txt \
    && install -m 0644 /tmp/source-code-pro-otf/OTF/*.otf /usr/local/share/fonts/alkahest/source-code-pro/ \
    && install -m 0644 /tmp/source-code-pro-woff2/WOFF2/OTF/*.woff2 /opt/alkahest/fonts/web/source-code-pro/ \
    && install -m 0644 /tmp/source-code-pro-ofl.md /usr/local/share/doc/fonts/source-code-pro/OFL.md \
    && fc-cache --force \
    && rm -rf \
        /tmp/libertinus \
        /tmp/libertinus.zip \
        /tmp/source-code-pro-otf \
        /tmp/source-code-pro-otf.zip \
        /tmp/source-code-pro-woff2 \
        /tmp/source-code-pro-woff2.zip \
        /tmp/source-code-pro-ofl.md

# Explicit font paths take precedence over Typst's embedded fallback fonts.
ENV TYPST_FONT_PATHS=/usr/local/share/fonts/alkahest

# Verify the installed family names before Typst uses them.
RUN test "$(fc-match --format '%{family[0]}' 'Libertinus Serif')" = "Libertinus Serif" \
    && test "$(fc-match --format '%{family[0]}' 'Libertinus Serif Display')" = "Libertinus Serif Display" \
    && test "$(fc-match --format '%{family[0]}' 'Libertinus Sans')" = "Libertinus Sans" \
    && test "$(fc-match --format '%{family[0]}' 'Libertinus Math')" = "Libertinus Math" \
    && test "$(fc-match --format '%{family[0]}' 'Source Code Pro')" = "Source Code Pro"

# Provide a safe default identity for direct `podman run` use. The project
# wrapper overrides this with the invoking host UID/GID so bind-mounted build
# artifacts remain owned by the developer, but never asks the container to run
# as root.
RUN groupadd --gid 10001 alkahest \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin alkahest \
    && install --directory --owner=10001 --group=10001 /workspace

# Install the exact uv release used by the root Python project. uv then installs
# its checksum-verified Python build and the locked runtime environment;
# neither normal rendering nor validation needs the network or writes package
# state into the bind-mounted repository.
RUN curl --fail --location --silent --show-error --output /tmp/uv.tar.gz "${ALKAHEST_UV_ARCHIVE_URL}" \
    && echo "${ALKAHEST_UV_ARCHIVE_SHA256}  /tmp/uv.tar.gz" | sha256sum --check \
    && tar --extract --gzip --file /tmp/uv.tar.gz --directory /tmp \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-gnu \
    && uv --version

COPY pyproject.toml uv.lock .python-version /opt/alkahest/tools-project/

RUN export UV_CACHE_DIR=/tmp/uv-cache \
        UV_PYTHON_INSTALL_DIR=/opt/alkahest/python \
        UV_PROJECT_ENVIRONMENT=/opt/alkahest/tools \
        UV_LINK_MODE=copy \
    && uv python install 3.13.15 \
    && uv sync --project /opt/alkahest/tools-project --locked --no-default-groups --no-install-project --python 3.13.15 \
    && /opt/alkahest/tools/bin/python -c 'import yaml; assert yaml.__version__ == "6.0.3"' \
    && chmod -R a+rX /opt/alkahest/python /opt/alkahest/tools /opt/alkahest/tools-project \
    && rm -rf /tmp/uv-cache

# Keep JavaScript and prose-tool identities beside their late install layers so
# changes do not invalidate the larger font, browser, and media environments.
ENV ALKAHEST_NODE_VERSION="22.23.2" \
    ALKAHEST_NODE_ARCHIVE_URL="https://nodejs.org/download/release/v22.23.2/node-v22.23.2-linux-x64.tar.xz" \
    ALKAHEST_NODE_ARCHIVE_SHA256="d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307" \
    ALKAHEST_NPM_VERSION="10.9.8" \
    ALKAHEST_VALE_VERSION="3.17.1" \
    ALKAHEST_VALE_ARCHIVE_URL="https://github.com/vale-cli/vale/releases/download/v3.17.1/vale_3.17.1_Linux_64-bit.tar.gz" \
    ALKAHEST_VALE_ARCHIVE_SHA256="db947f89f2292e6a0381a61de155f6a5f5cb4cb460ca178ea412ef605559cefd" \
    ALKAHEST_CSPELL_VERSION="10.0.1" \
    ALKAHEST_AXE_CORE_VERSION="4.13.0" \
    ALKAHEST_ACE_VERSION="1.4.6"

# Install the writing-quality executables from immutable inputs. Node is a
# declared CSpell runtime rather than an accidental base-image dependency;
# Vale is a standalone binary. Downloads use /tmp only as transient build
# storage, while the finished tools live in /opt and /usr/local/bin.
RUN test "$(dpkg --print-architecture)" = "amd64" \
    && curl --fail --location --silent --show-error --output /tmp/node.tar.xz "${ALKAHEST_NODE_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error --output /tmp/vale.tar.gz "${ALKAHEST_VALE_ARCHIVE_URL}" \
    && echo "${ALKAHEST_NODE_ARCHIVE_SHA256}  /tmp/node.tar.xz" | sha256sum --check \
    && echo "${ALKAHEST_VALE_ARCHIVE_SHA256}  /tmp/vale.tar.gz" | sha256sum --check \
    && install --directory /opt/node /tmp/vale \
    && tar --extract --xz --file /tmp/node.tar.xz --directory /opt/node --strip-components=1 \
    && tar --extract --gzip --file /tmp/vale.tar.gz --directory /tmp/vale \
    && install -m 0755 /tmp/vale/vale /usr/local/bin/vale \
    && install -d /usr/local/share/doc/vale \
    && install -m 0644 /tmp/vale/LICENSE /usr/local/share/doc/vale/LICENSE \
    && ln -s /opt/node/bin/node /usr/local/bin/node \
    && ln -s /opt/node/bin/npm /usr/local/bin/npm \
    && test "$(/opt/node/bin/node --version)" = "v${ALKAHEST_NODE_VERSION}" \
    && test "$(/opt/node/bin/npm --version)" = "${ALKAHEST_NPM_VERSION}" \
    && test "$(vale --version)" = "vale version ${ALKAHEST_VALE_VERSION}" \
    && rm -rf /tmp/node.tar.xz /tmp/vale /tmp/vale.tar.gz

ENV PATH="/opt/node/bin:/opt/alkahest/writing/node_modules/.bin:${PATH}"
ENV PUPPETEER_EXECUTABLE_PATH="${QUARTO_CHROMIUM}" \
    PUPPETEER_SKIP_DOWNLOAD="true"

# npm's lockfile records the integrity of CSpell, axe-core, Ace by DAISY, and
# every transitive package.
# Ignore lifecycle scripts and remove the transient package cache so runtime
# checks are offline, deterministic, and writable by neither the manuscript nor
# the unprivileged publishing user.
COPY tools/writing/package.json tools/writing/package-lock.json /opt/alkahest/writing/

RUN npm ci --prefix /opt/alkahest/writing --omit=dev --ignore-scripts --no-audit --no-fund --cache /tmp/npm-cache \
    && test "$(cspell --version)" = "${ALKAHEST_CSPELL_VERSION}" \
    && test "$(node -p "require('/opt/alkahest/writing/node_modules/axe-core/package.json').version")" = "${ALKAHEST_AXE_CORE_VERSION}" \
    && test "$(HOME=/tmp ace-cli --version)" = "${ALKAHEST_ACE_VERSION}" \
    && ln -s /opt/alkahest/writing/node_modules/.bin/cspell /usr/local/bin/cspell \
    && chmod -R a+rX /opt/alkahest/writing \
    && rm -rf /tmp/npm-cache

# Embed the author engine in its runtime layout. The development
# repository keeps canonical files in book/, scripts/, and src/; the runtime
# image presents one read-only engine root so a mounted book needs none of this
# repository's source code.
COPY book/_extensions/ /opt/alkahest/engine/_extensions/
COPY book/filters/ /opt/alkahest/engine/filters/
COPY book/icons/ /opt/alkahest/engine/icons/
COPY book/theme/ /opt/alkahest/engine/theme/
COPY book/typst/ /opt/alkahest/engine/typst/
COPY book/_brand.yml /opt/alkahest/engine/_brand.yml
COPY book/alkahest-defaults.yml /opt/alkahest/engine/defaults/quarto.yml
COPY scripts/author.py /opt/alkahest/engine/scripts/author.py
COPY src/alkahest/__init__.py src/alkahest/author_project.py src/alkahest/process.py /opt/alkahest/engine/src/alkahest/

# Stage the twelve locked web faces as regular files. Quarto preserves resource
# timestamps while copying, which cannot operate through a symlink whose target
# lives in the image's read-only font directory at runtime.
RUN install --directory /opt/alkahest/engine/theme/fonts \
    && install -m 0644 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSans-Bold.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSans-Italic.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSans-Regular.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSerif-Bold.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSerif-BoldItalic.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSerif-Italic.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSerif-Regular.woff2 \
        /opt/alkahest/fonts/web/libertinus/LibertinusSerifDisplay-Regular.woff2 \
        /opt/alkahest/fonts/web/source-code-pro/SourceCodePro-Bold.otf.woff2 \
        /opt/alkahest/fonts/web/source-code-pro/SourceCodePro-BoldIt.otf.woff2 \
        /opt/alkahest/fonts/web/source-code-pro/SourceCodePro-It.otf.woff2 \
        /opt/alkahest/fonts/web/source-code-pro/SourceCodePro-Regular.otf.woff2 \
        /opt/alkahest/engine/theme/fonts/ \
    && chmod -R a+rX /opt/alkahest/engine \
    && /opt/alkahest/tools/bin/python /opt/alkahest/engine/scripts/author.py --help >/dev/null

ENV HOME=/home/alkahest
# Maintainer containers prefer a mounted checkout; standalone book containers
# fall back to the embedded runtime when /workspace/src is absent.
ENV PYTHONPATH=/workspace/src:/opt/alkahest/engine/src
ENV PATH="/opt/alkahest/tools/bin:${PATH}"
WORKDIR /workspace

# Identify the image and link it to its source repository. The build wrapper
# replaces the development identity when producing a release image.
LABEL org.opencontainers.image.title="Alkahest" \
    org.opencontainers.image.description="Containerized publishing engine for Quarto Markdown books" \
    org.opencontainers.image.source="https://github.com/barrettotte/alkahest" \
    org.opencontainers.image.url="https://github.com/barrettotte/alkahest" \
    org.opencontainers.image.documentation="https://github.com/barrettotte/alkahest#readme" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.version="development" \
    org.opencontainers.image.revision="unknown"

# Rendering and validation run unprivileged even when the caller invokes the
# image directly instead of using the repository wrappers.
USER 10001:10001
