# Apollo R — validación cruzada + Latent Class

Scripts Apollo del proyecto. Los modelos **protagonistas del informe** son
**M3** (MNL con interacciones demográficas, Set A), **M4b** (Nested Logit con
$\lambda_{\text{non\_seafood}}=1$ fijo, sobre ranking explotado), **M5-LC3**
(Latent Class MNL con 3 clases) y **M6** (MNL de atributos sobre Set B,
estimado en Python). Los **baselines** M1, M2 y M2$_\text{exp}$ se estiman
aquí como referencia anidada para los tests de razón de verosimilitud que
justifican la selección de M3 y M4b; no se discuten en el cuerpo del informe
pero aparecen como filas en la tabla de comparación.

**Estado: EJECUTADOS el 2026-07-04 con R 4.5.3 + Apollo 0.3.7.** Los outputs
(`APOLLO_*_output.txt`, `*_estimates.csv`, CSVs de validación) están en
`outputs/tables/`. Guía de interpretación: `EXPLICACION_MODELOS_R.txt`.

## Requisitos

```r
install.packages(c("apollo", "dplyr", "tidyr"))
```

## Orden de ejecución (working directory = esta carpeta)

| # | Script | Modelos | Resultado ejecutado |
|---|---|---|---|
| 1 | `01_apollo_mnl.R` | M1, M2, M3 (baselines + protagonista) | LL −9850.73 / −9755.07 / −9733.21 — paridad Python ≤0.004 |
| 2 | `02_apollo_nested_logit.R` | M2exp (baseline), M4b (protagonista) | LL −29446.46 / −29159.71 — paridad ≤0.01 |
| 3 | `03_apollo_latent_class.R` | M5-LC (S=2 y S=3; protagonista M5-LC3) | LC3 mejor por BIC: LL −28513.74, BIC 57383.3 |
| 4 | `04_lc_postprocess.R` | posteriores LC | shares 33.7/31.3/34.9%, perfiles por clase |

Desde terminal (R no está en PATH):
`"C:\Program Files\R\R-4.5.3\bin\Rscript.exe" 01_apollo_mnl.R`

## Notas

- Los atributos entran CRUDOS (sin z-score) para que los coeficientes sean
  directamente comparables con Python.
- Identificación (plan §0.3): nunca combinar ASCs completos con betas de
  atributos — son perfectamente colineales en el Set A. Aplica también
  dentro de cada clase del LC.
- El M4 con los 3 λ libres NO es estimable en Apollo: λ_non_seafood cae a la
  frontera λ→0 y el optimizador BGW produce NaN. El M4 libre se estima en
  Python (reparametrización exp + logsumexp); Apollo valida M4b
  (λ_non_seafood = 1), que es además la variante usada en las simulaciones
  contrafactuales del informe (Sección C, escenarios A y B).
- Los escenarios Set A del informe transfieren los betas de atributo desde
  M6 (Set B) con constantes calibradas (Train, 2009); este enfoque evita la
  multicolinealidad del Set A (corr(precio, oiliness) = 0.82).
