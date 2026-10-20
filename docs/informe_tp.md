# Informe — Impacto de la IA en el Empleo (2020-2026)

**Sector asignado:** Tecnología · **Grupo 1** · Fundamentos para la Ciencia de Datos

> Todas las cifras de este informe se generan al ejecutar `python main.py`. Las tablas fuente
> están en `outputs/tablas/` y los gráficos en `outputs/figuras/`.

---

## 1. Resumen ejecutivo

- El dataset crudo tenía **15.050 registros** con anomalías en 9 de sus 20 columnas. Después del
  saneamiento quedaron **14.930 registros válidos** (se descartó el 0,8 %). **1.790 corresponden al sector Tecnología.**
- La mayoría de los valores faltantes **se recuperó con exactitud** gracias a relaciones matemáticas
  internas del dataset, en vez de imputar promedios.
- **Salarios:** la media casi no cambia (USD 90.250 → 90.412, +0,18 %), pero la dispersión crece
  (desvío +3,7 %, Gini 0,226 → 0,233). Solo el 40 % de los trabajadores quedó estable: el 31 % ganó
  más de un 5 % y el 30 % perdió más de un 5 %. **Hay una polarización moderada a nivel individual.**
- **Puestos más vulnerables:** Atención al Cliente (59,7 % de riesgo medio), Camionero/a (59,2 %)
  y Especialista en Marketing (46,6 %). **El nivel educativo no explica el riesgo** (r = −0,002).
- **Perfil más resiliente:** Analista de Datos (bajo riesgo, suba salarial y mayor crecimiento de la
  demanda de habilidades), seguido por Ingeniero/a de Software (el riesgo más bajo del sector).
- La urgencia de re-capacitación crece con la intensidad de la disrupción (r = 0,41): es una
  relación positiva pero moderada.

---

## 2. Fase I — Auditoría de calidad

Diagnóstico del archivo crudo, antes de modificar nada (`outputs/tablas/00_auditoria_calidad.csv`):

| Problema | Columna | Registros |
|---|---|---:|
| Filas duplicadas exactas | todas | 50 |
| Valores nulos | `industry` | 751 |
| Valores nulos | `automation_risk_percent` | 752 |
| Valores nulos | `salary_before_usd` | 753 |
| Valores nulos | `salary_after_usd` | 754 |
| Escritura inconsistente (32 variantes para 8 categorías: `" Technology "`, `TECHNOLOGY`, `technology`…) | `industry` | 2.134 |
| Monto guardado como texto (`"$32,820.29"`) | `salary_before_usd` | 1.348 |
| Monto guardado como texto | `salary_after_usd` | 1 |
| Valor centinela `-99999` (salario negativo) | `salary_before_usd` | 10 |
| Año con formato decimal (`2021.0`) | `year` | 390 |
| Puntaje fuera de la escala 0-100 (máx. 113,07) | `ai_replacement_score` | 95 |
| Salario posterior que no coincide con el % de cambio | `salary_after_usd` | 48 |

### Relaciones internas descubiertas

Al explorar el dataset verificamos que varias columnas son **derivadas** de otras. Estas identidades
se cumplen en el 100 % de los registros completos, salvo en los registros con errores que se describen
más abajo, y fueron clave para la limpieza:

| Identidad | Uso |
|---|---|
| `salary_after = salary_before × (1 + salary_change_percent / 100)` | Recuperar salarios faltantes y detectar errores |
| `skill_transition_pressure = (skill_gap_index + automation_risk_percent) / 2` | Recuperar el riesgo faltante |
| `ai_disruption_intensity = automation_risk_percent × ai_adoption_level / 100` | Verificación cruzada |
| `wage_volatility_index = abs(salary_change_percent)` | Confirmar contradicciones salariales |
| Categoría: Low < 30 ≤ Medium < 60 ≤ High | Coherencia entre % y categoría |

Los 48 salarios incoherentes resultaron ser de tres tipos: 10 valores centinela `-99999`, 10 salarios
posteriores cargados **exactamente ×10** (por ejemplo, USD 915.099 donde correspondían 91.509,90) y
30 registros con salario antes = después pero con un `salary_change_percent` de 5 %.

---

## 3. Bitácora de saneamiento

Orden de ejecución y justificación técnica (`outputs/tablas/00_bitacora_saneamiento.csv`):

