-- Place one semantic note source as native notes, sidenotes, or linked endnotes.
local registry_path = pandoc.path.join({
  quarto.project.directory,
  "_extensions",
  "alkahest-notes",
  "registry.lua",
})
local registry = dofile(registry_path)
local placement = "footnotes"
local occurrences = {}

local valid_placements = {
  footnotes = true,
  sidenotes = true,
  ["chapter-endnotes"] = true,
  ["book-endnotes"] = true,
}

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function reference_anchor(name, occurrence)
  return "note-ref-" .. name .. "-" .. occurrence
end

local function book_note_anchor(name)
  return "book-note-" .. name
end

local function book_note_reference(entry, occurrence)
  local anchor = reference_anchor(entry.name, occurrence)
  local link = pandoc.Link(
    { pandoc.Str(tostring(entry.index)) },
    "glossary-backmatter.qmd#" .. book_note_anchor(entry.name),
    "Book note " .. entry.index,
    pandoc.Attr("", { "book-endnote-reference-link" }, {
      ["aria-label"] = "Book note " .. entry.index,
      ["data-note-id"] = entry.name,
    })
  )
  return pandoc.Span(
    { pandoc.Superscript({ link }) },
    pandoc.Attr(anchor, { "book-endnote-reference" }, {
      ["data-note-id"] = entry.name,
      ["data-note-number"] = tostring(entry.index),
      ["data-note-occurrence"] = tostring(occurrence),
    })
  )
end

local function back_links(entry)
  local inlines = { pandoc.Str("Back to") }
  local count = entry.references
  for occurrence = 1, count do
    table.insert(inlines, pandoc.Space())
    table.insert(inlines, pandoc.Link(
      { pandoc.Str("reference " .. occurrence) },
      entry.source .. "#" .. reference_anchor(entry.name, occurrence),
      "Back to reference " .. occurrence,
      pandoc.Attr("", { "book-endnote-backlink" }, {
        ["aria-label"] = "Back to note " .. entry.index
          .. " reference " .. occurrence,
      })
    ))
    if occurrence < count then
      table.insert(inlines, pandoc.Str(","))
    end
  end
  table.insert(inlines, pandoc.Str("."))
  return pandoc.Para(inlines)
end

local function generated_book_notes()
  local items = {}
  for _, entry in ipairs(registry.entries) do
    local blocks = registry.content_for(entry):clone()
    table.insert(blocks, back_links(entry))
    table.insert(items, {
      pandoc.Div(
        blocks,
        pandoc.Attr(book_note_anchor(entry.name), { "book-endnote" }, {
          ["data-note-id"] = entry.name,
          ["data-note-number"] = tostring(entry.index),
          ["data-note-backlinks"] = tostring(entry.references),
        })
      ),
    })
  end
  return pandoc.Div(
    {
      pandoc.Header(2, "Notes", pandoc.Attr("sec-book-notes")),
      pandoc.OrderedList(items),
    },
    pandoc.Attr("", { "generated-book-notes" }, {
      ["data-note-count"] = tostring(#registry.entries),
    })
  )
end

return {
  {
    Meta = function(meta)
      if meta.alkahest ~= nil and meta.alkahest.notes ~= nil then
        local configured = value_as_string(meta.alkahest.notes.placement)
        if configured ~= nil and configured ~= "" then
          placement = configured
        end
      end
      if not valid_placements[placement] then
        error("alkahest notes: unsupported placement " .. placement)
      end
    end,
  },
  {
    Note = function(note)
      local first = note.content[1]
      if first == nil or (first.t ~= "Para" and first.t ~= "Plain") then
        return note
      end
      local marker = first.content[1]
      if marker == nil or marker.t ~= "Span"
          or not marker.classes:includes("alkahest-note") then
        return note
      end
      local name = marker.identifier:gsub("^note%-", "")
      local provisional = (occurrences[name] or 0) + 1
      local entry = registry.identify_note(note, provisional)
      occurrences[entry.name] = provisional
      if placement == "book-endnotes" then
        return book_note_reference(entry, provisional)
      end
      return note
    end,
    Div = function(div)
      if div.classes:includes("alkahest-book-notes-placeholder") then
        if placement == "book-endnotes" then
          return generated_book_notes()
        end
        return {}
      end
    end,
  },
}
