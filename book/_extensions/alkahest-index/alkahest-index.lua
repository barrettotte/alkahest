-- Expand stable subject/person index markers without adding visible prose.
local registry = require("./registry")

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function anchor(entry, marker, range_edge)
  if range_edge == nil then
    return "index-ref-" .. entry.name .. "-" .. marker
  end
  return "index-range-" .. entry.name .. "-" .. marker .. "-" .. range_edge
end

return {
  ["alk-index"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-index: shortcodes are not allowed inside code, attributes, or URLs")
    end
    local requested_name = value_as_string(args[1])
    if requested_name == nil or requested_name == "" then
      error("alk-index: expected an index name such as computation")
    end
    if args[2] ~= nil then
      error("alk-index: unexpected positional argument after " .. requested_name)
    end
    for key, _value in pairs(kwargs) do
      if key ~= "id" and key ~= "range" then
        error("alk-index: unknown named argument " .. key)
      end
    end
    local entry = registry.lookup[requested_name]
    if entry == nil then
      error("alk-index: unknown index name or alias " .. requested_name)
    end
    local marker = value_as_string(kwargs.id)
    if marker == nil or not marker:match("^[a-z][a-z0-9-]*$") then
      error("alk-index: id must be a lowercase hyphenated stable name")
    end
    local range_edge = value_as_string(kwargs.range)
    if range_edge == "" then
      range_edge = nil
    end
    if range_edge ~= nil and range_edge ~= "start" and range_edge ~= "end" then
      error("alk-index: range must be start or end")
    end
    local identifier = anchor(entry, marker, range_edge)
    local attributes = {
      ["data-index-id"] = entry.name,
      ["data-index-marker"] = marker,
      ["data-index-requested"] = requested_name,
    }
    if range_edge ~= nil then
      attributes["data-index-range"] = range_edge
    end

    if quarto.doc.isFormat("typst") then
      return pandoc.Span(
        { pandoc.RawInline("typst", "#box(width: 0pt)[] <" .. identifier .. ">") },
        pandoc.Attr("", { "index-marker" }, attributes)
      )
    end
    return pandoc.Span({}, pandoc.Attr(
      identifier,
      { "index-marker" },
      attributes
    ))
  end,
}
