# Overleaf / LaTeX report — Agricultural Water Usage Analyzer

Upload the contents of this `report/` folder to a blank Overleaf project
(or compile locally) as follows:

## Files

- `main.tex` — the complete report (article class, 11pt, A4)
- `figures/` — all figures used by the report:
  - `vce_logo.jpg` — college logo for the title page (from the supplied template)
  - `crop_intensity.png`, `monthly_usage.png`, `heatmap.png` — charts generated
    by running `water_usage_analyzer.py` (see the project README)
  - `terminal_output.png` — rendered transcript of the actual verified run log,
    cropped to the cleaning report and headline totals
- No `.bib` file is needed: references are written inline in `main.tex`
  (`thebibliography`), so the project compiles with plain pdfLaTeX.

## Compile in Overleaf

1. Create a blank Overleaf project.
2. Upload `main.tex` and the whole `figures/` folder, preserving the folder name.
3. Set the compiler to pdfLaTeX and press Recompile.
4. The PDF must be **15 pages or fewer**. Verified locally on 2026-10-25:
   **13 pages** (A4, pdfLaTeX, TeX Live 2023, 3 passes, no compilation
   errors, no overfull boxes, no undefined references). A copy of that
   verified PDF is included here as `main.pdf`.

## Compile locally

```bash
cd report
pdflatex main.tex
pdflatex main.tex   # second run resolves the table of contents
pdfinfo main.pdf | grep Pages
```

## Notes

- The full Python program is **not** reprinted in this report (to stay within
  the page limit). It lives in the repository root as
  `water_usage_analyzer.py`. The program, its tests and this report are
  published at https://github.com/Taraka-Ramarao-D/Agricultural-Water-Usage-Analyzer.
- All numbers in the report were produced by actually running the program
  (Python 3.12.3, Matplotlib 3.6.3): 612 raw records → 550 clean records,
  1,749.23 ha, 1,292,341 m³ of water.
- The dataset is simulated by the program itself (fixed seed 16) and is
  stated as such in the report; it is not presented as real farm measurements.
