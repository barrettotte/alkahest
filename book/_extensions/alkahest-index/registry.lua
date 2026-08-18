-- Load index identity, hierarchy, redirects, and declared marker locations.
local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local index_path = "index.yml"
if quarto.project.directory ~= nil then
  index_path = pandoc.path.join({ quarto.project.directory, index_path })
end
local handle = io.open(index_path, "r")
if handle == nil then
  error("alkahest index: cannot read index.yml from the project root")
end
local source = handle:read("*a")
handle:close()

local document = pandoc.read("---\n" .. source .. "\n---\n", "markdown")
local raw_entries = document.meta.entries
if raw_entries == nil then
  error("alkahest index: index.yml has no entries mapping")
end

local function string_list(values)
  local result = {}
  for _, value in ipairs(values or {}) do
    table.insert(result, value_as_string(value))
  end
  return result
end

local function parse_locator(value)
  local source_path, marker = value:match("^([^#]+)#([^#]+)$")
  if source_path == nil then
    error("alkahest index: malformed declared locator " .. value)
  end
  return { source = source_path, marker = marker }
end

local entries = {}
local canonical = {}
for name, raw_entry in pairs(raw_entries) do
  local entry = {
    name = name,
    term = value_as_string(raw_entry.term),
    kind = value_as_string(raw_entry.kind),
    sort = value_as_string(raw_entry.sort),
    parent = value_as_string(raw_entry.parent),
    see = value_as_string(raw_entry.see),
    aliases = string_list(raw_entry.aliases),
    see_also = string_list(raw_entry["see-also"]),
    locations = {},
    ranges = {},
    children = {},
  }
  for _, value in ipairs(string_list(raw_entry.locations)) do
    table.insert(entry.locations, parse_locator(value))
  end
  for _, value in ipairs(string_list(raw_entry.ranges)) do
    table.insert(entry.ranges, parse_locator(value))
  end
  table.insert(entries, entry)
  canonical[name] = entry
end

local lookup = {}
for _, entry in ipairs(entries) do
  lookup[entry.name] = entry
  for _, alias in ipairs(entry.aliases) do
    if lookup[alias] ~= nil then
      error("alkahest index: duplicate index name or alias " .. alias)
    end
    lookup[alias] = entry
  end
end

local roots = { subject = {}, person = {} }
for _, entry in ipairs(entries) do
  if entry.parent ~= nil and entry.parent ~= "" then
    local parent = canonical[entry.parent]
    if parent == nil then
      error("alkahest index: unknown parent " .. entry.parent)
    end
    table.insert(parent.children, entry)
  else
    table.insert(roots[entry.kind], entry)
  end
end

local function sort_entries(values)
  table.sort(values, function(left, right)
    local left_sort = pandoc.text.lower(left.sort or left.term)
    local right_sort = pandoc.text.lower(right.sort or right.term)
    if left_sort == right_sort then
      return left.name < right.name
    end
    return left_sort < right_sort
  end)
  for _, entry in ipairs(values) do
    sort_entries(entry.children)
  end
end
sort_entries(roots.subject)
sort_entries(roots.person)

return {
  canonical = canonical,
  entries = entries,
  language = value_as_string(document.meta.lang),
  lookup = lookup,
  roots = roots,
}
