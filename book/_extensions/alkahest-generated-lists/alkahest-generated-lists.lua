-- Generate configured reference, acronym, symbol, and nomenclature lists.
local registry_path = pandoc.path.join({
  quarto.project.directory,
  "_extensions",
  "alkahest-generated-lists",
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

local function markdown_inlines(value)
  local parsed = pandoc.read(value, "markdown")
  if #parsed.blocks ~= 1
      or (parsed.blocks[1].t ~= "Para" and parsed.blocks[1].t ~= "Plain") then
    error("alkahest generated lists: entry text must be one inline Markdown paragraph")
  end
  return parsed.blocks[1].content
end

local function append_all(target, values)
  for _, value in ipairs(values) do
    table.insert(target, value)
  end
end

local function separator(inlines)
  table.insert(inlines, pandoc.Space())
  table.insert(inlines, pandoc.Str("—"))
  table.insert(inlines, pandoc.Space())
end

local function crossref_inlines(identifier)
  return markdown_inlines("@" .. identifier)
end

local function crossref_entry(list, entry)
  local content = {}
  append_all(content, crossref_inlines(entry.id))
  separator(content)
  append_all(content, markdown_inlines(entry.title))
  return pandoc.Div(
    { pandoc.Para(content) },
    pandoc.Attr("", { "generated-list-entry", "generated-list-crossref-entry" }, {
      ["data-entry-id"] = entry.id,
      ["data-list-name"] = list.name,
    })
  )
end

local function acronym_entry(list, entry)
  local acronym = pandoc.Link(
    { pandoc.Str(entry.acronym) },
    "glossary-backmatter.qmd#glossary-" .. entry.id,
    entry.term,
    pandoc.Attr("", { "generated-list-acronym-link" })
  )
  local content = { pandoc.Strong({ acronym }) }
  separator(content)
  table.insert(content, pandoc.Str(entry.term))
  return pandoc.Div(
    { pandoc.Para(content) },
    pandoc.Attr("", { "generated-list-entry", "generated-list-acronym-entry" }, {
      ["data-entry-id"] = entry.id,
      ["data-list-name"] = list.name,
    })
  )
end

local function term_entry(list, entry)
  local content = {
    pandoc.Strong({ pandoc.Math("InlineMath", entry.display) }),
  }
  separator(content)
  append_all(content, markdown_inlines(entry.meaning))
  if entry.target ~= nil and entry.target ~= "" then
    table.insert(content, pandoc.Space())
    table.insert(content, pandoc.Str("("))
    append_all(content, crossref_inlines(entry.target))
    table.insert(content, pandoc.Str(")"))
  end
  return pandoc.Div(
    { pandoc.Para(content) },
    pandoc.Attr("", { "generated-list-entry", "generated-list-term-entry" }, {
      ["data-entry-id"] = entry.id,
      ["data-list-name"] = list.name,
    })
  )
end

local function list_group(list)
  local blocks = {
    pandoc.Header(2, list.title, pandoc.Attr("generated-list-" .. list.name)),
  }
  for _, entry in ipairs(list.entries) do
    if entry.entry_type == "crossref" then
      table.insert(blocks, crossref_entry(list, entry))
    elseif entry.entry_type == "acronym" then
      table.insert(blocks, acronym_entry(list, entry))
    else
      table.insert(blocks, term_entry(list, entry))
    end
  end
  return pandoc.Div(
    blocks,
    pandoc.Attr("", { "generated-list-group", "generated-list-source-" .. list.source }, {
      ["data-entry-count"] = tostring(#list.entries),
      ["data-list-name"] = list.name,
    })
  )
end

local function generated_lists()
  local blocks = {}
  for _, list in ipairs(registry.order) do
    if list.enabled and #list.entries > 0 then
      table.insert(blocks, list_group(list))
    end
  end
  return pandoc.Div(
    blocks,
    pandoc.Attr("", { "generated-reference-lists" }, {
      ["data-configured-list-count"] = tostring(registry.configured_count),
      ["data-generated-list-count"] = tostring(#blocks),
      lang = registry.language,
    })
  )
end

return {
  Div = function(div)
    if has_class(div, "alkahest-generated-lists-placeholder") then
      return generated_lists()
    end
  end,
}
