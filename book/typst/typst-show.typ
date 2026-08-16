// Adapt Quarto's bundled orange-book partial for Alkahest's shared page system.
// Keep wrappers narrow so future Quarto upgrades remain easy to compare.
#import "@preview/orange-book:0.7.1" as orange-book

#set text(font: "$mainfont$")

// Quarto's book filter emits these function names into the generated Typst.
// The wrappers preserve that interface while applying the selected display face.
#let part(title) = orange-book.part(text(font: "$displayfont$", title))
#let chapter(title, image: none, l: none) = orange-book.chapter(
  text(font: "$displayfont$", title),
  image: image,
  l: l,
)
#let appendices(title, doc, hide-parent: false) = orange-book.appendices(
  title,
  doc,
  hide-parent: hide-parent,
)

// Orange-book accepts one copyright content value. Isolated page functions
// give us separate, furniture-free publication-data and dedication pages.
#let alkahest-front-matter = [
  #page(header: none, footer: none, numbering: none)[
    #place(bottom + left, block(width: 100%)[
      #set text(font: "$mainfont$", size: 10pt)
      #set par(spacing: 0.65em)
      #text(font: "$displayfont$", size: 18pt)[Publication data]
      #v(1.2em)
      Copyright © $alkahest.copyright-year$ $alkahest.copyright-holder$\
      $alkahest.rights-statement$\
      #v(0.5em)
      $alkahest.edition$\
      $alkahest.publisher$\
      $alkahest.identifier$\
      #v(0.5em)
      This page contains template placeholders, not publication or legal claims.
    ])
  ]
  #page(header: none, footer: none, numbering: none)[
    #place(center + horizon, text(font: "$displayfont$", size: 18pt)[$alkahest.dedication$])
  ]
  // Reserve the verso after the dedication so the contents begins recto.
  #page(header: none, footer: none, numbering: none)[]
]

#show: orange-book.book.with(
$if(title)$
  title: [#text(font: "$displayfont$")[$title$]],
$endif$
$if(subtitle)$
  subtitle: [#text(font: "$sansfont$")[$subtitle$]],
$endif$
$if(by-author)$
  author: "$for(by-author)$$it.name.literal$$sep$, $endfor$\n$alkahest.edition$",
$endif$
$if(date)$
  date: "$date$",
$endif$
$if(lang)$
  lang: "$lang$",
$endif$
$if(trim-width)$
  width: $trim-width$,
$endif$
$if(trim-height)$
  height: $trim-height$,
$endif$
$if(body-font-size)$
  font-size: $body-font-size$,
$endif$
  main-color: brand-color.at("primary", default: rgb("#334155")),
  copyright: alkahest-front-matter,
  part-style: 1,
  heading-style: 1,
  logo: {
    let logo-info = brand-logo.at("medium", default: none)
    if logo-info != none { image(logo-info.path, alt: logo-info.at("alt", default: none)) }
  },
$if(toc-depth)$
  outline-depth: $toc-depth$,
$endif$
$if(lof)$
$if(crossref.lof-title)$
  list-of-figure-title: "$crossref.lof-title$",
$else$
$if(quarto.language.crossref-lof-title)$
  list-of-figure-title: "$quarto.language.crossref-lof-title$",
$endif$
$endif$
$endif$
$if(lot)$
$if(crossref.lot-title)$
  list-of-table-title: "$crossref.lot-title$",
$else$
$if(quarto.language.crossref-lot-title)$
  list-of-table-title: "$quarto.language.crossref-lot-title$",
$endif$
$endif$
$endif$
$if(quarto.language.crossref-ch-prefix)$
  supplement-chapter: "$quarto.language.crossref-ch-prefix$",
$endif$
$if(margin-geometry)$
  padded-heading-number: false,
$endif$
)

$if(margin-geometry)$
// Apply book-aware inside/outside margins after orange-book's page setup.
#import "@preview/marginalia:0.3.1" as marginalia

#show: marginalia.setup.with(
  inner: (
    far: $margin-geometry.inner.far$,
    width: $margin-geometry.inner.width$,
    sep: $margin-geometry.inner.separation$,
  ),
  outer: (
    far: $margin-geometry.outer.far$,
    width: $margin-geometry.outer.width$,
    sep: $margin-geometry.outer.separation$,
  ),
  top: $if(margin.top)$$margin.top$$else$1.25in$endif$,
  bottom: $if(margin.bottom)$$margin.bottom$$else$1.25in$endif$,
  book: true,
  clearance: $margin-geometry.clearance$,
)
$endif$

// Use one restrained body rhythm across Typst and LuaLaTeX. This rule is
// intentionally applied after orange-book so it replaces the package's extra
// paragraph gap while retaining its heading, list, and figure treatments.
#let alkahest-body-style(body) = {
  // Orange-book places a second folio in the default footer; its running head
  // already provides the single outward folio required by the design contract.
  set page(numbering: none)
  set text(font: "$mainfont$")
  set par(
    justify: true,
    leading: $body-leading$,
    first-line-indent: $paragraph-indent$,
    spacing: $paragraph-spacing$,
  )
  show heading: set text(font: "$sansfont$")
  // Quarto/Typst currently carries numbering deeper than number-depth. Keep
  // H4-H6 as local, unnumbered structure to match HTML/EPUB and LuaLaTeX.
  show heading.where(level: 4): set heading(numbering: none)
  show heading.where(level: 5): set heading(numbering: none)
  show heading.where(level: 6): set heading(numbering: none)
  show math.equation: set text(font: "$mathfont$")
  show raw: set text(font: "$monofont$")
  body
}

#show: alkahest-body-style