| # | Decisión | Registros | Justificación |
|---|---|---:|---|
| 1 | Eliminar duplicados exactos | 50 | Comparten incluso `job_id`: son copias que inflan los conteos y sesgan las medias. |
| 2 | Normalizar `industry` (sin espacios extremos, Formato Título) | 2.127 | Son la misma categoría escrita de distinta forma; si no se unifican, el filtro por sector pierde registros. |
| 3 | Castear salarios a `float` (quitar `$` y `,`) | 1.347 | Un monto guardado como texto no se puede sumar ni promediar. |
| 4 | Castear año a entero | 389 | El año es discreto; `2021.0` y `2021` deben ser el mismo valor. |
| 5 | Centinela `-99999` → nulo | 10 | Un salario negativo es imposible. Se lo trata como faltante y se recupera en el paso 9. |
| 6 | Dividir por 10 los salarios posteriores inflados | 10 | El valor es exactamente 10 veces el esperado: es un error de carga, no un outlier real. |
| 7 | Eliminar contradicciones salariales | 30 | Antes = después pero con cambio de 5 %. No se puede saber qué campo es el correcto, y la volatilidad (= cambio en valor absoluto) tampoco coincide con 5. Es el 0,2 % del total. |
| 8 | Acotar `ai_replacement_score` a [0, 100] | 94 | Es un puntaje 0-100 que acompaña al riesgo (r = 0,96); los excesos son ruido fuera de escala. |
| 9 | Recuperar el salario previo por fórmula | 720 | `antes = después / (1 + cambio/100)`. El cambio % no tiene nulos: el valor recuperado es exacto, no estimado. |
| 10 | Recuperar el salario posterior por fórmula | 709 | `después = antes × (1 + cambio/100)`. También exacto. |
| 11 | Eliminar registros sin ningún salario | 40 | Sin ninguno de los dos salarios no hay base para reconstruirlos; imputar la media inventaría datos. |
| 12 | Recuperar el riesgo de automatización por fórmula | 745 | `riesgo = 2 × presión − brecha`. Exacto. |
| 13 | Recalcular la categoría de riesgo | 0 | Control de coherencia: no hubo cambios, pero garantiza la regla. |
| 14 | Imputar la industria faltante como "Sin dato" | 742 | No se puede deducir de otras columnas. El registro se conserva para análisis globales y queda fuera del análisis por sector. |
| 15 | Traducir al español y asignar tipos | 14.930 | Columnas y valores en español; categóricos como `category`; índice reseteado. |

**¿Por qué no imputar con la media o la mediana?** Porque el dataset permitía recuperar el valor
**verdadero**. Imputar la media habría achicado artificialmente el desvío salarial, que es justamente
lo que necesitamos medir para hablar de polarización.

Al final, `validar_contrato()` verifica que no queden nulos, que los `id_registro` sean únicos y que
todos los salarios sean coherentes. Sobre el dataset limpio, las 5 reglas de negocio dan **0 violaciones**
(`inconsistencias_negocio.csv`).

---

## 4. Fase II — Análisis exploratorio (sector Tecnología, n = 1.790)

### 4.1 Distribución salarial y polarización

| Estadístico | Antes de la IA | Después de la IA | Variación |
|---|---:|---:|---:|
| Media | USD 90.250 | USD 90.412 | +0,18 % |
| Desvío estándar | USD 35.310 | USD 36.609 | **+3,68 %** |
| Mediana | USD 90.528 | USD 90.533 | +0,01 % |
| Coeficiente de variación | 39,1 % | 40,5 % | +3,5 % |
| Percentil 10 | USD 41.365 | USD 41.616 | +0,6 % |
| Percentil 90 | USD 138.993 | USD 140.876 | +1,4 % |
| Ratio P90/P10 | 3,36 | 3,39 | +0,7 % |
| Coeficiente de Gini | 0,226 | 0,233 | **+3,2 %** |

| Resultado individual | Trabajadores | % |
|---|---:|---:|
| Ganancia mayor a +5 % | 548 | 30,6 % |
| Estable (±5 %) | 713 | 39,8 % |
| Pérdida mayor a −5 % | 529 | 29,6 % |

**Interpretación:** en promedio el sector "no se mueve", porque las subas y las bajas se compensan. Pero
esa estabilidad agregada esconde una **polarización moderada**:

- El desvío y el Gini crecen más de un 3 %.
- El percentil 90 sube más que el percentil 10, así que la brecha entre los que más y los que menos ganan se amplía.
- 6 de cada 10 trabajadores tuvieron un cambio salarial mayor al 5 %, con proporciones casi iguales hacia arriba y hacia abajo.

Por cuartil del salario previo, el cambio medio es pequeño en todos los tramos (entre −0,05 % y +0,47 %). Es decir, la
polarización no depende de cuánto ganaba cada persona antes de la IA.

![Salarios antes y después](../outputs/figuras/04_salarios_pre_post.png)

### 4.2 Grado de vulnerabilidad: los 3 roles de mayor riesgo

| Puesto | Riesgo medio | % en categoría "Alto" | Nivel educativo medio |
|---|---:|---:|---:|
| **Atención al Cliente** | 59,7 % | 49,7 % | 3,07 |
| **Camionero/a** | 59,2 % | 47,0 % | 3,08 |
| **Especialista en Marketing** | 46,6 % | 32,6 % | 3,05 |
| _Promedio del sector_ | _45,7 %_ | — | _3,02_ |
| _Ingeniero/a de Software (mínimo)_ | _35,2 %_ | _10,2 %_ | _3,10_ |

**Relación con el nivel educativo:** no existe. La correlación entre nivel educativo y riesgo es nula
(Pearson −0,002; Spearman 0,002), y el riesgo medio por nivel educativo es casi constante (de 44,2 % a 47,0 %).
En los tres puestos de mayor riesgo, los registros se reparten de forma pareja entre los niveles 1 a 5
(entre 17 % y 24 % en cada nivel). En este dataset, **la vulnerabilidad depende de la tarea que realiza el puesto, no de
la credencial educativa**.

