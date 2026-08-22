// Adapt Quarto's bundled orange-book partial for Alkahest's shared page system.
// The PDF/UA evaluation uses native Typst structure because orange-book's
// boxed outline rows cannot be represented as valid split structure tags.
$if(alkahest-pdf-ua)$
$else$
#import "@preview/orange-book:0.7.1" as orange-book
$endif$

#set text(font: "$mainfont$", fallback: false)

// Quarto's book filter emits these function names into the generated Typst.
// The wrappers preserve that interface while applying the selected display face.
$if(alkahest-pdf-ua)$
#let alkahest-part-counter = counter("alkahest-part-counter")
#let alkahest-appendix-state = state("appendix-state", none)

#let part(title) = context {
  let previous-heading = counter(heading).get()
  pagebreak(to: "odd")
  alkahest-part-counter.step()
  heading(level: 1, numbering: none, outlined: true)[
    #text(font: "$displayfont$", fallback: false)[
      Part #alkahest-part-counter.display("I"): #title
    ]
  ]
  // A part is real navigable structure but must not consume a chapter number.
  counter(heading).update(previous-heading)
}
#let chapter(title, image: none, l: none) = {
  if l != none {
    heading(level: 1, title) + label(l)
  } else {
    heading(level: 1, title)
  }
}
#let appendices(title, doc, hide-parent: false) = {
  counter(heading).update(0)
  alkahest-appendix-state.update(title)
  set figure(numbering: num => numbering("A.1", counter(heading).get().first(), num))
  set heading(numbering: (..numbers) => numbering("A.1", ..numbers.pos()))
  doc
}
$else$
#let part(title) = orange-book.part(text(font: "$displayfont$", fallback: false, title))
#let chapter(title, image: none, l: none) = orange-book.chapter(
  text(font: "$displayfont$", fallback: false, title),
  image: image,
  l: l,
)
#let appendices(title, doc, hide-parent: false) = orange-book.appendices(
  title,
  doc,
  hide-parent: hide-parent,
)
$endif$

// Orange-book accepts one copyright content value. Isolated page functions
// give us separate, furniture-free publication-data and dedication pages.
#let alkahest-front-matter = [
  #page(header: none, footer: none, numbering: none)[
    #place(bottom + left, block(width: 100%)[
      #set text(font: "$mainfont$", fallback: false, size: 10pt)
      #set par(spacing: 0.65em)
      #text(font: "$displayfont$", fallback: false, size: 18pt)[Publication data]
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
    #place(center + horizon, text(font: "$displayfont$", fallback: false, size: 18pt)[$alkahest.dedication$])
  ]
  // Reserve the verso after the dedication so the contents begins recto.
  #page(header: none, footer: none, numbering: none)[]
]

$if(alkahest-pdf-ua)$
#let alkahest-accessible-book(body) = {
  set document(title: "$title$", author: "$for(by-author)$$it.name.literal$$sep$, $endfor$")
  set text(font: "$mainfont$", fallback: false, size: $body-font-size$, lang: "$lang$")
  set page(
    width: $trim-width$,
    height: $trim-height$,
    margin: (inside: $margin-geometry.inner.far$, outside: $margin-geometry.outer.far$, top: $margin.top$, bottom: $margin.bottom$),
    numbering: "1",
  )
  set heading(numbering: (..numbers) => numbering("1.1", ..numbers.pos()))
  show heading.where(level: 1): set heading(supplement: "Chapter")
  set figure(numbering: number => numbering("1.1", counter(heading).get().first(), number))
  set math.equation(numbering: number => numbering("(1.1)", counter(heading).get().first(), number))

  page(header: none, footer: none, numbering: none)[
    #align(center + horizon, block(width: 86%)[
      #set par(justify: false)
      #text(font: "$displayfont$", fallback: false, size: 30pt, weight: "bold")[$title$]
      #v(1.2em)
      #text(font: "$sansfont$", fallback: false, size: 16pt)[$subtitle$]
      #v(2em)
      #text(font: "$sansfont$", fallback: false)[$for(by-author)$$it.name.literal$$sep$, $endfor$]
    ])
  ]
  alkahest-front-matter
  pagebreak(to: "odd")
  outline(title: [Contents], depth: $toc-depth$)
  pagebreak(to: "odd")
  body
}

