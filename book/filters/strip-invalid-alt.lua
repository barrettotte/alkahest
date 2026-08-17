-- Normalize invalid attributes Quarto copies onto generated HTML/EPUB wrappers.
function Div(div)
  local changed = false

  -- The nested Image retains its explicit alternative; Div elements do not
  -- permit alt and otherwise fail EPUBCheck.
  if div.attributes["alt"] ~= nil then
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
