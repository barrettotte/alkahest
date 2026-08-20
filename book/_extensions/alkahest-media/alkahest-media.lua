-- Render web media enhancements and portable static/transcript fallbacks.
local registry = require("./registry")

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function text_inlines(value)
  local document = pandoc.read(value, "markdown")
  if #document.blocks == 1 and document.blocks[1].content ~= nil then
    return document.blocks[1].content
  end
  return { pandoc.Str(value) }
end

local function escape_html(value)
  return value:gsub("&", "&amp;"):gsub('"', "&quot;"):gsub("<", "&lt;"):gsub(">", "&gt;")
end

local function player_html(item)
  local title = escape_html(item.title)
  local asset = escape_html(item.asset)
  local media_type = escape_html(item.media_type)
  local fallback = escape_html(item.fallback)
  local alt = escape_html(item.fallback_alt)
  if item.kind == "audio" then
    return string.format(
      '<audio class="rich-media-player rich-media-audio" controls preload="metadata" aria-label="%s"><source src="%s" type="%s"></audio>',
      title,
      asset,
      media_type
    )
  end
  if item.kind == "video" then
    return string.format(
      '<video class="rich-media-player rich-media-video" controls preload="metadata" poster="%s" aria-label="%s"><source src="%s" type="%s"><track kind="captions" src="%s" srclang="en" label="English" default></video>',
      fallback,
      title,
      asset,
      media_type,
      escape_html(item.captions)
    )
  end
  local sandbox = item.kind == "interactive" and ' sandbox="allow-scripts"' or ' sandbox=""'
  return string.format(
    '<iframe class="rich-media-player rich-media-%s" src="%s" title="%s" loading="lazy"%s></iframe><noscript><img src="%s" alt="%s"></noscript>',
    item.kind,
    asset,
    title,
    sandbox,
    fallback,
    alt
  )
end

local function transcript_blocks(item)
  local blocks = {
    pandoc.Para({ pandoc.Strong({ pandoc.Str("Transcript and description") }) }),
  }
  local parsed = pandoc.read(registry.read_file(item.transcript), "markdown")
  for _, block in ipairs(parsed.blocks) do
    table.insert(blocks, block)
  end
  return pandoc.Div(blocks, pandoc.Attr("", { "rich-media-transcript" }))
end

return {
  ["alk-media"] = function(args, kwargs, _meta, _raw_args, context)
    if context == "text" then
      error("alk-media: shortcodes are not allowed inside code, attributes, or URLs")
    end
    local id = value_as_string(args[1])
    if id == nil or id == "" or not id:match("^media%-%l[%l%d%-]+$") then
      error("alk-media: expected a stable media-... ID")
    end
    if args[2] ~= nil then
      error("alk-media: unexpected positional argument after " .. id)
    end
    if next(kwargs) ~= nil then
      error("alk-media: named arguments are not supported")
    end
    local item = registry.items[id]
    if item == nil then
      error("alk-media: unknown rich-media ID: " .. id)
    end

    local blocks = {
      pandoc.Para({ pandoc.Strong(text_inlines(item.title)) }),
    }
    local web = quarto.doc.isFormat("html") and not quarto.doc.isFormat("epub")
    if web then
      table.insert(blocks, pandoc.RawBlock("html", player_html(item)))
    else
      local image = pandoc.Image(
        text_inlines(item.fallback_alt),
        item.fallback,
        item.title,
        pandoc.Attr("", { "rich-media-fallback-image" }, { width = "90%" })
      )
      table.insert(blocks, pandoc.Para({ image }))
    end
    table.insert(blocks, pandoc.Para(text_inlines(item.description)))
    table.insert(blocks, transcript_blocks(item))

    return pandoc.Div(
      blocks,
      pandoc.Attr(id, {
        "rich-media",
        "rich-media-kind-" .. item.kind,
      }, {
        ["data-media-kind"] = item.kind,
        ["data-media-type"] = item.media_type,
        ["data-media-sha256"] = item.sha256,
        ["data-media-license"] = item.license,
        ["data-media-public"] = tostring(item.public_distribution),
      })
    )
  end,
}
