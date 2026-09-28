# Report

The assignment report in the ACM Small format (`acmart` class with the
`nonacm` option, so there is no ACM, journal or copyright information).

| File | Contents |
|---|---|
| `main.tex` | the report |
| `references.bib` | bibliography (ACM reference format) |
| `figures/*.pdf` | copies of `results/figures/*.pdf`, produced by `python -m scripts.plot_results` |

## Compiling on Overleaf

1. Zip this `report/` folder.
2. In Overleaf, choose **New Project → Upload Project** and upload the zip.
3. Check that the compiler is **pdfLaTeX** (Menu → Settings) and the main document is `main.tex`.
4. Click **Recompile**. BibTeX runs automatically.

## Compiling locally

With a TeX distribution that includes `acmart` (TeX Live or MiKTeX):

```bash
latexmk -pdf main.tex
```

## Updating the figures

After a new benchmark run, regenerate the figures and copy them in:

```bash
python -m scripts.plot_results
cp results/figures/*.pdf report/figures/
```
