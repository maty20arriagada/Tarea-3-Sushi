# Apollo R — validación cruzada + Latent Class

Scripts Apollo del proyecto. Los modelos M1–M4b replican las especificaciones
Python (`scripts/02_estimate_models.py`, `scripts/03_exploded_models.py`) como
validación cruzada; el M5-LC (clases latentes) se estima solo aquí.

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
| 1 | `01_apollo_mnl.R` | M1, M2, M3 | LL −9850.73 / −9755.07 / −9733.21 — paridad Python ≤0.004 |
| 2 | `02_apollo_nested_logit.R` | M2exp, M4b | LL −29446.46 / −29159.71 — paridad ≤0.01 |
| 3 | `03_apollo_latent_class.R` | M5-LC (S=2 y S=3) | LC3 mejor por BIC: LL −28513.74, BIC 57383.3 |
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
  Python (reparametrización exp + logsumexp); Apollo valida M4b (λ_ns = 1),
  que es además la variante usada en las simulaciones.
