-- Expand semantic icon shortcodes from the central registry into portable AST.
local registry = require("./registry")
local lookup = {}

for name, entry in pairs(registry) do
  entry.name = name
  lookup[name] = entry
  for _, alias in ipairs(entry.aliases or {}) do
    if lookup[alias] ~= nil then
      error("alk-icon: duplicate registry name or alias: " .. alias)
    end
    lookup[alias] = entry
  end
end

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

return {
  ["alk-icon"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-icon: shortcodes are not allowed inside code, attributes, or URLs")
    end

    local requested_name = value_as_string(args[1])
    if requested_name == nil or requested_name == "" then
      error("alk-icon: expected a registry name such as equipment or warning")
    end
    if args[2] ~= nil then
      error("alk-icon: unexpected positional argument after " .. requested_name)
    end

    local entry = lookup[requested_name]
    if entry == nil then
      error("alk-icon: unknown registry name or alias: " .. requested_name)
    end

    for key, value in pairs(kwargs) do
      if key ~= "label" and #value > 0 then
        error("alk-icon: unknown named argument: " .. key)
      end
    end

    local label = entry.label
    if kwargs.label ~= nil and #kwargs.label > 0 then
      label = value_as_string(kwargs.label)
      if label == "" then
        error("alk-icon: label must not be empty")
      end
    end

    local asset = entry.asset
    if quarto.doc.isFormat("latex") then
      asset = asset:gsub("%.svg$", ".pdf")
    end

    -- Reflowable editions always require equivalent visible text, so hiding the
    -- span avoids a duplicate screen-reader announcement. The image alternative
    -- remains intact for format conversion and PDF metadata.
    local reflowable = quarto.doc.isFormat("html") or quarto.doc.isFormat("epub")

    local image = pandoc.Image(
      { pandoc.Str(label) },
      asset,
      label,
      pandoc.Attr("", { "semantic-icon-image" }, {
        width = "1em",
        height = "1em",
      })
    )
    local span_attributes = {
      ["data-icon"] = entry.name,
      ["data-icon-label"] = label,
      title = label,
    }
    if reflowable then
      span_attributes["aria-hidden"] = "true"
    end

    return pandoc.Span(
      { image },
      pandoc.Attr("", {
        "semantic-icon",
        "semantic-icon-" .. entry.name,
      }, span_attributes)
    )
  end,
}