$if(subject)$
// Orange-book owns title/author but inherits these canonical document fields.
#set document(description: "$subject$")
$endif$
$if(keywords)$
#set document(keywords: ($for(keywords)$"$keywords$",$endfor$))
$endif$

#show: alkahest-accessible-book
$else$
$if(subject)$
// Orange-book owns title/author but inherits these canonical document fields.
#set document(description: "$subject$")
$endif$
$if(keywords)$
#set document(keywords: ($for(keywords)$"$keywords$",$endfor$))
$endif$

#show: orange-book.book.with(
$if(title)$
  title: [#text(font: "$displayfont$", fallback: false)[$title$]],
$endif$
$if(subtitle)$
  subtitle: [#text(font: "$sansfont$", fallback: false)[$subtitle$]],
$endif$
$if(by-author)$
  // Keep edition/status wording on the front-matter page; PDF Author metadata
  // contains creator names only.
  author: "$for(by-author)$$it.name.literal$$sep$, $endfor$",
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
$endif$

$if(alkahest-pdf-ua)$
$else$
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
$endif$

// Use one restrained body rhythm across Typst and LuaLaTeX. This rule is
// intentionally applied after orange-book so it replaces the package's extra
// paragraph gap while retaining its heading, list, and figure treatments.
#let alkahest-body-style(body) = {
  let theme-ink = brand-color.at("ink", default: rgb("#20262e"))
  let theme-primary = brand-color.at("primary", default: rgb("#334155"))
  let theme-line = brand-color.at("line", default: rgb("#cbd5e1"))
  let theme-mist = brand-color.at("mist", default: rgb("#f1f5f9"))

  // Orange-book places a second folio in the default footer; its running head
  // already provides the single outward folio required by the design contract.
$if(alkahest-pdf-ua)$
  set page(numbering: "1")
$else$
  set page(numbering: none)
$endif$
  // Typst prevents widows and orphans by default. State the nonzero costs
  // explicitly so a future engine or package default cannot weaken the policy.
  set text(
    font: "$mainfont$",
    fallback: false,
    costs: (widow: 100%, orphan: 100%),
  )
  set par(
    justify: true,
    leading: $body-leading$,
    first-line-indent: $paragraph-indent$,
    spacing: $paragraph-spacing$,
  )
  show heading: set text(font: "$sansfont$", fallback: false, fill: theme-primary)
  // Preserve Typst's built-in keep-with-next behavior through later show rules.
  show heading: set block(sticky: true)
  // Quarto/Typst currently carries numbering deeper than number-depth. Keep
  // H4-H6 as local, unnumbered structure to match HTML/EPUB and LuaLaTeX.
  show heading.where(level: 4): set text(fill: theme-ink)
  show heading.where(level: 4): set heading(numbering: none)
  show heading.where(level: 5): set text(fill: theme-ink)
  show heading.where(level: 5): set heading(numbering: none)
  show heading.where(level: 6): set text(fill: theme-ink)
  show heading.where(level: 6): set heading(numbering: none)
  show link: set text(fill: theme-primary)
  show figure.caption: set text(font: "$sansfont$", fallback: false, size: 8.5pt)
  // Quarto emits code-annotation fallbacks as term-list items. Give the term a
  // real column so labels such as "Line 12" cannot collide with their prose.
  show terms.item: item => block(breakable: false, below: 0.35em)[
    #grid(
      columns: (3.5em, 1fr),
      column-gutter: 0.5em,
      text(font: "$sansfont$", fallback: false, weight: "bold", item.term),
      block[
        #set par(first-line-indent: 0em)
        #item.description
      ],
    )
  ]
  show raw.where(block: true): content => block(
    width: 100%,
    fill: theme-mist,
    stroke: (left: 2pt + theme-primary, rest: 0.5pt + theme-line),
    inset: 7pt,
    radius: 2pt,
    content,
  )
  // Quarto's Typst highlighter emits each lexical token as one raw element.
  // Make its grapheme clusters individually breakable so a URL, hash, or other
  // intentionally unbroken value cannot escape a narrow print page.
  show raw.where(block: false): content => {
    if content.text == "\n" {
      linebreak()
    } else {
      for cluster in content.text.clusters() {
        box(text(font: "$monofont$", fallback: false, cluster))
      }
    }
  }
  show math.equation: set text(font: "$mathfont$", fallback: false)
  show raw: set text(font: "$monofont$", fallback: false)
  body
}

#show: alkahest-body-style
