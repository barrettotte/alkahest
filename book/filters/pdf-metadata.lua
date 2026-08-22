-- Adapt canonical descriptions to the single PDF Subject metadata field.
function Meta(metadata)
  if FORMAT:match("typst") or FORMAT:match("latex") then
    metadata.subject = metadata.description
  end
  return metadata
end
