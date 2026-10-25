# Original Workbook Audit

## Source
- Workbook: TANK_FILL_rev4.xlsx
- Worksheets: Tank Fill, Field Notes, Read Me
- Purpose: Estimate liquid volume added during tank-fill runs.

## Finding 1: Possible Unit Discrepancy
Run R-108 is recorded as 2.5 inches in the Tank Fill sheet.
The Field Notes sheet records the same run as 2.5 ft.

These values are not equivalent. The source records must be
reviewed before choosing which measurement the application uses.
The original workbook is not modified.

## Finding 2: Total Formula Range
Cell G25 uses =SUM(G6:G17).
This range includes runs R-101 through R-112 but excludes
R-113 through R-118, which also have recorded volumes.

The application should calculate totals from the accepted
records rather than silently omitting later runs.

## Finding 3: Volume Calculation
The visible row formula is:
Length (ft) * Width (ft) * (Fill Depth (in) / 12) * 7.48052

The depth is converted from inches to feet before calculating
volume in cubic feet and converting to US gallons.

## Limitations
The workbook's Read Me sheet warns that formulas and data
may be incorrect. These findings are based on the visible
worksheet contents. They do not establish which R-108
measurement is correct or independently validate every formula.

## Preservation
The original workbook is retained as a reference.
Any corrections or experiments should be made in application
code or a separate copy, not in the original source file.
