# 3. MÉTODOS
## Materiales y métodos
### Área de estudio

El experimento se llevó a cabo en la región Lambayeque, al norte del Perú, bajo condiciones agroecológicas costeras caracterizadas por un clima árido a semiárido, baja precipitación anual, alta radiación solar y agricultura bajo riego. Estas condiciones son representativas de los principales sistemas de producción de ajo en la costa peruana.
---

### Material vegetal

Se evaluaron cinco cultivares de ajo (Allium sativum L.), incluyendo variedades mejoradas y colecciones locales:

INIA 104 Blanco

INIA 105 Donajus

Ajo Chino

Ajo Canetano

Ajo Kiyan

Estos materiales fueron seleccionados en función de su relevancia agronómica, disponibilidad en sistemas productivos locales y potencial para programas de desarrollo de semilla regional.
---

### Diseño experimental y manejo del cultivo

El experimento se estableció en condiciones de campo utilizando un diseño de bloques completos al azar (DBCA). Cada cultivar fue asignado a parcelas experimentales dentro de cada bloque, con el objetivo de controlar la variabilidad espacial.

Se aplicaron prácticas agronómicas estándar para el cultivo de ajo en la región, incluyendo preparación del suelo, siembra, manejo del riego, fertilización y control de plagas y enfermedades. Todas las parcelas fueron manejadas bajo condiciones uniformes para asegurar que las diferencias observadas entre cultivares se deban principalmente a factores genéticos y fisiológicos.
---

### Variables agronómicas

Se evaluó un conjunto de variables agronómicas y morfológicas relacionadas con el desarrollo del cultivo, características del bulbo y componentes del rendimiento. Las variables incluyeron:

Número de plantas por muestra

Proporción comercial de plantas

Peso de bulbo (g)

Peso total de muestra (g)

Peso comercial de muestra (g)

Peso total de parcela (kg)

Peso comercial de parcela (kg)

Rendimiento total (t ha⁻¹)

Rendimiento comercial (t ha⁻¹)

Longitud de bulbo (mm)

Diámetro de bulbo (mm)

Número de dientes

Número de hojas

Estas variables fueron seleccionadas para representar tanto atributos productivos como características morfológicas relevantes para la evaluación comercial y la diferenciación varietal.
---

### Preprocesamiento de datos

Los datos fueron procesados utilizando Python. Antes del análisis, se excluyeron variables no numéricas y columnas de identificación (por ejemplo, parcela, bloque, códigos de tratamiento).

Para garantizar la comparabilidad entre variables medidas en diferentes escalas, los datos fueron estandarizados mediante normalización tipo z-score (media = 0, desviación estándar = 1). Asimismo, se calcularon valores promedio por cultivar para representar su desempeño agronómico general en los análisis multivariados.
---

### Análisis estadístico univariado

Se realizó un análisis de varianza (ANOVA) para evaluar las diferencias entre cultivares en cada variable agronómica. El modelo incluyó el cultivar como factor fijo y los bloques como efecto aleatorio.

Previamente al ANOVA, se verificaron los supuestos de normalidad y homogeneidad de varianzas. En caso necesario, se consideraron transformaciones de datos para cumplir con estos supuestos.

Las diferencias significativas entre cultivares se interpretaron a un nivel de significancia de p < 0.05.
---

### Análisis multivariado
Análisis de Componentes Principales (ACP)

Se realizó un análisis de componentes principales (ACP) utilizando datos estandarizados, con el objetivo de reducir la dimensionalidad e identificar las principales fuentes de variabilidad entre cultivares. Se consideraron los dos primeros componentes principales (PC1 y PC2) para la interpretación.

Se calculó la proporción de varianza explicada por cada componente, y las coordenadas de los cultivares fueron utilizadas para visualizar su relación y diferenciación.
---

Clustering jerárquico

Se llevó a cabo un análisis de agrupamiento jerárquico para clasificar los cultivares en función de la similitud de sus perfiles agronómicos. Se construyó una matriz de distancias a partir de los datos estandarizados y se aplicó un método aglomerativo.
---

Se generaron dendrogramas para visualizar la estructura de agrupamiento entre los cultivares.

Análisis mediante heatmap

Se generó un mapa de calor (heatmap) basado en valores estandarizados (z-score) para visualizar los perfiles agronómicos de los cultivares. Este enfoque permitió identificar patrones relativos de alto y bajo desempeño en las variables evaluadas, facilitando la interpretación comparativa entre materiales.
---

### Software y reproducibilidad

Todos los análisis fueron realizados en Python (versión 3.14), utilizando las siguientes bibliotecas:

pandas para el manejo de datos

scikit-learn para ACP y estandarización

scipy para clustering jerárquico

seaborn y matplotlib para visualización

Todos los scripts, datos y resultados están disponibles en un repositorio público, garantizando la reproducibilidad del análisis y la transparencia del flujo de trabajo.
