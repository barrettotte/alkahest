-- Expand glossary term shortcodes and mark where generated back matter belongs.
local registry = require("./registry")
local lookup = registry.lookup

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local valid_forms = {
  term = true,
  plural = true,
  acronym = true,
  ["acronym-plural"] = true,
  first = true,
  ["first-plural"] = true,
}
local valid_cases = {
  ["as-written"] = true,
  sentence = true,
}

local function is_reflowable()
  return quarto.doc.isFormat("html") or quarto.doc.isFormat("epub")
end

local function glossary_anchor(entry)
  return "glossary-" .. entry.name
end

local function first_use_anchor(entry)
  return "glossary-first-" .. entry.name
end

local function glossary_target(entry)
  return "glossary-backmatter.qmd#" .. glossary_anchor(entry)
end

local function display_for(entry, form)
  if form == "term" then
    return entry.term
  elseif form == "plural" then
    return entry.plural
  elseif form == "acronym" then
    return entry.acronym
  elseif form == "acronym-plural" then
    return entry.acronym_plural
  elseif form == "first" then
    if entry.acronym ~= nil and entry.acronym ~= "" then
      return entry.term .. " (" .. entry.acronym .. ")"
    end
    return entry.term
  elseif form == "first-plural" then
    if entry.plural == nil or entry.plural == "" then
      return nil
    end
    if entry.acronym_plural ~= nil and entry.acronym_plural ~= "" then
      return entry.plural .. " (" .. entry.acronym_plural .. ")"
    end
    return entry.plural
  end
end

local function sentence_case(value)
  if value == "" then
    return value
  end
  return pandoc.text.upper(pandoc.text.sub(value, 1, 1))
    .. pandoc.text.sub(value, 2)
end

return {
  ["alk-term"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-term: shortcodes are not allowed inside code, attributes, or URLs")
    end

    local requested_name = value_as_string(args[1])
    if requested_name == nil or requested_name == "" then
      error("alk-term: expected a glossary name such as central-processing-unit")
    end
    if args[2] ~= nil then
      error("alk-term: unexpected positional argument after " .. requested_name)
    end

    local entry = lookup[requested_name]
    if entry == nil then
      error("alk-term: unknown glossary name or alias: " .. requested_name)
    end
    for key, _value in pairs(kwargs) do
      if key ~= "form" and key ~= "case" and key ~= "link" then
        error("alk-term: unknown named argument: " .. key)
      end
    end

    local form = value_as_string(kwargs.form)
    if form == nil or form == "" then
      form = "term"
    end
    if not valid_forms[form] then
      error("alk-term: unknown form for " .. requested_name .. ": " .. form)
    end
    local text_case = value_as_string(kwargs["case"])
    if text_case == nil or text_case == "" then
      text_case = "as-written"
    end
    if not valid_cases[text_case] then
      error("alk-term: unknown case for " .. requested_name .. ": " .. text_case)
    end
    local link = value_as_string(kwargs.link)
    if link == nil or link == "" then
      link = "true"
    end
    if link ~= "true" and link ~= "false" then
      error("alk-term: link for " .. requested_name .. " must be true or false")
    end
    local display = display_for(entry, form)
    if display == nil or display == "" then
      error("alk-term: form " .. form .. " is unavailable for " .. entry.name)
    end
    if text_case == "sentence" then
      display = sentence_case(display)
    end

    local identifier = ""
    local content = { pandoc.Str(display) }
    if form == "first" or form == "first-plural" then
      identifier = first_use_anchor(entry)
      if quarto.doc.isFormat("latex") then
        table.insert(content, 1, pandoc.RawInline(
          "latex",
          "\\label{" .. identifier .. "}"
        ))
      end
    end
    local reference = pandoc.Span(
      content,
      pandoc.Attr(identifier, { "glossary-term" }, {
        ["data-glossary-case"] = text_case,
        ["data-glossary-id"] = entry.name,
        ["data-glossary-form"] = form,
        ["data-glossary-link"] = link,
        lang = registry.language,
      })
    )
    if is_reflowable() and link == "true" then
      return pandoc.Link(
        { reference },
        glossary_target(entry),
        entry.definition,
        pandoc.Attr("", { "glossary-link" })
      )
    end
    return reference
  end,
}