### 4.3 Inconsistencias de negocio

Se detectaron y trataron en la limpieza (ver bitácora, pasos 5 a 8 y 13): 10 centinelas, 10 salarios
×10, 30 contradicciones antes = después y 94 puntajes fuera de escala. Se verificó que, después del
tratamiento, ninguna regla de negocio queda violada.

---

## 5. Fase III — Visualización

### Histograma de riesgo

![Histograma de riesgo](../outputs/figuras/01_histograma_riesgo.png)

La distribución es unimodal, centrada en el tramo "Medio", y prácticamente simétrica: la media (45,7 %) y la mediana
(45,5 %) casi coinciden. Por encima del 80 % de riesgo la cantidad de registros cae fuerte. La mayor parte del sector
está en riesgo medio, no extremo.

### Cambio salarial por puesto

![Cambio salarial por puesto](../outputs/figuras/02_cambio_salarial_por_puesto.png)

Los cambios medios son chicos (entre −1,05 % y +1,36 %). Atención al Cliente, que es el puesto de mayor
riesgo, también es el que más pierde salario. Especialista en Marketing (3º en riesgo) es el segundo que más pierde.
Así, en los puestos más expuestos, riesgo alto y pérdida salarial aparecen juntos.

### Urgencia de re-capacitación vs. intensidad de disrupción

![Dispersión](../outputs/figuras/03_dispersion_urgencia_disrupcion.png)

La relación es positiva y moderada (r = 0,41; pendiente 0,28). La nube tiene forma de abanico: con
disrupción baja hay urgencias de todo tipo (de 5 a 70), y con disrupción alta casi no aparecen urgencias bajas.
Una disrupción alta es **suficiente** para que la urgencia sea alta, pero no es **necesaria**. La urgencia
también depende de la brecha de habilidades.

---

## 6. Fase IV — Reflexión crítica

> **Nota para el grupo:** esta sección es un borrador basado en las tablas generadas. Para la defensa oral,
> revísenla y escríbanla con sus propias palabras.

### ¿Qué perfil tecnológico es más resiliente?

Construimos un **índice de resiliencia**: el promedio de los puntajes z de cuatro indicadores. Suman el
cambio salarial y el crecimiento de la demanda de habilidades; restan el riesgo y la urgencia de re-capacitación
(`resiliencia_puestos.csv`).

| Puesto | Riesgo | Cambio salarial | Crec. demanda | Urgencia | Índice |
|---|---:|---:|---:|---:|---:|
| **Analista de Datos** | 37,6 % | +0,50 % | **6,13 %** | 32,6 | **0,97** |
| Ingeniero/a de Software | **35,2 %** | −0,22 % | 5,35 % | **31,4** | 0,65 |
| … | | | | | |
| Atención al Cliente | 59,7 % | −1,05 % | 5,33 % | 41,4 | −1,19 |

El perfil más resiliente es **Analista de Datos**. Es el único que combina un riesgo bajo (2º más bajo del sector),
suba salarial y el mayor crecimiento de demanda de sus habilidades. Ingeniero/a de Software tiene el riesgo
más bajo (solo 10 % de registros en categoría "Alto"), pero su salario medio cae levemente (−0,22 %).

### Tres recomendaciones para un gremio tecnológico (próximos 3 años)

1. **Priorizar la reconversión de Atención al Cliente y Camionero/a.** Tienen ~60 % de riesgo medio,
   casi la mitad de sus registros en categoría "Alto" y la mayor urgencia de re-capacitación (más de 40). Conviene orientar
   los programas hacia las habilidades de los perfiles resilientes (análisis de datos, software).
2. **Negociar formación en habilidades, no solo títulos.** El nivel educativo no protege del
   riesgo (r ≈ 0). Lo que diferencia a los perfiles resilientes es la demanda de sus habilidades,
   así que la capacitación técnica continua debería ser parte de los convenios.
3. **Proteger frente a la volatilidad salarial, no solo frente a la baja del promedio.** El salario medio
   no cambia, pero el 60 % de los trabajadores tuvo variaciones mayores al ±5 % y la desigualdad crece.
   Sugerimos negociar pisos salariales o cláusulas de transición y usar la intensidad de disrupción por puesto
   como alerta temprana de necesidad de re-capacitación.

---

## 7. Limitaciones

- Según el diccionario, los índices y scores son **sintéticos/simulados**. Los resultados sirven para
  ejercitar el método, no para describir el mercado real.
- Dentro de "Tecnología" aparecen puestos como Docente o Camionero/a. Esto es propio de un dataset sintético;
  los interpretamos como roles que trabajan dentro de empresas tecnológicas.
- 742 registros sin industria quedaron fuera del análisis del sector. No se pudo saber a qué sector pertenecían.
- El índice de resiliencia da el mismo peso a sus cuatro indicadores. Con otros pesos el orden de los puestos
  intermedios podría cambiar, aunque los extremos (Analista de Datos arriba, Atención al Cliente abajo) son claros.
