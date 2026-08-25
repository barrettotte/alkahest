# Toolchain lock record

- Captured: 2026-08-20
- Derived image: `localhost/alkahest-publishing:quarto-1.10.18-v19`
- Base image: `ghcr.io/quarto-dev/quarto-full:1.10.18`
- Base manifest: `sha256:280aa58ecdb814dcced42066e4f64d1825020ce5822f2ca2749fc6396020d7de`

Run `make toolchain-report` to inspect the locally built image. The Containerfile
also checks installed browser bytes, TeX package revisions,
and selected font files during bootstrap. A mismatch fails the image build and
requires an intentional lock update.

## Immutable bootstrap sources

| Input | Locked identity |
|---|---|
| Ubuntu archive | Snapshot `20260816T000000Z`; direct Chrome and Python runtime dependencies are version-pinned in the Containerfile |
| Python runtimes | Ubuntu `python3` `3.8.2-0ubuntu2` retained for base-image utilities; uv-managed Python 3.13.15 is active for the library, validators, development gates, and media generators |
| uv | Official 0.12.5 x86_64 GNU/Linux archive; SHA-256 `68a509da24b06b4223a1c0175fb5eb5bc79342b76cbeff0cfe51ac3f5b17b6b2` |
| Python project dependencies | Root `uv.lock` SHA-256 `970a925b8dcc2e5f83763d58fa946b76e1d374dc1be4635f25f0c2a86011aad4`; defusedxml 0.7.1, Schemdraw 0.23, RDKit 2026.3.5, NumPy 2.5.2, and Pillow 12.3.0 distributions are hash-locked there |
| Node.js | Official 22.23.2 LTS Linux x64 archive; SHA-256 `d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307` |
| Vale | Official 3.17.1 Linux 64-bit archive; SHA-256 `db947f89f2292e6a0381a61de155f6a5f5cb4cb460ca178ea412ef605559cefd` |
| JavaScript checks | npm lockfile v3 SHA-256 `d098069504bec89dc161f5be7359f5a217ff13dc617699094a29dc06e7c714f1`; CSpell 10.0.1, axe-core 4.13.0, Ace by DAISY 1.4.6, and all 343 installed packages carry registry integrity hashes |
| Chrome Headless Shell | Official Linux64 archive for 152.0.7977.42; SHA-256 `129686a270d84ac4637c614802c554634aa827aa13214216f81e0a0b9410f8cf` |
| EPUBCheck | Official 5.3.0 archive; SHA-256 `6c07e68584b2e2ce2f89fe06e1246dfead3eb36b46b340e7d93524f29dcff6c5` |
| veraPDF | Official Greenfield CLI installer 1.30.2; SHA-256 `6cc6341cb1af644044054b81f00a6590a7918abb18f762243de115258bcad838` |
| Chicago author–date CSL | Pandoc 3.10.0 bundled `default.csl`; SHA-256 `91fa1fe9787e737dff0c15d7cf8254c9f2bab4ebb4dccf4553a1f991ebddb7d1` |
| IEEE numeric CSL | CSL styles commit `1f32ca7259171b3c35b008ef41613df1215dad75`; SHA-256 `b4c7619fc16c45a31e4cc3271eab94ffe83192d3b4c7fc729470a3b459448de3` |
| Libertinus | Official 7.051 archive; SHA-256 `4d9be29b5cb380c35af8ba967abcc752ad1e07be1f738a9789c33e0dd7478c92` |
| Source Code Pro OTF | Official upright 2.042 / italic 1.062 archive; SHA-256 `754a2e3ebb945ae905d720ac5896b3b34acc9546dd6551ef9536869788629dae` |
| Source Code Pro WOFF2 | Official upright 2.042 / italic 1.062 / variable 1.026 archive; SHA-256 `2184c1f2bac48f4f7d952b0147dc0e48069fd1fb4a8c31b869b708efc978d365` |
| TeX Live | Daily archive `2026/08/16`; `texlive.tlpdb.xz` SHA-256 `a1b87eb64a6ffd2076f6bfc872e9ea0aa1e56ba7fe585636eed18a388d4adf8e` |

