// Self-contained Typst book layout used by Quarto's generated document.
#set text(font: "$mainfont$", fallback: false)

#let alkahest-part-counter = counter("alkahest-part-counter")

// Quarto's book filter emits these function names for divisions.
#let part(title) = context {
  let previous-heading = counter(heading).get()
  pagebreak()
  // Counter updates are location-based; get() at this location includes the
  // step below, yielding one for the first part and two for the second.
  let part-number = alkahest-part-counter.get().first()
  alkahest-part-counter.step()
  set page(header: none, footer: none, numbering: none)
  align(center + horizon)[
    #text(font: "$displayfont$", fallback: false, size: 28pt)[
      Part #numbering("I", part-number)
    ]
    #v(1em)
    #text(font: "$displayfont$", fallback: false, size: 22pt)[#title]
  ]
  counter(heading).update(previous-heading)
  pagebreak()
}

#let appendices(title, doc, hide-parent: false) = {
  pagebreak()
  counter(heading).update(0)
  set heading(numbering: (..numbers) => numbering("A.1", ..numbers.pos()))
  set figure(numbering: number => numbering("A.1", counter(heading).get().first(), number))
  set math.equation(numbering: number => numbering("(A.1)", counter(heading).get().first(), number))
  doc
}

#let alkahest-book(body) = {
  set document(
    title: "$title$",
    author: "$for(by-author)$$it.name.literal$$sep$, $endfor$",
$if(subject)$
    description: "$subject$",
$endif$
$if(keywords)$
    keywords: ($for(keywords)$"$keywords$",$endfor$),
$endif$
  )
  set text(
    font: "$mainfont$",
    fallback: false,
    size: $body-font-size$,
    lang: "$lang$",
  )
  set page(
    width: $trim-width$,
    height: $trim-height$,
    margin: (
      inside: $margin-geometry.inner.far$,
      outside: $margin-geometry.outer.far$,
      top: $margin.top$,
      bottom: $margin.bottom$,
    ),
    numbering: "1",
  )
  set heading(numbering: (..numbers) => numbering("1.1", ..numbers.pos()))
  set figure(numbering: number => numbering("1.1", counter(heading).get().first(), number))
  set math.equation(numbering: number => numbering("(1.1)", counter(heading).get().first(), number))

  page(header: none, footer: none, numbering: none)[
    #align(center + horizon, block(width: 86%)[
      #set par(justify: false)
      #text(font: "$displayfont$", fallback: false, size: 30pt, weight: "bold")[$title$]
$if(subtitle)$
      #v(1.2em)
      #text(font: "$sansfont$", fallback: false, size: 16pt)[$subtitle$]
$endif$
      #v(2em)
      #text(font: "$sansfont$", fallback: false)[$for(by-author)$$it.name.literal$$sep$, $endfor$]
    ])
  ]
$if(dedication)$
  page(header: none, footer: none, numbering: none)[
    #place(center + horizon, text(font: "$displayfont$", fallback: false, size: 18pt)[$dedication$])
  ]
$endif$
  pagebreak()
  outline(title: [Contents], depth: $toc-depth$)
  pagebreak()
  body
}

#show: alkahest-book

#let alkahest-body-style(body) = {
  let ink = rgb("#20262e")
  let primary = rgb("#334155")
  let line = rgb("#cbd5e1")
  let mist = rgb("#f1f5f9")

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
  show heading: set text(font: "$sansfont$", fallback: false, fill: primary)
  show heading: set block(sticky: true)
  show heading.where(level: 4): set text(fill: ink)
  show heading.where(level: 4): set heading(numbering: none)
  show heading.where(level: 5): set text(fill: ink)
  show heading.where(level: 5): set heading(numbering: none)
  show heading.where(level: 6): set text(fill: ink)
  show heading.where(level: 6): set heading(numbering: none)
  show link: set text(fill: primary)
  show figure.caption: set text(font: "$sansfont$", fallback: false, size: 8.5pt)
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
    fill: mist,
    stroke: (left: 2pt + primary, rest: 0.5pt + line),
    inset: 7pt,
    radius: 2pt,
    content,
  )
  // Break long highlighted tokens at grapheme boundaries inside narrow pages.
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
