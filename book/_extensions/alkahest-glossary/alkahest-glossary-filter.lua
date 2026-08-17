-- Generate sorted glossary back matter with backend-specific print references.
local registry_path = pandoc.path.join({
  quarto.project.directory,
  "_extensions",
  "alkahest-glossary",
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

local function is_print()
  return quarto.doc.isFormat("latex") or quarto.doc.isFormat("typst")
end

local function glossary_anchor(entry)
  return "glossary-" .. entry.name
end

local function first_use_anchor(entry)
  return "glossary-first-" .. entry.name
end

local function definition_inlines(value)
  local parsed = pandoc.read(value, "markdown")
  if #parsed.blocks ~= 1
      or (parsed.blocks[1].t ~= "Para" and parsed.blocks[1].t ~= "Plain") then
    error("alk-glossary: definitions must contain one inline Markdown paragraph")
  end
  return parsed.blocks[1].content
end

local function forms_inlines(entry)
  local forms = {}
  if entry.plural ~= nil and entry.plural ~= "" then
    table.insert(forms, "plural: " .. entry.plural)
  end
  if entry.acronym_plural ~= nil and entry.acronym_plural ~= "" then
    table.insert(forms, "acronym plural: " .. entry.acronym_plural)
  end
  if #forms == 0 then
    return nil
  end
  return pandoc.Span(
    { pandoc.Str(table.concat(forms, "; ")) },
    pandoc.Attr("", { "glossary-entry-forms" })
  )
end

local function page_reference_inlines(entry)
  if not is_print() then
    return nil
  end

  local page_number
  if quarto.doc.isFormat("latex") then
    page_number = pandoc.RawInline(
      "latex",
      "\\pageref{" .. first_use_anchor(entry) .. "}"
    )
  else
    page_number = pandoc.RawInline(
      "typst",
      "#context counter(page).at(<" .. first_use_anchor(entry) .. ">).first()"
    )
  end
  return pandoc.Span(
    {
      pandoc.Emph({ pandoc.Str("First use: p."), pandoc.Space(), page_number }),
    },
    pandoc.Attr("", { "glossary-page-reference" })
  )
end

local function glossary_headword(entry)
  local display = entry.term
  if entry.acronym ~= nil and entry.acronym ~= "" then
    display = display .. " (" .. entry.acronym .. ")"
  end
  return pandoc.Span(
    { pandoc.Str(display) },
    pandoc.Attr(glossary_anchor(entry), { "glossary-entry-name" }, {
      ["data-glossary-id"] = entry.name,
    })
  )
end

local function generated_glossary()
  local blocks = {}
  for _, entry in ipairs(registry.entries) do
    local content = {}
    if quarto.doc.isFormat("latex") then
      table.insert(content, pandoc.RawInline("latex", "\\noindent "))
    end
    table.insert(content, pandoc.Strong({ glossary_headword(entry) }))
    table.insert(content, pandoc.LineBreak())
    for _, inline in ipairs(definition_inlines(entry.definition)) do
      table.insert(content, inline)
    end
    local forms = forms_inlines(entry)
    if forms ~= nil then
      table.insert(content, pandoc.LineBreak())
      table.insert(content, forms)
    end
    local page_reference = page_reference_inlines(entry)
    if page_reference ~= nil then
      table.insert(content, pandoc.LineBreak())
      table.insert(content, page_reference)
    end
    local entry_blocks = { pandoc.Para(content) }
    if quarto.doc.isFormat("latex") then
      table.insert(entry_blocks, pandoc.RawBlock("latex", "\\smallskip"))
    elseif quarto.doc.isFormat("typst") then
      table.insert(entry_blocks, pandoc.RawBlock("typst", "#v(0.35em)"))
    end
    table.insert(blocks, pandoc.Div(
      entry_blocks,
    pandoc.Attr("", { "glossary-entry" }, {
        ["aria-labelledby"] = glossary_anchor(entry),
        lang = registry.language,
        role = "definition",
      })
    ))
  end
  return pandoc.Div(
    blocks,
    pandoc.Attr("", { "generated-glossary" }, {
      ["data-glossary-count"] = tostring(#registry.entries),
      lang = registry.language,
    })
  )
end

return {
  Div = function(div)
    if has_class(div, "alkahest-glossary-placeholder") then
      return generated_glossary()
    end
  end,
}
