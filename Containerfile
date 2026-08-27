# Pin the upstream image by manifest digest so a reused Quarto tag cannot change
# the base filesystem beneath this publishing toolchain.
FROM ghcr.io/quarto-dev/quarto:1.10.18@sha256:3c10521544c4f182eb5edf3c807f99c5ddad93869b233052fa13cf7cdba13572

# Keep every network-resolved bootstrap input visible in one place. These are
# intentionally ENV values, not build arguments: all developers and CI use the
# same source identities and the report command can inspect them at runtime.
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
    && DEBIAN_FRONTEND=noninteractive apt-get \
        -o Acquire::https::Verify-Peer=false \
        install --yes --no-install-recommends ca-certificates \
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

# Install one versioned, OFL-licensed font stack for every output. Keep
# WOFF2 siblings beside it so the later web/EPUB theme can use identical source
# releases without introducing another network-resolved build input.
RUN curl --fail --location --silent --show-error \
        --output /tmp/libertinus.zip \
        "${ALKAHEST_LIBERTINUS_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error \
        --output /tmp/source-code-pro-otf.zip \
        "${ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error \
        --output /tmp/source-code-pro-woff2.zip \
        "${ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error \
        --output /tmp/source-code-pro-ofl.md \
        "${ALKAHEST_SOURCE_CODE_PRO_LICENSE_URL}" \
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

# Assert the exact faces selected for manuscripts and verify their family names
# resolve through fontconfig before Typst uses them.
RUN set -eu; \
    echo "fcf06307a77367394fcb0ccb241e59eea70dba3d732be309647611224679c733  /usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Regular.otf" | sha256sum --check; \
    echo "0264914210ed51b3231ebc92ce529e9f2e166ba9eebf0cd4a579558690a27b64  /usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Bold.otf" | sha256sum --check; \
    echo "9a393d63d6e05f620d3dc0190dfd35a8ede58c0808cf0fc9de7fcb9c723e4c24  /usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Italic.otf" | sha256sum --check; \
    echo "47a665259f09f554f5d133d7718cdad43ff462c6a6b2328f38023465e62d57ce  /usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-BoldItalic.otf" | sha256sum --check; \
    echo "7734b4d4cc5f3b98926f47a1389d775107496c813269cfed238dae5bd9329d44  /usr/local/share/fonts/alkahest/libertinus/LibertinusSerifDisplay-Regular.otf" | sha256sum --check; \
    echo "8f897bcf5b209f7c4b2a18a688dab10b723961b87690cbf54c927d7a68e0c442  /usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Regular.otf" | sha256sum --check; \
    echo "51bdd322b60ceabd9e137225273b2eb493acd7ca9abd2b2395c4a5dd67c39cc9  /usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Bold.otf" | sha256sum --check; \
    echo "e5a3083685b8aeca96e1820ad9478de95056e129177c35d6c31537bff8ddd515  /usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Italic.otf" | sha256sum --check; \
    echo "ded714b0d3808af527438ed7a85f16933133f66a12104c4a83db4cc248888011  /usr/local/share/fonts/alkahest/libertinus/LibertinusMath-Regular.otf" | sha256sum --check; \
    echo "9f9664e2edf6f045c11e774f9bd0be6993971f2544a39061a5ce478b96b051f8  /usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-Regular.otf" | sha256sum --check; \
    echo "6f5a4a46a99ad1b92a8675e98f148272c8d2476fc0eb067247dd5eea6a3ad84c  /usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-Bold.otf" | sha256sum --check; \
    echo "6989245c8747ecef5d927f412b49e2cef495053434b635f560f20cc81a1433d1  /usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-It.otf" | sha256sum --check; \
    echo "a015a5762527946aa99778f5397da14d10b963938d1d6e08153f173fdf29d8ee  /usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-BoldIt.otf" | sha256sum --check; \
    test "$(fc-match --format '%{family[0]}' 'Libertinus Serif')" = "Libertinus Serif"; \
    test "$(fc-match --format '%{family[0]}' 'Libertinus Serif Display')" = "Libertinus Serif Display"; \
    test "$(fc-match --format '%{family[0]}' 'Libertinus Sans')" = "Libertinus Sans"; \
    test "$(fc-match --format '%{family[0]}' 'Libertinus Math')" = "Libertinus Math"; \
    test "$(fc-match --format '%{family[0]}' 'Source Code Pro')" = "Source Code Pro"

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

# Install the exact uv release used by the root Python project. uv then installs
# its checksum-verified Python build and the locked runtime environment;
# neither normal rendering nor validation needs the network or writes package
# state into the bind-mounted repository.
RUN curl --fail --location --silent --show-error \
        --output /tmp/uv.tar.gz \
        "${ALKAHEST_UV_ARCHIVE_URL}" \
    && echo "${ALKAHEST_UV_ARCHIVE_SHA256}  /tmp/uv.tar.gz" \
        | sha256sum --check \
    && tar --extract --gzip --file /tmp/uv.tar.gz --directory /tmp \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uv /usr/local/bin/uv \
    && install -m 0755 /tmp/uv-x86_64-unknown-linux-gnu/uvx /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-gnu \
    && echo "b65f23a420c4acc96427efb30e5ed9bc0f7e25d2d712000f6ede77c1a0de5f46  /usr/local/bin/uv" \
        | sha256sum --check \
    && uv --version

COPY pyproject.toml uv.lock .python-version /opt/alkahest/tools-project/

RUN UV_CACHE_DIR=/tmp/uv-cache \
        UV_PYTHON_INSTALL_DIR=/opt/alkahest/python \
        UV_PROJECT_ENVIRONMENT=/opt/alkahest/tools \
        UV_LINK_MODE=copy \
        uv python install 3.13.15 \
    && UV_CACHE_DIR=/tmp/uv-cache \
        UV_PYTHON_INSTALL_DIR=/opt/alkahest/python \
        UV_PROJECT_ENVIRONMENT=/opt/alkahest/tools \
        UV_LINK_MODE=copy \
        uv sync \
            --project /opt/alkahest/tools-project \
            --locked \
            --no-default-groups \
            --no-install-project \
            --python 3.13.15 \
    && /opt/alkahest/tools/bin/python -c \
        'import yaml; assert yaml.__version__ == "6.0.3"' \
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
    && curl --fail --location --silent --show-error \
        --output /tmp/node.tar.xz \
        "${ALKAHEST_NODE_ARCHIVE_URL}" \
    && curl --fail --location --silent --show-error \
        --output /tmp/vale.tar.gz \
        "${ALKAHEST_VALE_ARCHIVE_URL}" \
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
    && echo "3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327  /opt/node/bin/node" | sha256sum --check \
    && echo "ae9c62ed1c422cc5641f83a0045790cb2029c2bd9a21d2b7c216f3cb254f1231  /usr/local/bin/vale" | sha256sum --check \
    && test "$(/opt/node/bin/node --version)" = "v${ALKAHEST_NODE_VERSION}" \
    && test "$(/opt/node/bin/npm --version)" = "${ALKAHEST_NPM_VERSION}" \
    && test "$(vale --version)" = "vale version ${ALKAHEST_VALE_VERSION}" \
    && rm -rf /tmp/node.tar.xz /tmp/vale /tmp/vale.tar.gz

ENV PATH="/opt/node/bin:/opt/alkahest/writing/node_modules/.bin:${PATH}"
ENV PUPPETEER_EXECUTABLE_PATH="${QUARTO_CHROMIUM}" \
    PUPPETEER_SKIP_DOWNLOAD="true"

# npm's lockfile records the integrity of CSpell, axe-core, Ace by DAISY, and
# every transitive package.
# Ignore lifecycle scripts and remove the temporary package cache so runtime
# checks are offline, deterministic, and writable by neither the manuscript nor
# the unprivileged publishing user.
COPY tools/writing/package.json tools/writing/package-lock.json /opt/alkahest/writing/

RUN npm ci \
        --prefix /opt/alkahest/writing \
        --omit=dev \
        --ignore-scripts \
        --no-audit \
        --no-fund \
        --cache /tmp/npm-cache \
    && test "$(cspell --version)" = "${ALKAHEST_CSPELL_VERSION}" \
    && test "$(node -p "require('/opt/alkahest/writing/node_modules/axe-core/package.json').version")" = "${ALKAHEST_AXE_CORE_VERSION}" \
    && test "$(HOME=/tmp ace-cli --version)" = "${ALKAHEST_ACE_VERSION}" \
    && echo "fb0e83febdda495e211bc95d9676d3146cea78f240e1a815cb73ef3005be6cfd  /opt/alkahest/writing/node_modules/cspell/bin.mjs" \
        | sha256sum --check \
    && echo "c24f097bd2f451d4f933e8bc7d8d539f8672a2ebcb5cc9f9f3eec8ca9470a0c1  /opt/alkahest/writing/node_modules/axe-core/axe.min.js" \
        | sha256sum --check \
    && echo "39909ce78d85972fb694db2f485d117e051b6bb925f01c149fab303df6eef537  /opt/alkahest/writing/node_modules/@daisy/ace-cli/bin/ace.js" \
        | sha256sum --check \
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

# Rendering and validation run unprivileged even when the caller invokes the
# image directly instead of using the repository wrappers.
USER 10001:10001
