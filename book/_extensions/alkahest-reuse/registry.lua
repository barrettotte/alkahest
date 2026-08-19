-- Load the explicit reusable-content registry from the project root.
local function project_file(name)
  if quarto.project.directory ~= nil then
    return pandoc.path.join({ quarto.project.directory, name })
  end
  return name
end

local path = project_file("reusable-content.json")
local handle = io.open(path, "r")
if handle == nil then
  error("alkahest reuse: cannot read reusable-content.json from the project root")
end
local source = handle:read("*a")
handle:close()

local registry = pandoc.json.decode(source)
if registry == nil or registry.version ~= 1 or registry.items == nil then
  error("alkahest reuse: invalid reusable-content.json registry")
end

registry.project_file = project_file
return registry
