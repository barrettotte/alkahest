-- Render checked reusable Markdown fragments with explicit parameters and IDs.
local registry = require("./registry")

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function read_file(path)
  local handle = io.open(path, "r")
  if handle == nil then
    error("alk-reuse: cannot read registered fragment " .. path)
  end
  local source = handle:read("*a")
  handle:close()
  return source
end

local function contains(values, wanted)
  for _, value in ipairs(values) do
    if value == wanted then
      return true
    end
  end
  return false
end

return {
  ["alk-reuse"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-reuse: shortcodes are not allowed inside code, attributes, or URLs")
    end
    local reuse_id = value_as_string(args[1])
    if reuse_id == nil or reuse_id == "" then
      error("alk-reuse: expected a stable reuse-... ID")
    end
    if args[2] ~= nil then
      error("alk-reuse: unexpected positional argument after " .. reuse_id)
    end
    local item = registry.items[reuse_id]
    if item == nil then
      error("alk-reuse: unknown reusable-content ID: " .. reuse_id)
    end

    local instance_id = value_as_string(kwargs.id)
    local use_context = value_as_string(kwargs.context)
    if instance_id == nil or instance_id == "" then
      error("alk-reuse: " .. reuse_id .. " needs an explicit id")
    end
    if use_context == nil or not contains(item.allowed_contexts, use_context) then
      error("alk-reuse: " .. reuse_id .. " is not allowed in context " .. (use_context or "<missing>"))
    end

    local expected = { id = true, context = true }
    local replacements = {}
    for _, name in ipairs(item.parameters) do
      expected[name] = true
      local value = value_as_string(kwargs[name])
      if value == nil or value == "" then
        error("alk-reuse: " .. reuse_id .. " needs parameter " .. name)
      end
      replacements[name] = value
    end
    for name, _ in pairs(kwargs) do
      if not expected[name] then
        error("alk-reuse: " .. reuse_id .. " has unexpected argument " .. name)
      end
    end

    local source = read_file(registry.project_file(item.path))
    local rendered = source:gsub("{{([a-z][a-z0-9_]*)}}", function(name)
      local value = replacements[name]
      if value == nil then
        error("alk-reuse: " .. reuse_id .. " contains unresolved parameter " .. name)
      end
      return value
    end)
    local blocks = pandoc.read(rendered, "markdown").blocks
    return pandoc.Div(
      blocks,
      pandoc.Attr(instance_id, {
        "reusable-content",
        "reuse-kind-" .. item.kind,
      }, {
        ["data-reuse-id"] = reuse_id,
        ["data-reuse-version"] = item.version,
        ["data-reuse-sha256"] = item.sha256,
        ["data-reuse-origin"] = item.origin,
        ["data-reuse-scope"] = item.scope,
        ["data-reuse-context"] = use_context,
      })
    )
  end,
}
