-- Load the book glossary once for both shortcode and document-filter stages.
local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local glossary_path = "glossary.yml"
if quarto.project.directory ~= nil then
  glossary_path = pandoc.path.join({ quarto.project.directory, glossary_path })
end
local handle = io.open(glossary_path, "r")
if handle == nil then
  error("alkahest glossary: cannot read glossary.yml from the project root")
end
local source = handle:read("*a")
handle:close()

local document = pandoc.read("---\n" .. source .. "\n---\n", "markdown")
local raw_terms = document.meta.terms
if raw_terms == nil then
  error("alkahest glossary: glossary.yml has no terms mapping")
end
local language = value_as_string(document.meta.lang)
if language == nil or language == "" then
  error("alkahest glossary: glossary.yml has no language tag")
end

local entries = {}
local lookup = {}
for name, raw_entry in pairs(raw_terms) do
  local entry = {
    name = name,
    term = value_as_string(raw_entry.term),
    plural = value_as_string(raw_entry.plural),
    acronym = value_as_string(raw_entry.acronym),
    acronym_plural = value_as_string(raw_entry["acronym-plural"]),
    definition = value_as_string(raw_entry.definition),
  }
  table.insert(entries, entry)
  lookup[name] = entry
  for _, raw_alias in ipairs(raw_entry.aliases or {}) do
    local alias = value_as_string(raw_alias)
    if lookup[alias] ~= nil then
      error("alkahest glossary: duplicate glossary name or alias: " .. alias)
    end
    lookup[alias] = entry
  end
end

table.sort(entries, function(left, right)
  local left_term = string.lower(left.term)
  local right_term = string.lower(right.term)
  if left_term == right_term then
    return left.name < right.name
  end
  return left_term < right_term
end)

return {
  entries = entries,
  language = language,
  lookup = lookup,
}
