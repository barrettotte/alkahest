-- Load the central rich-media registry for portable shortcode rendering.
local function project_file(name)
  if quarto.project.directory ~= nil then
    return pandoc.path.join({ quarto.project.directory, name })
  end
  return name
end

local function read_file(name)
  local handle = io.open(project_file(name), "r")
  if handle == nil then
    error("alkahest media: cannot read " .. name .. " from the project root")
  end
  local source = handle:read("*a")
  handle:close()
  return source
end

local registry = pandoc.json.decode(read_file("media.json"))
if registry == nil or registry.version ~= 1 or registry.items == nil then
  error("alkahest media: invalid media.json registry")
end

registry.read_file = read_file
return registry
