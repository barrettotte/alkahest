-- Load the central JSON companion registry for portable shortcode rendering.
local function project_file(name)
  if quarto.project.directory ~= nil then
    return pandoc.path.join({ quarto.project.directory, name })
  end
  return name
end

local path = project_file("companion.json")
local handle = io.open(path, "r")
if handle == nil then
  error("alkahest companions: cannot read companion.json from the project root")
end
local source = handle:read("*a")
handle:close()

local registry = pandoc.json.decode(source)
if registry == nil or registry.version ~= 1 or registry.items == nil then
  error("alkahest companions: invalid companion.json registry")
end

return registry
