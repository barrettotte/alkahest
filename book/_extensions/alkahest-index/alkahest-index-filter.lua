-- Generate linked reflowable indexes and page-resolved print indexes.
local registry_path = pandoc.path.join({
  quarto.project.directory,
  "_extensions",
  "alkahest-index",
  "registry.lua",
})
local registry = dofile(registry_path)

local function has_class(element, expected)
  for _, class_name in ipairs(element.classes) do
    if class_name == expected then
      return true
    end
  end
  return false
end

local function is_linked_reflowable()
  return quarto.doc.isFormat("html") or quarto.doc.isFormat("epub")
end

local function entry_anchor(entry)
  return "index-entry-" .. entry.name
end

local function marker_anchor(entry, marker)
  return "index-ref-" .. entry.name .. "-" .. marker
end

local function range_anchor(entry, marker, edge)
  return "index-range-" .. entry.name .. "-" .. marker .. "-" .. edge
end

local function relation_link(target)
  local related = registry.canonical[target]
  return pandoc.Link(
    { pandoc.Str(related.term) },
    "#" .. entry_anchor(related),
    related.term,
    pandoc.Attr("", { "index-relation-link" })
  )
end

local function typst_page(anchor)
  return pandoc.RawInline(
    "typst",
    "#link(<" .. anchor .. ">)[#context counter(page).at(<"
      .. anchor .. ">).first()]"
  )
end

local function locator_inlines(entry)
  local result = {}
  local ordinal = 0
  local function separator()
    if #result > 0 then
      table.insert(result, pandoc.Str(","))
      table.insert(result, pandoc.Space())
    end
  end

  for _, locator in ipairs(entry.locations) do
    ordinal = ordinal + 1
    separator()
    local anchor = marker_anchor(entry, locator.marker)
    if is_linked_reflowable() then
      table.insert(result, pandoc.Link(
        { pandoc.Str(tostring(ordinal)) },
        locator.source .. "#" .. anchor,
        entry.term .. " reference " .. ordinal,
        pandoc.Attr("", { "index-locator-link" }, {
          ["aria-label"] = entry.term .. " reference " .. ordinal,
        })
      ))
    elseif quarto.doc.isFormat("typst") then
      table.insert(result, typst_page(anchor))
    else
      table.insert(result, pandoc.Code(locator.source .. "#" .. locator.marker))
    end
  end

  for _, locator in ipairs(entry.ranges) do
    ordinal = ordinal + 1
    separator()
    local start_anchor = range_anchor(entry, locator.marker, "start")
    local end_anchor = range_anchor(entry, locator.marker, "end")
    if is_linked_reflowable() then
      table.insert(result, pandoc.Link(
        { pandoc.Str(tostring(ordinal)) },
        locator.source .. "#" .. start_anchor,
        entry.term .. " range " .. ordinal .. " start",
        pandoc.Attr("", { "index-range-link", "index-range-start" })
      ))
      table.insert(result, pandoc.Str("–"))
      table.insert(result, pandoc.Link(
        { pandoc.Str(tostring(ordinal)) },
        locator.source .. "#" .. end_anchor,
        entry.term .. " range " .. ordinal .. " end",
        pandoc.Attr("", { "index-range-link", "index-range-end" })
      ))
    elseif quarto.doc.isFormat("typst") then
      table.insert(result, typst_page(start_anchor))
      table.insert(result, pandoc.Str("–"))
      table.insert(result, typst_page(end_anchor))
    else
      table.insert(result, pandoc.Code(locator.source .. "#" .. locator.marker))
    end
  end
  return result
end

local function entry_blocks(entry, depth)
  local line = {}
  if quarto.doc.isFormat("typst") and depth > 0 then
    table.insert(line, pandoc.RawInline("typst", "#h(" .. depth .. "em)"))
  end
  table.insert(line, pandoc.Strong({
    pandoc.Span(
      { pandoc.Str(entry.term) },
      pandoc.Attr(entry_anchor(entry), { "index-entry-term" }, {
        ["data-index-id"] = entry.name,
        ["data-index-kind"] = entry.kind,
      })
    ),
  }))

  local locators = locator_inlines(entry)
  if #locators > 0 then
    table.insert(line, pandoc.Str(","))
    table.insert(line, pandoc.Space())
    for _, inline in ipairs(locators) do
      table.insert(line, inline)
    end
  end
  if entry.see ~= nil and entry.see ~= "" then
    table.insert(line, pandoc.Str(","))
    table.insert(line, pandoc.Space())
    table.insert(line, pandoc.Emph({ pandoc.Str("see") }))
    table.insert(line, pandoc.Space())
    table.insert(line, relation_link(entry.see))
  elseif #entry.see_also > 0 then
    table.insert(line, pandoc.Str(";"))
    table.insert(line, pandoc.Space())
    table.insert(line, pandoc.Emph({ pandoc.Str("see also") }))
    table.insert(line, pandoc.Space())
    for index, target in ipairs(entry.see_also) do
      if index > 1 then
        table.insert(line, pandoc.Str(","))
        table.insert(line, pandoc.Space())
      end
      table.insert(line, relation_link(target))
    end
  end

  local blocks = {
    pandoc.Div(
      { pandoc.Para(line) },
      pandoc.Attr("", {
        "index-entry",
        "index-entry-depth-" .. depth,
        "index-entry-kind-" .. entry.kind,
      })
    ),
  }
  for _, child in ipairs(entry.children) do
    for _, block in ipairs(entry_blocks(child, depth + 1)) do
      table.insert(blocks, block)
    end
  end
  return blocks
end

local function index_group(title, kind, entries)
  local blocks = { pandoc.Header(2, title, pandoc.Attr("index-" .. kind)) }
  for _, entry in ipairs(entries) do
    for _, block in ipairs(entry_blocks(entry, 0)) do
      table.insert(blocks, block)
    end
  end
  return pandoc.Div(
    blocks,
    pandoc.Attr("", { "generated-index-group", "index-kind-" .. kind }, {
      ["data-index-kind"] = kind,
      ["data-index-root-count"] = tostring(#entries),
    })
  )
end

local function generated_indexes()
  return pandoc.Div(
    {
      index_group("Subject index", "subject", registry.roots.subject),
      index_group("Name index", "person", registry.roots.person),
    },
    pandoc.Attr("", { "generated-indexes" }, {
      ["data-index-entry-count"] = tostring(#registry.entries),
      lang = registry.language,
    })
  )
end

return {
  Div = function(div)
    if has_class(div, "alkahest-index-placeholder") then
      return generated_indexes()
    end
  end,
}
