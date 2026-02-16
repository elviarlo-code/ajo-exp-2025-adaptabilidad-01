# Descripción de datasets y criterios de procesamiento  
Proyecto: ajo-exp-2025-adaptabilidad-01  

Este documento describe los archivos de datos generados durante el experimento de evaluación de cultivares de ajo y los criterios utilizados para su procesamiento, con el fin de asegurar trazabilidad, reproducibilidad y claridad metodológica.

---

## 1. Archivo: biometria_con_calibre.csv

### Descripción general

Contiene los datos crudos de biometría de 10 plantas por parcela experimental, incluyendo variables morfológicas, peso de bulbo y clasificación comercial.

Cada fila representa una planta individual.

### Variables principales

- `parcela`: Identificador de la parcela experimental.
- `bloque`: Bloque experimental.
- `tratamiento_nombre`: Cultivar evaluado.
- `DDS`: Días después de la siembra al momento de cosecha.
- `peso_bulbo_gr`: Peso individual del bulbo (g).
- `longitud_bulbo_mm`: Longitud del bulbo (mm).
- `ancho_bulbo_mm`: Diámetro del bulbo (mm).
- `num_dientes`: Número de dientes por bulbo.
- `num_hojas`: Número de hojas por planta.
- `calibre_com`: Calibre comercial según escala Mercosur.

### Clasificación comercial

Se consideraron como bulbos comerciales aquellos con:
calibre_com ≥ 5
correspondiente aproximadamente a diámetros ≥45 mm, según criterios de comercialización del ajo en Mercosur.

---

## 2. Archivo: diseno_experimental.csv

Describe el diseño experimental y la estructura de parcelas.

Variables clave:

- `parcela`
- `bloque`
- `tratamiento_codigo`
- `tratamiento_nombre`
- `area_parcela_surco_m2`: Área cosechada de la parcela (m²)
- `plantas_totales_parcela`: Número total de plantas por parcela (66)

Este archivo se utiliza para convertir pesos de parcela a rendimiento por hectárea.

---

## 3. Archivo: rend_extra_muestra_coma.csv

Contiene el peso del resto de la parcela cosechada, excluyendo las 10 plantas muestreadas.

Variables:

- `parcela`
- `peso_conto_gr`: peso del material restante de la parcela (g)

Este valor se suma al peso de las 10 plantas para obtener la cosecha total observada por parcela.

---

## 4. Archivo generado: parcelas_cuantitativas.csv

Archivo agregado a nivel de parcela (unidad experimental) utilizado para análisis estadístico.

Cada fila representa una parcela experimental.

### Variables de identificación

- `parcela`
- `bloque`
- `tratamiento_codigo`
- `tratamiento_nombre`
- `area_parcela_surco_m2`
- `plantas_totales_parcela`

---

### Precocidad

- `dds_cosecha`: valor mínimo de DDS por parcela (días después de siembra), utilizado como indicador de precocidad.

---

### Información de la submuestra (10 plantas)

- `n_muestreo`: número de plantas evaluadas (10)
- `n_com_muestreo`: número de plantas comerciales en la muestra
- `prop_comercial_n_muestreo`: proporción comercial por número
- `peso_muestra_total_g`: peso total de la muestra (g)
- `peso_muestra_com_g`: peso comercial de la muestra (g)
- `prop_comercial_peso_muestra`: proporción comercial por peso en la muestra

---

### Cosecha real de la parcela

- `peso_conto_gr`: peso del resto de la parcela (sin incluir las 10 plantas)
- `peso_parcela_total_g_obs`: peso total observado de la parcela

Calculado como:
peso_parcela_total_g_obs = peso_muestra_total_g + peso_conto_gr

---

### Rendimiento

El rendimiento se calculó utilizando el área real de la parcela:

rendimiento_total_tn_ha = (peso_parcela_total_g_obs / area_parcela_surco_m2) × 0.01

- `rendimiento_total_tn_ha`: rendimiento total (t/ha)

El rendimiento comercial se estimó como:

peso_parcela_comercial_g_est =
peso_muestra_com_g + (peso_conto_gr × prop_comercial_peso_muestra)
rendimiento_comercial_tn_ha =
(peso_parcela_comercial_g_est / area_parcela_surco_m2) × 0.01

- `rendimiento_comercial_tn_ha`: rendimiento comercial estimado (t/ha)

---

### Variables morfológicas promedio

Promedios por parcela de las variables cuantitativas medidas en 10 plantas:

- `peso_bulbo_gr`
- `num_hojas`
- `longitud_bulbo_mm`
- `ancho_bulbo_mm`
- `num_dientes`
- `ancho_bulbo_mm_clasif`

Estas variables se utilizan como variables dependientes en el análisis de varianza.

---

## Nota metodológica

- La parcela constituye la unidad experimental.
- Las plantas individuales representan submuestras.
- DDS se resume por parcela usando el valor mínimo para representar precocidad.
- El rendimiento total se basa en cosecha observada por parcela.
- El rendimiento comercial se estima usando la proporción comercial por peso de la submuestra.

Este enfoque permite integrar productividad, calidad comercial y precocidad dentro de un mismo marco analítico reproducible.

