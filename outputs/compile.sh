#!/bin/bash
# =============================================================================
# compile.sh — Compile HW03 report and presentation to PDF
# Requires: texlive (pdflatex) + texlive-latex-extra (for metropolis beamer theme).
# If metropolis is unavailable, install it or edit presentation.tex to use
# a built-in theme (e.g., Warsaw, Madrid, Copenhagen).
# Run from: outputs/ directory
# =============================================================================
set -e

# Detect LaTeX engine
if command -v lualatex &>/dev/null; then
    LATEX="lualatex"
elif command -v pdflatex &>/dev/null; then
    LATEX="pdflatex"
else
    echo "ERROR: No LaTeX engine found (pdflatex or lualatex)."
    echo "Install texlive on Linux: sudo apt install texlive-latex-base texlive-latex-extra"
    echo "Or on Windows: install MiKTeX or TeX Live."
    exit 1
fi

echo "Using LaTeX engine: $LATEX"

echo "=== Compiling Report ==="
$LATEX -interaction=nonstopmode report.tex
$LATEX -interaction=nonstopmode report.tex  # second pass for TOC/refs
echo "  -> report.pdf"

echo "=== Compiling Presentation ==="
$LATEX -interaction=nonstopmode presentation.tex
$LATEX -interaction=nonstopmode presentation.tex
echo "  -> presentation.pdf"

echo "=== Cleaning aux files ==="
rm -f *.aux *.log *.out *.toc *.nav *.snm *.bbl *.blg *.bcf *.run.xml 2>/dev/null || true

echo ""
echo "Done. Outputs: report.pdf, presentation.pdf"
