-- Load semantic note identity, source, order, and repeat policy once per render.
local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local notes_path = "notes.yml"
if quarto.project.directory ~= nil then
  notes_path = pandoc.path.join({ quarto.project.directory, notes_path })
end
local handle = io.open(notes_path, "r")
if handle == nil then
  error("alkahest notes: cannot read notes.yml from the project root")
end
local source = handle:read("*a")
handle:close()

local document = pandoc.read("---\n" .. source .. "\n---\n", "markdown")
local raw_notes = document.meta.notes
local raw_order = document.meta.order
if raw_notes == nil or raw_order == nil then
  error("alkahest notes: notes.yml needs notes and order fields")
end

local entries = {}
local lookup = {}
for index, raw_name in ipairs(raw_order) do
  local name = value_as_string(raw_name)
  local raw_entry = raw_notes[name]
  if raw_entry == nil then
    error("alkahest notes: order references unknown note " .. name)
  end
  local entry = {
    index = index,
    name = name,
    source = value_as_string(raw_entry.source),
    repeat_policy = value_as_string(raw_entry["repeat"]),
    references = tonumber(value_as_string(raw_entry.references)),
  }
  table.insert(entries, entry)
  lookup[name] = entry
end

local function has_class(element, expected)
  for _, class_name in ipairs(element.classes) do
    if class_name == expected then
      return true
    end
  end
  return false
end

local function identify_note(note, occurrence)
  local first_block = note.content[1]
  if first_block == nil
      or (first_block.t ~= "Para" and first_block.t ~= "Plain") then
    error("alkahest notes: semantic note must begin with a paragraph")
  end
  local marker = first_block.content[1]
  if marker == nil or marker.t ~= "Span" or not has_class(marker, "alkahest-note") then
    error("alkahest notes: note definition lacks its leading .alkahest-note marker")
  end
  local name = marker.identifier:gsub("^note%-", "")
  local entry = lookup[name]
  if entry == nil or marker.identifier ~= "note-" .. name then
    error("alkahest notes: unknown or malformed note marker " .. marker.identifier)
  end
  marker.identifier = ""
  marker.classes = { "semantic-note-content" }
  marker.attributes["data-note-id"] = name
  if occurrence ~= nil then
    marker.attributes["data-note-occurrence"] = tostring(occurrence)
  end
  return entry, note.content
end

local content_cache = {}
local function content_for(entry)
  if content_cache[entry.name] ~= nil then
    return content_cache[entry.name]
  end
  local source_path = entry.source
  if quarto.project.directory ~= nil then
    source_path = pandoc.path.join({ quarto.project.directory, source_path })
  end
  local source_handle = io.open(source_path, "r")
  if source_handle == nil then
    error("alkahest notes: cannot read note source " .. entry.source)
  end
  local manuscript = source_handle:read("*a")
  source_handle:close()
  local parsed = pandoc.read(manuscript, "markdown")
  parsed:walk({
    Note = function(note)
      local ok, found_entry, content = pcall(identify_note, note, nil)
      if ok and found_entry.name == entry.name and content_cache[entry.name] == nil then
        content_cache[entry.name] = content
      end
      return note
    end,
  })
  if content_cache[entry.name] == nil then
    error("alkahest notes: cannot find note " .. entry.name .. " in " .. entry.source)
  end
  return content_cache[entry.name]
end

return {
  content_for = content_for,
  entries = entries,
  identify_note = identify_note,
  lookup = lookup,
}
