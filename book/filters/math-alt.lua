-- Give annotated inline mathematics explicit alternatives in Typst PDF output.
local class_name = "alkahest-math-alt"

function Meta(metadata)
  if FORMAT:match("typst") then
    metadata.subject = metadata.description
  end
  return metadata
end

local function has_class(span)
  for _, value in ipairs(span.classes) do
    if value == class_name then
      return true
    end
  end
  return false
end

local function typst_string(value)
  value = value:gsub("\\", "\\\\")
  value = value:gsub('"', '\\"')
  value = value:gsub("\r?\n", " ")
  return '"' .. value .. '"'
end

function Span(span)
  if not has_class(span) then
    return nil
  end

  local alternative = span.attributes.alt
  if alternative == nil or alternative:match("^%s*$") then
    error("alkahest math alt: annotated inline math needs nonempty alt text")
  end
  if #span.content ~= 1 or span.content[1].t ~= "Math"
      or span.content[1].mathtype ~= "InlineMath" then
    error("alkahest math alt: annotation must contain exactly one inline expression")
  end

  if FORMAT:match("typst") then
    return {
      pandoc.RawInline(
        "typst",
        "#math.equation(block: false, alt: " .. typst_string(alternative) .. ", ["
      ),
      span.content[1],
      pandoc.RawInline("typst", "])")
    }
  end

  -- HTML and EPUB retain native MathML.
  return span.content
end
