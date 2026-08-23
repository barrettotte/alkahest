"""Exercise PDF preflight parsers and rejection boundaries with text fixtures."""

from alkahest.pdf_preflight import (
    PreflightError,
    validate_color_spaces,
    validate_document_metadata,
    validate_fonts,
    validate_page_boxes,
    validate_raster_images,
)

INFO = """Pages:           2
Encrypted:       no
JavaScript:      no
PDF version:     1.7
"""

BOXES = """Page    1 size:  504 x 720 pts
Page    1 rot:   0
Page    2 size:  504 x 720 pts
Page    2 rot:   0
Page    1 MediaBox:      0.00     0.00   504.00   720.00
Page    1 CropBox:       0.00     0.00   504.00   720.00
Page    1 BleedBox:      0.00     0.00   504.00   720.00
Page    1 TrimBox:       0.00     0.00   504.00   720.00
Page    1 ArtBox:        0.00     0.00   504.00   720.00
Page    2 MediaBox:      0.00     0.00   504.00   720.00
Page    2 CropBox:       0.00     0.00   504.00   720.00
Page    2 BleedBox:      0.00     0.00   504.00   720.00
Page    2 TrimBox:       0.00     0.00   504.00   720.00
Page    2 ArtBox:        0.00     0.00   504.00   720.00
"""

FONTS = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
ABCDEF+LibertinusSerif-Regular       CID Type 0C       Identity-H       yes yes yes     12  0
UVWXYZ+SourceCodePro-Regular         CID Type 0C       Identity-H       yes yes yes     19  0
"""

IMAGES = """page   num  type   width height color comp bpc  enc interp  object ID x-ppi y-ppi size ratio
--------------------------------------------------------------------------------------------
   4     0 image    1200    900  rgb     3   8  jpeg   no       81  0   320   320  100K 3.0%
   8     1 image    2400   1200 mono     1   1  ccitt  no       94  0   600   600   20K 0.2%
"""

ALLOWED_COLORS = {("mono", 1), ("gray", 1), ("rgb", 3), ("icc", 3)}

COLOR_REPORT = """<?xml version="1.0" encoding="utf-8"?>
<report>
  <jobs><job><featuresReport><documentResources><colorSpaces>
    <colorSpace id="rgb" family="DeviceRGB" />
    <colorSpace id="icc" family="ICCBased"><components>3</components></colorSpace>
  </colorSpaces></documentResources></featuresReport></job></jobs>
  <batchSummary failedToParse="0" encrypted="0" veraExceptions="0">
    <featureReports failedJobs="0">1</featureReports>
  </batchSummary>
</report>
"""


def rejected(name, action, message):
    try:
        action()
    except PreflightError as error:
        if message not in str(error):
            raise RuntimeError(
                f"{name}: expected diagnostic containing {message!r}, got {error!r}"
            ) from error
    else:
        raise RuntimeError(f"{name}: invalid fixture unexpectedly passed")


def replace_image(**changes):
    fields = IMAGES.splitlines()[2].split()
    positions = {
        "color": 5,
        "components": 6,
        "bits": 7,
        "x_ppi": 12,
        "y_ppi": 13,
    }
    for name, value in changes.items():
        fields[positions[name]] = str(value)
    return "\n".join(IMAGES.splitlines()[:2] + [" ".join(fields)]) + "\n"


def main():
    if validate_document_metadata(INFO, {"1.7"}) != 2:
        raise RuntimeError("valid metadata fixture returned the wrong page count")
    validate_page_boxes(BOXES, 2, 504, 720, 0, 0.1)
    if validate_fonts(FONTS) != 2:
        raise RuntimeError("valid font fixture returned the wrong row count")
    if validate_raster_images(IMAGES, ALLOWED_COLORS, 300, 600) != 2:
        raise RuntimeError("valid image fixture returned the wrong row count")
    if validate_color_spaces(COLOR_REPORT, {"DeviceRGB", "ICCBased"}, {1, 3}, False) != {
        "DeviceRGB",
        "ICCBased",
    }:
        raise RuntimeError("valid color-space fixture returned the wrong families")

    cases = [
        (
            "encrypted",
            lambda: validate_document_metadata(
                INFO.replace("Encrypted:       no", "Encrypted:       yes"), {"1.7"}
            ),
            "must not be encrypted",
        ),
        (
            "javascript",
            lambda: validate_document_metadata(
                INFO.replace("JavaScript:      no", "JavaScript:      yes"), {"1.7"}
            ),
            "must not contain JavaScript",
        ),
        (
            "version",
            lambda: validate_document_metadata(INFO, {"2.0"}),
            "outside the allowed set",
        ),
        (
            "wrong-trim",
            lambda: validate_page_boxes(
                BOXES.replace(
                    "Page    2 TrimBox:       0.00     0.00   504.00   720.00",
                    "Page    2 TrimBox:       0.00     0.00   500.00   720.00",
                ),
                2,
                504,
                720,
                0,
                0.1,
            ),
            "page 2 TrimBox",
        ),
        (
            "rotation",
            lambda: validate_page_boxes(
                BOXES.replace("Page    1 rot:   0", "Page    1 rot:   90"),
                2,
                504,
                720,
                0,
                0.1,
            ),
            "unsupported rotation",
        ),
        (
            "unembedded-font",
            lambda: validate_fonts(FONTS.replace("yes yes yes", "no  no  yes", 1)),
            "is not embedded",
        ),
        (
            "unsubset-font",
            lambda: validate_fonts(FONTS.replace("yes yes yes", "yes no  yes", 1)),
            "not subset",
        ),
        (
            "low-resolution",
            lambda: validate_raster_images(replace_image(x_ppi=299), ALLOWED_COLORS, 300, 600),
            "minimum is 300 PPI",
        ),
        (
            "low-resolution-one-bit",
            lambda: validate_raster_images(
                replace_image(color="mono", components=1, bits=1, x_ppi=599),
                ALLOWED_COLORS,
                300,
                600,
            ),
            "minimum is 600 PPI",
        ),
        (
            "cmyk",
            lambda: validate_raster_images(
                replace_image(color="cmyk", components=4),
                ALLOWED_COLORS,
                300,
                600,
            ),
            "disallowed color model cmyk/4",
        ),
        (
            "vector-cmyk",
            lambda: validate_color_spaces(
                COLOR_REPORT.replace("DeviceRGB", "DeviceCMYK"),
                {"DeviceRGB", "ICCBased"},
                {1, 3},
                False,
            ),
            "disallowed vector color-space family DeviceCMYK",
        ),
        (
            "icc-cmyk",
            lambda: validate_color_spaces(
                COLOR_REPORT.replace("<components>3", "<components>4"),
                {"DeviceRGB", "ICCBased"},
                {1, 3},
                False,
            ),
            "has 4 components",
        ),
        (
            "undeclared-output-intent",
            lambda: validate_color_spaces(
                COLOR_REPORT.replace(
                    "</documentResources>",
                    "<outputIntents><outputIntent /></outputIntents></documentResources>",
                ),
                {"DeviceRGB", "ICCBased"},
                {1, 3},
                False,
            ),
            "contains an output intent",
        ),
    ]
    for name, action, message in cases:
        rejected(name, action, message)
    print(f"ok: PDF preflight fixtures ({len(cases) + 5} cases)")


def test_contract():
    result = main()
    assert result in (None, 0)
