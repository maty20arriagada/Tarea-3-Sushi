@echo off
REM =============================================================================
REM compile.bat — Windows batch file for compiling HW03 report and presentation
REM Requires: MiKTeX or TeX Live with pdflatex in PATH.
REM Run from: outputs\ directory
REM =============================================================================

echo === Compiling Report ===
pdflatex -interaction=nonstopmode report.tex
pdflatex -interaction=nonstopmode report.tex
echo   -^> report.pdf

echo === Compiling Presentation ===
pdflatex -interaction=nonstopmode presentation.tex
pdflatex -interaction=nonstopmode presentation.tex
echo   -^> presentation.pdf

echo === Cleaning aux files ===
del /q *.aux *.log *.out *.toc *.nav *.snm *.bbl *.blg *.bcf *.run.xml 2>nul

echo.
echo Done. Outputs: report.pdf, presentation.pdf
pause
