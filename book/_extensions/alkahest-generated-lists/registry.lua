-- Load generated-list configuration, curated cross-references, and terminology.
local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function value_as_bool(value, default)
  if value == nil then
    return default
  end
  return value_as_string(value) == "true"
end

local function project_file(name)
  if quarto.project.directory ~= nil then
    return pandoc.path.join({ quarto.project.directory, name })
  end
  return name
end

local function read_metadata(name)
  local path = project_file(name)
  local handle = io.open(path, "r")
  if handle == nil then
    error("alkahest generated lists: cannot read " .. name .. " from the project root")
  end
  local source = handle:read("*a")
  handle:close()
  return pandoc.read("---\n" .. source .. "\n---\n", "markdown").meta
end

local metadata = read_metadata("generated-lists.yml")
local raw_lists = metadata.lists
if raw_lists == nil then
  error("alkahest generated lists: generated-lists.yml has no lists mapping")
end

local lists = {}
for name, raw_list in pairs(raw_lists) do
  lists[name] = {
    name = name,
    title = value_as_string(raw_list.title),
    source = value_as_string(raw_list.source),
    prefix = value_as_string(raw_list.prefix),
    enabled = value_as_bool(raw_list.enabled, true),
    entries = {},
  }
end

local order = {}
for _, raw_name in ipairs(metadata.order or {}) do
  local name = value_as_string(raw_name)
  local list = lists[name]
  if list == nil then
    error("alkahest generated lists: unknown list in order: " .. name)
  end
  table.insert(order, list)
end

for _, raw_object in ipairs(metadata.objects or {}) do
  local id = value_as_string(raw_object.id)
  local prefix = id and id:match("^([a-z][a-z0-9]*)%-") or nil
  local owner = nil
  for _, list in pairs(lists) do
    if list.source == "crossref" and list.prefix == prefix then
      owner = list
      break
    end
  end
  if owner == nil then
    error("alkahest generated lists: no cross-reference list owns " .. tostring(id))
  end
  table.insert(owner.entries, {
    id = id,
    title = value_as_string(raw_object.title),
    entry_type = "crossref",
  })
end

for name, raw_term in pairs(metadata.terms or {}) do
  local list_name = value_as_string(raw_term.list)
  local owner = lists[list_name]
  if owner == nil or owner.source ~= "terms" then
    error("alkahest generated lists: term " .. name .. " has no terms list")
  end
  table.insert(owner.entries, {
    id = name,
    display = value_as_string(raw_term.display),
    meaning = value_as_string(raw_term.meaning),
    sort = value_as_string(raw_term.sort),
    target = value_as_string(raw_term.target),
    entry_type = "term",
  })
end

for _, list in pairs(lists) do
  if list.source == "terms" then
    table.sort(list.entries, function(left, right)
      local left_sort = pandoc.text.lower(left.sort or left.meaning)
      local right_sort = pandoc.text.lower(right.sort or right.meaning)
      if left_sort == right_sort then
        return left.id < right.id
      end
      return left_sort < right_sort
    end)
  end
end

local glossary = read_metadata("glossary.yml")
for _, list in pairs(lists) do
  if list.source == "glossary-acronyms" then
    for name, raw_term in pairs(glossary.terms or {}) do
      local acronym = value_as_string(raw_term.acronym)
      if acronym ~= nil and acronym ~= "" then
        table.insert(list.entries, {
          id = name,
          acronym = acronym,
          term = value_as_string(raw_term.term),
          entry_type = "acronym",
        })
      end
    end
    table.sort(list.entries, function(left, right)
      local left_sort = pandoc.text.lower(left.acronym)
      local right_sort = pandoc.text.lower(right.acronym)
      if left_sort == right_sort then
        return left.id < right.id
      end
      return left_sort < right_sort
    end)
  end
end

return {
  configured_count = #order,
  language = value_as_string(metadata.lang),
  lists = lists,
  order = order,
}

