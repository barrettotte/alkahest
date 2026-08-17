-- Remove Quarto-copied alt attributes from non-image wrappers after rendering.
-- The nested Image retains its explicit alternative; HTML/EPUB Div elements
-- do not permit alt and otherwise fail EPUBCheck.
function Div(div)
  if div.attributes["alt"] ~= nil then
    div.attributes["alt"] = nil
    return div
  end
end