The base image does not provide GPG to `tlmgr`. The checked-in SHA-256 of the
dated TeX Live package database is therefore this build's repository trust
anchor; package revisions and selected installed font hashes provide additional
post-install checks.

## Tools

| Component | Locked identity |
|---|---|
| Quarto | 1.10.18; transitively locked by base-image manifest |
| Pandoc | 3.10.0; binary SHA-256 `8fedc028b2314cd649b6cabf363c94a7c940aff352a1c20753ffb0875f083cac` |
| Typst | 0.15.1 (`9dfd3a08`); binary SHA-256 `29273eaa04f6d00edd0c2bec578f565fc9c65be856bfbffc894567c68ed0b237` |
| LuaHBTeX | 1.24.0, TeX Live 2026; binary SHA-256 `9d7a1a55bb2503181d71ada62a6ef78303acdd9d99910ea8da33b059e89c8a8a` |
| Chrome for Testing | 152.0.7977.42; binary SHA-256 `7e0227229e5d5d6050a743ec8c2954b2e7b90e84d73c6796ab6ae61a0dde9bce` |
| EPUBCheck | 5.3.0; JAR SHA-256 `f7f96617c929371821609b88c8484d6dc9f24fe916499863c46094c5fb778a65` |
| veraPDF | 1.30.2 Greenfield CLI; PDF/UA-1 and PDF/UA-2 machine-verifiable profiles |
| OpenJDK | 11.0.27; Ubuntu package `openjdk-11-jre-headless` version `11.0.27+6~us1-0ubuntu1~20.04` |
| Poppler | 0.86.1; Ubuntu package `poppler-utils` version `0.86.1-0ubuntu1.7` |
| librsvg | 2.48.9; Ubuntu package `librsvg2-bin` version `2.48.9-1ubuntu0.20.04.4`; `rsvg-convert` SHA-256 `daaec6e04e775ff7582545e055d0559590ff44a75664ff94b0ec3562afeb9509` |
| uv | 0.12.5; installed binary SHA-256 `b65f23a420c4acc96427efb30e5ed9bc0f7e25d2d712000f6ede77c1a0de5f46` |
| Node.js and npm | Node.js 22.23.2 LTS; binary SHA-256 `3517c2df0b2f8cd7f422b4b8450ef81c6889f08eb03e281d6de9079b15e6a327`; npm 10.9.8 |
| Vale | 3.17.1; binary SHA-256 `ae9c62ed1c422cc5641f83a0045790cb2029c2bd9a21d2b7c216f3cb254f1231` |
| CSpell | 10.0.1; CLI SHA-256 `fb0e83febdda495e211bc95d9676d3146cea78f240e1a815cb73ef3005be6cfd`; resolved by npm from the committed lock |
| axe-core | 4.13.0; browser bundle SHA-256 `c24f097bd2f451d4f933e8bc7d8d539f8672a2ebcb5cc9f9f3eec8ca9470a0c1`; WCAG rules execute through the locked Chrome runtime |
| Ace by DAISY | 1.4.6; CLI SHA-256 `39909ce78d85972fb694db2f485d117e051b6bb925f01c149fab303df6eef537`; its Puppeteer runner uses the locked Chrome runtime without downloading a browser |
| Python environment | Python 3.13.15; defusedxml 0.7.1; Schemdraw 0.23; RDKit 2026.03.5; RDKit `rdchem.so` SHA-256 `b77e8e660aaeadd88dc39b9d3f00d6f83f3c26800715d44452050a8b6d1dcafb`; resolved by uv from the committed root lock |
| Mermaid runtime | Bundled with Quarto; JavaScript SHA-256 `07e37dfa97b337ccc85365d57eddf99b9706f09db3b59b260d0333b23b343c4b` |
| Graphviz runtime | Bundled with Quarto; wrapper SHA-256 `8d6c1517a55aea0aa05c1fae0eb221a6473bdc018e0c9e10e3e893ec4832ad4f`; WASM SHA-256 `75d33c9c6e0f3972b7fa064e67d03ce09c68a453f0adefdacd1c4dc1ed3ed943` |

