-- Render versioned companion references with web downloads and print fallbacks.
local registry = require("./registry")

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function append_text(inlines, text)
  if #inlines > 0 then
    table.insert(inlines, pandoc.Space())
  end
  table.insert(inlines, pandoc.Str(text))
end

return {
  ["alk-companion"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-companion: shortcodes are not allowed inside code, attributes, or URLs")
    end
    local id = value_as_string(args[1])
    if id == nil or id == "" then
      error("alk-companion: expected a stable asset-... ID")
    end
    if args[2] ~= nil then
      error("alk-companion: unexpected positional argument after " .. id)
    end
    if next(kwargs) ~= nil then
      error("alk-companion: named arguments are not supported")
    end
    local item = registry.items[id]
    if item == nil then
      error("alk-companion: unknown companion ID: " .. id)
    end

    local title = item.title
    local title_inlines = { pandoc.Str(title) }
    if quarto.doc.isFormat("html") and not quarto.doc.isFormat("epub") then
      title_inlines = {
        pandoc.Link(
          { pandoc.Str("Download " .. title) },
          item.url or item.path,
          item.description,
          pandoc.Attr("", { "companion-download" }, {
            download = "",
            ["data-media-type"] = item.media_type,
          })
        ),
      }
    end

    local inlines = { pandoc.Strong(title_inlines) }
    append_text(inlines, "—")
    append_text(inlines, item.kind .. ", version " .. item.version .. ".")
    append_text(inlines, item.description)
    append_text(inlines, "Compatibility: " .. table.concat(item.compatibility, "; ") .. ".")
    append_text(inlines, "SHA-256: " .. item.sha256:sub(1, 12) .. "….")
    if item.release_path ~= nil then
      append_text(inlines, "Release package: " .. item.release_path .. ".")
    else
      append_text(inlines, "Durable URL: " .. item.url .. ".")
    end

    return pandoc.Span(
      inlines,
      pandoc.Attr(id, {
        "companion-reference",
        "companion-kind-" .. item.kind,
      }, {
        ["data-companion-kind"] = item.kind,
        ["data-companion-version"] = item.version,
        ["data-companion-sha256"] = item.sha256,
        ["data-companion-path"] = item.path,
        ["data-release-path"] = item.release_path or "",
        ["data-companion-url"] = item.url or "",
      })
    )
  end,
}
