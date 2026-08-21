-- Normalize invalid attributes Quarto copies onto generated HTML/EPUB wrappers.
function Div(div)
  local changed = false

  -- Generated Mermaid and Graphviz figures can leave their source fig-alt on
  -- the wrapper instead of the converted image. Restore it before removing
  -- the invalid wrapper attribute; ordinary figures already carry their own.
  if div.attributes["alt"] ~= nil then
    local wrapper_alt = div.attributes["alt"]
    div = div:walk({
      Image = function(image)
        if image.attributes["alt"] == nil
            and pandoc.utils.stringify(image.caption):match("^%s*$") then
          image.attributes["alt"] = wrapper_alt
          changed = true
          return image
        end
      end,
    })
    div.attributes["alt"] = nil
    changed = true
  end

  -- EPUB callout rendering may preserve semantic classes in an outer wrapper
  -- while copying the same identifier to its nested callout. Keep the ID on
  -- the actual callout so references remain unique and correctly targeted.
  local child = div.content[1]
  if div.identifier ~= ""
      and child ~= nil
      and child.t == "Div"
      and child.identifier == div.identifier then
    div.identifier = ""
    changed = true
  end

  if changed then
    return div
  end
end
