-- Expand one shared-source placeholder into preview product messaging and links.
local preview = {
  enabled = false,
  watermark_enabled = false,
}

local function value_as_string(value)
  if value == nil then
    return nil
  end
  return pandoc.utils.stringify(value)
end

local function nonempty(value, label)
  local text = value_as_string(value)
  if text == nil or not text:match("%S") then
    error("alkahest preview: " .. label .. " must be nonempty")
  end
  return text
end

local function optional_url(value, label)
  local url = value_as_string(value)
  if url == nil or url == "" then
    return nil
  end
  if not url:match("^https://[^%s]+$") then
    error("alkahest preview: " .. label .. " must be an absolute HTTPS URL")
  end
  return url
end

local function as_boolean(value, label)
  local text = value_as_string(value)
  if text ~= "true" and text ~= "false" then
    error("alkahest preview: " .. label .. " must be true or false")
  end
  return text == "true"
end

local function text_inlines(text)
  local document = pandoc.read(text, "markdown")
  if #document.blocks ~= 1 or document.blocks[1].t ~= "Para" then
    error("alkahest preview: presentation text must be one paragraph")
  end
  return document.blocks[1].content
end

local function has_class(div, name)
  for _, class_name in ipairs(div.classes) do
    if class_name == name then
      return true
    end
  end
  return false
end

local function link_status(url)
  if url == nil then
    return "unassigned"
  end
  return "assigned"
end

local function preview_notice()
  local blocks = {
    pandoc.Para({ pandoc.Strong(text_inlines(preview.label)) }),
    pandoc.Para(text_inlines(preview.message)),
  }
  local links = pandoc.Inlines({})
  if preview.full_edition_url ~= nil then
    links:insert(pandoc.Link(
      text_inlines(preview.full_edition_label),
      preview.full_edition_url
    ))
  end
  if preview.purchase_url ~= nil then
    if #links > 0 then
      links:insert(pandoc.Space())
      links:insert(pandoc.Str("·"))
      links:insert(pandoc.Space())
    end
    links:insert(pandoc.Link(
      text_inlines(preview.purchase_label),
      preview.purchase_url
    ))
  end
  if #links > 0 then
    table.insert(blocks, pandoc.Para(links))
  else
    table.insert(blocks, pandoc.Para(text_inlines(preview.links_pending)))
  end
  return pandoc.Div(
    blocks,
    pandoc.Attr("preview-edition", { "alkahest-preview-notice" }, {
      ["aria-label"] = preview.label,
      ["data-full-edition-link"] = link_status(preview.full_edition_url),
      ["data-purchase-link"] = link_status(preview.purchase_url),
      ["data-watermark"] = preview.watermark_enabled and "enabled" or "disabled",
      role = "note",
    })
  )
end

function Meta(metadata)
  local alkahest = metadata.alkahest
  local config = alkahest and alkahest.preview
  if config == nil then
    return metadata
  end
  preview.enabled = as_boolean(config.enabled, "enabled")
  if not preview.enabled then
    return metadata
  end
  preview.label = nonempty(config.label, "label")
  preview.message = nonempty(config.message, "message")
  preview.full_edition_label = nonempty(
    config["full-edition-label"], "full-edition-label"
  )
  preview.full_edition_url = optional_url(
    config["full-edition-url"], "full-edition-url"
  )
  preview.purchase_label = nonempty(config["purchase-label"], "purchase-label")
  preview.purchase_url = optional_url(config["purchase-url"], "purchase-url")
  preview.links_pending = nonempty(config["links-pending"], "links-pending")
  if config.watermark == nil then
    error("alkahest preview: watermark settings are required")
  end
  preview.watermark_enabled = as_boolean(
    config.watermark.enabled, "watermark.enabled"
  )
  preview.watermark_text = nonempty(config.watermark.text, "watermark.text")
  return metadata
end

function Div(div)
  if not has_class(div, "alkahest-preview-placeholder") then
    return nil
  end
  if not preview.enabled then
    return {}
  end
  local result = pandoc.Blocks({})
  if preview.watermark_enabled
      and (FORMAT:match("html") or FORMAT:match("epub")) then
    result:insert(pandoc.Div(
      { pandoc.Plain(text_inlines(preview.watermark_text)) },
      pandoc.Attr("", { "alkahest-preview-watermark" }, {
        ["aria-hidden"] = "true",
      })
    ))
  end
  result:insert(preview_notice())
  return result
end

return {
  { Meta = Meta },
  { Div = Div },
}