## Selected font stack

Both PDF backends use Libertinus Serif for body text, Libertinus Sans for
headings, Libertinus Math for equations, and Source Code Pro for code. The
Libertinus Serif Display face is used for title and division-page designs.
Typst searches only the declared locked faces for manuscript text; LuaLaTeX
resolves the same system OTF files through fontspec.

The build checks the archive hashes and every selected OTF face. WOFF2 siblings
from the same releases supply the current HTML/EPUB theme. Full role, license,
and fallback decisions are recorded in `docs/font-selection.md` and
`docs/localization.md`.

The original Latin Modern and DejaVu baseline hashes remain asserted while the
backend comparison is active. The TeX packages are `lm` 2.005 at revision 77682
and `lm-math` 1.959 at revision 67718.

## Other asserted TeX packages

| Package | Revision | Catalog version |
|---|---:|---|
| babel-english | 77682 | 3.3r |
| babel-french | 79302 | not reported |
| babel-german | 78737 | 3.3 |
| babel-greek | 78101 | 1.15 |
| babel-hebrew | 77914 | 2.5 |
| babel-russian | 57376 | 1.3m |
| hyphen-english | 78069 | not reported |
| hyphen-french | 78069 | not reported |
| hyphen-german | 78069 | not reported |
| hyphen-greek | 78069 | 5 |
| hyphen-russian | 78069 | not reported |
| ruhyphen | 79618 | 1.6 |
| caption | 79618 | not reported |
| fvextra | 78296 | 1.14.0 |
| pgf | 79866 | 3.1.12 |
| tcolorbox | 79191 | 6.10.0 |
| tikzfill | 78793 | 1.2.0 |
| pdfcol | 79618 | 1.8 |
| fontawesome5 | 77682 | 5.15.4 |
| `latex` | 79618 | not reported |
| `l3kernel` | 79868 | not reported |
| `luamml` | 79442 | 0.9.2 |
| `latex-lab` | 79404 | not reported |
| `pdfmanagement` | 79164 | not reported |
| `tagpdf` | 79799 | 1.0d |
| koma-script | 77575 | 3.49.2 |

The Babel language modules and separate hyphenation-pattern packages provide
the locked LuaLaTeX behavior exercised by the English, French, German, Greek,
Russian, and Hebrew reference samples. They are installed during bootstrap so
an offline render never attempts a package download.

`fvextra` provides fixed-page wrapping for both spaced code and unbroken
tokens. `pgf` supplies the TikZ marker generated by Quarto's LuaLaTeX code-line
annotations. `tcolorbox` and its Quarto-required `tikzfill`, `pdfcol`, and
`fontawesome5` libraries supply the native callout environments. The authored
blocks currently suppress icons, but Quarto still loads the icon package in its
callout preamble. These packages are installed and revision-asserted during
bootstrap so the rootless renderer never attempts to modify TinyTeX at
publication time.

## Lock boundary

Bootstrap still needs network access to retrieve the immutable base manifest,
Ubuntu snapshot, browser archive, Node and Vale archives, checksum-locked npm
packages, uv-managed Python and locked wheels, and TeX snapshot. Normal checks,
generators, and renders run without network access. `make
check-writing-toolchain` additionally proves Vale, CSpell, axe-core, and Ace start
inside the unprivileged container with networking disabled. The accessibility
web workflow executes axe-core through locked Chrome after rendering; the EPUB
workflow runs EPUBCheck and Ace through the same offline image. Both keep manual
evidence separate from automated results. The EPUB gate additionally validates
the three-engine reader matrix, representative locations, text-scale plan,
artifact identity, result completeness, and conformance-claim state.
The upstream archives remain an availability dependency, so a future archival
phase should mirror the locked inputs when the project establishes durable
artifact storage.
