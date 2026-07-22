# Especificación completa de programación y outputs
## Proyecto de grafos: similitud social, cohesión e intermediación en Facebook

## 0. Objetivo general

Implementar de principio a fin el análisis empírico del proyecto:

> **¿La similitud social genera cohesión dentro de grupos, mientras la diversidad social genera intermediación entre grupos en una red de Facebook?**

El pipeline debe ejecutarse de una sola pasada y producir todos los outputs necesarios para el informe final: bases procesadas, estadísticas descriptivas, métricas de red, comunidades, pruebas estadísticas, modelos nulos, tablas, figuras, logs y archivos de control de calidad.

No se debe implementar una versión mínima. La primera versión debe incluir todos los ejercicios necesarios para responder de manera convincente la pregunta de investigación. Posteriormente se revisarán y ajustarán los resultados uno por uno.

---

# 1. Estructura actual de datos

Se asume que el proyecto tiene una estructura similar a:

```text
project_root/
├── notes/
├── twitter/
├── facebook_combined.txt.gz
├── facebook.tar.gz
└── readme-Ego.txt
```

El análisis debe usar exclusivamente los datos de Facebook.

Archivos esperados después de extraer `facebook.tar.gz`:

```text
facebook/
├── 0.edges
├── 0.feat
├── 0.egofeat
├── 0.featnames
├── 0.circles
├── 107.edges
├── 107.feat
├── ...
```

El archivo `facebook_combined.txt.gz` contiene la red agregada.

---

# 2. Principios generales de implementación

1. Todo el análisis debe ser reproducible desde un único script principal.
2. Todos los scripts deben usar rutas relativas respecto a `project_root`.
3. No sobrescribir datos originales.
4. Crear seeds fijas para algoritmos aleatorios.
5. Guardar outputs intermedios para no recalcular métricas costosas.
6. Separar:
   - carga y validación;
   - construcción de redes;
   - construcción de atributos;
   - métricas;
   - análisis estadístico;
   - figuras;
   - exportación.
7. Cada script debe:
   - imprimir progreso;
   - registrar errores;
   - guardar un log;
   - detenerse ante errores críticos;
   - continuar ante problemas menores documentables.
8. Todos los resultados deben guardarse en `outputs/`.
9. Las carpetas de resultados deben comenzar con numerales para preservar el orden lógico.
10. No interpretar resultados dentro del código. El código debe producir evidencia limpia y documentada.
11. No hacer inferencias causales.
12. No combinar ego-networks sin verificar compatibilidad de los atributos.
13. Las métricas de similitud deben calcularse dentro de cada ego-network.
14. Cuando se agrupen resultados, se deben incluir identificadores de ego-network.
15. Toda exclusión de nodos, aristas, redes o atributos debe quedar registrada.

---

# 3. Estructura obligatoria del proyecto

Crear:

```text
project_root/
├── data_raw/
│   ├── facebook_combined.txt.gz
│   ├── facebook.tar.gz
│   └── readme-Ego.txt
│
├── data_processed/
│   ├── extracted_facebook/
│   ├── graphs/
│   ├── node_features/
│   ├── communities/
│   └── analytic/
│
├── src/
│   ├── 00_config.py
│   ├── 01_extract_and_inventory.py
│   ├── 02_validate_raw_data.py
│   ├── 03_build_ego_graphs.py
│   ├── 04_parse_features.py
│   ├── 05_construct_sample.py
│   ├── 06_descriptive_networks.py
│   ├── 07_detect_communities.py
│   ├── 08_compute_social_similarity.py
│   ├── 09_compute_cohesion.py
│   ├── 10_compute_brokerage.py
│   ├── 11_build_node_level_dataset.py
│   ├── 12_statistical_analysis.py
│   ├── 13_permutation_tests.py
│   ├── 14_robustness_checks.py
│   ├── 15_make_figures.py
│   ├── 16_make_tables.py
│   ├── 17_generate_sample_text.py
│   └── run_all.py
│
├── outputs/
│   ├── 0_logs/
│   ├── 1_data_inventory/
│   ├── 2_sample_definition/
│   ├── 3_network_descriptives/
│   ├── 4_feature_descriptives/
│   ├── 5_communities/
│   ├── 6_social_similarity/
│   ├── 7_cohesion/
│   ├── 8_brokerage/
│   ├── 9_main_results/
│   ├── 10_null_models/
│   ├── 11_robustness/
│   ├── 12_figures/
│   ├── 13_tables/
│   └── 14_report_inputs/
│
├── requirements.txt
├── README.md
└── run_project.py
```

---

# 4. Configuración general

## Archivo `src/00_config.py`

Definir como mínimo:

```python
RANDOM_SEED = 7745
N_PERMUTATIONS_MAIN = 1000
N_PERMUTATIONS_FAST = 200
MIN_VALID_FEATURES_NODE = 1
MIN_NODES_EGO = 10
MIN_EDGES_EGO = 10
USE_LARGEST_CONNECTED_COMPONENT_FOR_PATHS = True
COMMUNITY_METHOD = "louvain"
COMMUNITY_RESOLUTION = 1.0
BETWEENNESS_APPROX_THRESHOLD = 5000
BETWEENNESS_APPROX_K = 500
ALPHA = 0.05
```

También incluir todas las rutas del proyecto.

Guardar copia de la configuración utilizada en:

```text
outputs/0_logs/config_used.json
```

---

# 5. Bloque explícito de definición de muestra

Este bloque es obligatorio y debe producir resultados concretos para complementar la sección de datos del informe.

## 5.1. Universo bruto

El universo inicial corresponde a todos los ego-networks contenidos en `facebook.tar.gz`, junto con sus archivos:

- `.edges`
- `.feat`
- `.egofeat`
- `.featnames`
- `.circles`

También se debe inspeccionar `facebook_combined.txt.gz` como referencia de la red agregada, pero el análisis principal debe realizarse a nivel de ego-network para preservar la correspondencia entre nodos y atributos.

## 5.2. Criterios de inclusión de ego-networks

Una ego-network es elegible si:

1. Tiene archivo `.edges`.
2. Tiene archivo `.feat`.
3. Tiene archivo `.featnames`.
4. Los identificadores de nodos pueden alinearse correctamente.
5. Tiene al menos `MIN_NODES_EGO` nodos.
6. Tiene al menos `MIN_EDGES_EGO` aristas.
7. Contiene al menos una dimensión de atributos válida.
8. No presenta errores estructurales críticos.

## 5.3. Criterios de inclusión de nodos

Un nodo entra en el análisis social si:

1. Pertenece a una ego-network elegible.
2. Tiene al menos un atributo usable.
3. Tiene grado mayor o igual a uno.
4. Para clustering, tiene grado mayor o igual a dos.
5. Para métricas de caminos, pertenece a la componente conexa principal cuando corresponda.

Los nodos sin atributos:

- deben conservarse en el grafo para métricas estructurales;
- deben excluirse de medidas de similitud y diversidad;
- deben ser identificados con una bandera `has_valid_features`.

## 5.4. Muestras analíticas

Construir y guardar explícitamente:

### Muestra A: descriptiva estructural

Todos los nodos de ego-networks elegibles.

### Muestra B: similitud social

Nodos con atributos válidos y al menos un vecino con atributos válidos.

### Muestra C: cohesión

Nodos de la muestra B con grado mayor o igual a dos.

### Muestra D: intermediación

Nodos de la muestra B pertenecientes a la componente conexa principal usada para betweenness.

### Muestra E: regresiones principales

Intersección de:

- atributos válidos;
- similitud o diversidad definida;
- grado válido;
- clustering o betweenness disponible;
- participation coefficient disponible;
- ego-network elegible.

## 5.5. Output obligatorio de muestra

Crear:

```text
outputs/2_sample_definition/sample_flow.csv
outputs/2_sample_definition/sample_flow_by_ego.csv
outputs/2_sample_definition/exclusion_reasons.csv
outputs/2_sample_definition/feature_coverage_by_ego.csv
outputs/2_sample_definition/final_sample_summary.json
outputs/2_sample_definition/sample_definition.md
outputs/2_sample_definition/sample_definition.tex
```

La tabla de flujo debe mostrar:

```text
Stage
Number of ego-networks
Number of nodes
Number of edges
Nodes excluded
Reason
Share retained
```

El archivo `sample_definition.md` debe producir automáticamente un párrafo tipo:

> The raw dataset contains X ego-networks, Y unique node records, and Z friendship ties. After excluding ego-networks without valid feature files or with insufficient network size, the final analytical sample contains ...

No inventar cifras. Deben provenir del pipeline.

---

# 6. Ejercicio 1: extracción e inventario

## Script

```text
src/01_extract_and_inventory.py
```

## Tareas

1. Detectar si `facebook.tar.gz` ya fue extraído.
2. Extraerlo en `data_processed/extracted_facebook/`.
3. Enumerar todos los archivos por extensión.
4. Identificar todos los ego IDs.
5. Verificar qué archivos existen para cada ego.
6. Leer tamaño en bytes y número de filas.
7. Inspeccionar `facebook_combined.txt.gz`.
8. Guardar un inventario completo.

## Outputs

```text
outputs/1_data_inventory/file_inventory.csv
outputs/1_data_inventory/ego_file_matrix.csv
outputs/1_data_inventory/archive_summary.json
outputs/1_data_inventory/missing_files.csv
```

---

# 7. Ejercicio 2: validación de datos brutos

## Script

```text
src/02_validate_raw_data.py
```

## Validaciones

### Aristas

- duplicados;
- self-loops;
- identificadores no válidos;
- aristas repetidas en sentido inverso;
- nodos presentes en aristas pero ausentes en features;
- nodos presentes en features pero ausentes en aristas.

### Features

- dimensionalidad consistente;
- número de columnas;
- valores distintos de 0/1;
- filas duplicadas;
- nodos duplicados;
- columnas sin variación;
- columnas completamente vacías;
- compatibilidad con `.featnames`.

### Ego feature

- longitud compatible con `.feat`;
- existencia del ego;
- posibilidad de añadir el ego al grafo.

### Círculos

- IDs válidos;
- nodos desconocidos;
- círculos vacíos;
- solapamiento entre círculos;
- cobertura de nodos.

## Outputs

```text
outputs/1_data_inventory/data_quality_summary.csv
outputs/1_data_inventory/data_quality_by_ego.csv
outputs/1_data_inventory/invalid_edges.csv
outputs/1_data_inventory/invalid_feature_rows.csv
outputs/1_data_inventory/feature_dimension_check.csv
outputs/1_data_inventory/circle_validation.csv
```

---

# 8. Ejercicio 3: construcción de ego-networks

## Script

```text
src/03_build_ego_graphs.py
```

## Construcción

Para cada ego ID:

1. Cargar `.edges`.
2. Crear grafo no dirigido y no ponderado.
3. Añadir el ego central.
4. Conectar el ego a todos los alters incluidos en su ego-network, de acuerdo con la estructura original del dataset.
5. Eliminar self-loops.
6. Eliminar duplicados.
7. Conservar todos los nodos válidos.
8. Crear versión completa.
9. Crear versión de componente conexa principal.
10. Guardar ambos grafos.

## Outputs

```text
data_processed/graphs/ego_<id>_full.gpickle
data_processed/graphs/ego_<id>_lcc.gpickle
outputs/3_network_descriptives/graph_build_summary.csv
```

## Variables básicas por ego-network

- `ego_id`
- `n_nodes_full`
- `n_edges_full`
- `n_components`
- `largest_component_nodes`
- `largest_component_share`
- `density`
- `mean_degree`
- `median_degree`
- `max_degree`
- `isolates`
- `self_loops_removed`
- `duplicate_edges_removed`

---

# 9. Ejercicio 4: parseo y armonización de atributos

## Script

```text
src/04_parse_features.py
```

## Objetivo

Reconstruir los vectores binarios y agrupar columnas según las categorías disponibles en `.featnames`.

## Tareas

1. Leer cada `.featnames`.
2. Extraer:
   - índice de feature;
   - categoría general;
   - valor anonimizado;
   - texto original anonimizado.
3. Crear diccionario por ego-network.
4. Determinar si las categorías generales son comparables entre redes.
5. No asumir que el valor anonimizado `feature 1` significa lo mismo entre ego-networks.
6. Construir:
   - vector completo;
   - vectores por categoría;
   - conteo de features activas;
   - banderas de datos faltantes.

## Categorías esperadas

Cuando existan:

- education
- work
- location
- hometown
- religion
- political
- gender
- birthday
- languages
- other

## Outputs

```text
data_processed/node_features/node_features_long.csv
data_processed/node_features/node_features_wide.parquet
data_processed/node_features/feature_dictionary.csv
outputs/4_feature_descriptives/feature_categories_by_ego.csv
outputs/4_feature_descriptives/feature_prevalence.csv
outputs/4_feature_descriptives/feature_missingness.csv
outputs/4_feature_descriptives/feature_variation.csv
outputs/4_feature_descriptives/comparability_report.md
```

---

# 10. Ejercicio 5: construcción definitiva de la muestra

## Script

```text
src/05_construct_sample.py
```

Aplicar las reglas de la sección 5.

## Outputs adicionales

```text
data_processed/analytic/eligible_egos.csv
data_processed/analytic/eligible_nodes.csv
data_processed/analytic/node_sample_flags.parquet
```

Variables mínimas:

- `ego_id`
- `node_id`
- `in_full_graph`
- `in_lcc`
- `has_features`
- `n_active_features`
- `degree`
- `eligible_similarity`
- `eligible_clustering`
- `eligible_betweenness`
- `eligible_main_regression`
- `exclusion_reason`

---

# 11. Ejercicio 6: estadísticas descriptivas de redes

## Script

```text
src/06_descriptive_networks.py
```

## Métricas por ego-network

- nodos;
- aristas;
- densidad;
- componentes;
- tamaño de componente principal;
- grado promedio;
- mediana del grado;
- grado máximo;
- desviación estándar del grado;
- clustering promedio;
- transitivity;
- assortativity por grado;
- diámetro de la LCC;
- average shortest path length de la LCC;
- número de triángulos;
- proporción de nodos en triángulos;
- número de puentes;
- número de articulation points.

## Distribuciones a guardar

- grado por nodo;
- clustering por nodo;
- component size;
- triangle count;
- shortest path summary.

## Outputs

```text
outputs/3_network_descriptives/network_summary_by_ego.csv
outputs/3_network_descriptives/network_summary_pooled.csv
outputs/3_network_descriptives/node_degree_distribution.csv
outputs/3_network_descriptives/components_by_ego.csv
outputs/3_network_descriptives/bridges_and_articulation.csv
```

---

# 12. Ejercicio 7: detección de comunidades

## Script

```text
src/07_detect_communities.py
```

## Método principal

Louvain con:

- seed fija;
- resolución 1.0;
- ejecución separada por ego-network.

## Robustez

- greedy modularity;
- opcionalmente spectral clustering si es requerido por el curso.

## Outputs por ego-network

- asignación de comunidad;
- número de comunidades;
- tamaño de comunidades;
- modularidad;
- cobertura;
- conductance promedio si es viable;
- estabilidad del algoritmo bajo varias seeds.

## Estabilidad

Ejecutar Louvain con al menos 20 seeds por ego-network y guardar:

- modularidad por seed;
- número de comunidades;
- Adjusted Rand Index entre particiones;
- partición final seleccionada como la de mayor modularidad.

## Comparación con círculos declarados

Cuando `.circles` esté disponible:

- overlap entre comunidad y círculo;
- Jaccard;
- precision;
- recall;
- F1;
- NMI o ARI cuando sea metodológicamente válido;
- advertir que los círculos pueden solaparse.

## Outputs

```text
data_processed/communities/community_assignments.parquet
outputs/5_communities/community_summary_by_ego.csv
outputs/5_communities/community_sizes.csv
outputs/5_communities/louvain_stability.csv
outputs/5_communities/community_circle_overlap.csv
outputs/5_communities/modularity_comparison.csv
```

---

# 13. Ejercicio 8: similitud social y diversidad

## Script

```text
src/08_compute_social_similarity.py
```

## 13.1. Similitud por arista

Calcular para cada arista válida:

### Jaccard general

\[
S_{ij}
=
\frac{|A_i\cap A_j|}
{|A_i\cup A_j|}
\]

### Similitud por categoría

Cuando sea posible:

- education similarity;
- work similarity;
- location similarity;
- political similarity;
- religion similarity;
- gender similarity;
- hometown similarity.

### Cosine similarity

Usar como robustez:

\[
\cos(i,j)
=
\frac{x_i^\top x_j}
{\|x_i\|\|x_j\|}
\]

## 13.2. Similitud nodal

Para cada nodo:

- promedio;
- mediana;
- mínimo;
- máximo;
- desviación estándar;
- share de vecinos con similitud positiva;
- share de vecinos con al menos una coincidencia.

## 13.3. Diversidad nodal

Construir:

### Complemento de similitud

\[
D_i^{(1)}=1-\bar S_i
\]

### Entropía de categorías

Cuando exista una categoría con valores reconstruibles:

\[
D_i^{(2)}
=
-\frac{\sum_g p_{ig}\log(p_{ig})}{\log(G_i)}
\]

### Diversidad de círculos

- número de círculos alcanzados;
- entropía de círculos;
- share de conexiones fuera del círculo dominante.

## Outputs

```text
data_processed/analytic/edge_similarity.parquet
data_processed/analytic/node_similarity_diversity.parquet
outputs/6_social_similarity/similarity_summary.csv
outputs/6_social_similarity/similarity_by_category.csv
outputs/6_social_similarity/diversity_summary.csv
outputs/6_social_similarity/within_vs_between_similarity.csv
```

---

# 14. Ejercicio 9: cohesión local

## Script

```text
src/09_compute_cohesion.py
```

## Métricas principales

### Local clustering coefficient

\[
C_i
=
\frac{2T_i}{k_i(k_i-1)}
\]

### Ego-network density excluding ego

La densidad entre los vecinos de cada nodo.

### Triangle count

Número de triángulos por nodo.

### Average edge embeddedness

Número promedio de vecinos comunes por arista incidente.

### Redundancia estructural

Cuando sea viable:

- Burt's constraint;
- effective size;
- efficiency.

## Outputs

```text
data_processed/analytic/node_cohesion.parquet
outputs/7_cohesion/cohesion_summary.csv
outputs/7_cohesion/cohesion_by_ego.csv
outputs/7_cohesion/cohesion_by_degree_bin.csv
outputs/7_cohesion/embeddedness_summary.csv
```

---

# 15. Ejercicio 10: intermediación y brokerage

## Script

```text
src/10_compute_brokerage.py
```

## Métricas

### Betweenness centrality

- exacta en redes pequeñas;
- aproximada en redes por encima del umbral;
- normalizada;
- guardar método usado.

### Participation coefficient

\[
P_i
=
1-
\sum_c
\left(
\frac{k_{ic}}{k_i}
\right)^2
\]

### Number of communities reached

Número de comunidades distintas entre los vecinos.

### Within-module degree z-score

\[
z_i
=
\frac{k_{i,c}-\bar{k}_c}{\sigma_{k_c}}
\]

### Bridge status

- arista puente incidente;
- articulation point;
- nodo que conecta dos o más comunidades;
- bridging coefficient si se implementa.

### Structural holes

- Burt's constraint;
- effective size;
- efficiency.

## Outputs

```text
data_processed/analytic/node_brokerage.parquet
outputs/8_brokerage/brokerage_summary.csv
outputs/8_brokerage/brokerage_by_ego.csv
outputs/8_brokerage/top_broker_nodes.csv
outputs/8_brokerage/top_degree_vs_top_betweenness.csv
outputs/8_brokerage/community_connector_roles.csv
```

---

# 16. Ejercicio 11: base analítica final a nivel nodo

## Script

```text
src/11_build_node_level_dataset.py
```

Combinar:

- flags de muestra;
- atributos;
- similitud;
- diversidad;
- grado;
- clustering;
- triangles;
- embeddedness;
- betweenness;
- participation coefficient;
- community assignment;
- community count;
- circle measures;
- Burt metrics;
- ego-network controls.

## Archivo principal

```text
data_processed/analytic/node_level_analysis.parquet
data_processed/analytic/node_level_analysis.csv
```

## Diccionario

```text
outputs/14_report_inputs/node_level_dictionary.csv
```

Cada variable debe tener:

- nombre;
- definición;
- fórmula;
- rango;
- tipo;
- fuente;
- notas.

---

# 17. Ejercicio 12: análisis estadístico principal

## Script

```text
src/12_statistical_analysis.py
```

## 17.1. Correlaciones

Calcular Pearson y Spearman para:

- similarity vs clustering;
- similarity vs ego density;
- diversity vs betweenness;
- diversity vs participation coefficient;
- diversity vs number of communities reached;
- degree vs betweenness;
- degree vs clustering;
- similarity vs degree;
- diversity vs degree.

Guardar:

- coeficiente;
- p-value;
- N;
- intervalo de confianza bootstrap.

## 17.2. Regresiones principales

### Modelo 1: cohesión

\[
C_i
=
\alpha
+
\beta_1 Similarity_i
+
\varepsilon_i
\]

### Modelo 2: cohesión con grado

\[
C_i
=
\alpha
+
\beta_1 Similarity_i
+
\beta_2 \log(1+k_i)
+
\mu_e
+
\varepsilon_i
\]

### Modelo 3: intermediación

\[
\log(1+B_i)
=
\alpha
+
\gamma_1 Diversity_i
+
\varepsilon_i
\]

### Modelo 4: intermediación con grado

\[
\log(1+B_i)
=
\alpha
+
\gamma_1 Diversity_i
+
\gamma_2 \log(1+k_i)
+
\mu_e
+
\varepsilon_i
\]

### Modelo 5: participation coefficient

\[
P_i
=
\alpha
+
\delta_1 Diversity_i
+
\delta_2 \log(1+k_i)
+
\mu_e
+
\varepsilon_i
\]

### Modelo 6: comunidades alcanzadas

Poisson o negative binomial si corresponde:

\[
E[Communities_i|X_i]
=
\exp(
\alpha+\theta_1 Diversity_i+\theta_2\log(1+k_i)+\mu_e
)
\]

## 17.3. Especificaciones

- errores robustos HC3;
- fixed effects por ego-network;
- estandarización de regresores principales;
- reportar coeficientes estandarizados;
- reportar N, R² y adjusted R²;
- verificar heterocedasticidad;
- revisar residuos;
- VIF;
- leverage y Cook's distance;
- no eliminar outliers sin reportar.

## 17.4. Modelos alternativos adecuados a la variable dependiente

Para clustering y participation coefficient, que están en \([0,1]\):

- OLS como especificación principal interpretable;
- fractional logit como robustez, si es viable.

Para betweenness:

- `log1p`;
- rank-based regression como robustez.

## Outputs

```text
outputs/9_main_results/correlations.csv
outputs/9_main_results/regression_main.csv
outputs/9_main_results/regression_diagnostics.csv
outputs/9_main_results/model_fit_summary.csv
outputs/9_main_results/standardized_effects.csv
outputs/9_main_results/results_by_ego.csv
```

---

# 18. Ejercicio 13: modelos nulos y permutation tests

## Script

```text
src/13_permutation_tests.py
```

## Modelo nulo principal

Dentro de cada ego-network:

1. Mantener fija la red.
2. Permutar vectores de atributos entre nodos.
3. Recalcular similitud y diversidad.
4. Reestimar:
   - Spearman similarity-clustering;
   - Spearman diversity-betweenness;
   - Spearman diversity-participation;
   - coeficientes principales de regresión.

## Número de permutaciones

- principal: 1,000;
- guardar seed por iteración;
- permitir modo rápido de 200.

## p-value empírico

\[
p
=
\frac{
1+\sum_{r=1}^R
\mathbf{1}(|T_r|\geq |T_{obs}|)
}{
R+1
}
\]

## Modelo nulo estructural adicional

Generar configuration-model graphs por ego-network preservando aproximadamente la secuencia de grados.

Objetivo:

- comparar clustering observado;
- comparar modularidad;
- comparar betweenness promedio;
- evaluar cuánto de la estructura se explica por grado.

No usar Erdős--Rényi como único modelo nulo.

## Outputs

```text
outputs/10_null_models/permutation_statistics.csv
outputs/10_null_models/permutation_distributions.parquet
outputs/10_null_models/empirical_pvalues.csv
outputs/10_null_models/configuration_model_summary.csv
outputs/10_null_models/observed_vs_null.csv
```

---

# 19. Ejercicio 14: robustez

## Script

```text
src/14_robustness_checks.py
```

Ejecutar todas las siguientes verificaciones.

## 19.1. Medidas alternativas de similitud

- Jaccard;
- cosine similarity;
- category-specific matching.

## 19.2. Medidas alternativas de diversidad

- \(1-\) similarity;
- entropy;
- circle diversity.

## 19.3. Medidas alternativas de cohesión

- clustering;
- ego density;
- embeddedness;
- Burt's constraint.

## 19.4. Medidas alternativas de brokerage

- betweenness;
- participation coefficient;
- communities reached;
- effective size;
- articulation-point indicator.

## 19.5. Restricciones de muestra

- excluir degree 1;
- excluir top 1% de degree;
- excluir top 1% de betweenness;
- solo LCC;
- solo nodos con cobertura completa de features;
- solo ego-networks grandes;
- solo ego-networks con buena modularidad;
- estimaciones separadas por ego-network.

## 19.6. Comunidades

- Louvain;
- greedy modularity;
- varias resoluciones:
  - 0.5;
  - 1.0;
  - 1.5;
  - 2.0.

## 19.7. Inferencia

- HC3;
- clustered standard errors si el número de ego-networks lo permite;
- bootstrap por ego-network;
- bootstrap por nodo dentro de ego-network como análisis secundario.

## Outputs

```text
outputs/11_robustness/robustness_summary.csv
outputs/11_robustness/alternative_similarity.csv
outputs/11_robustness/alternative_diversity.csv
outputs/11_robustness/alternative_community_methods.csv
outputs/11_robustness/sample_restrictions.csv
outputs/11_robustness/bootstrap_results.csv
```

---

# 20. Ejercicio 15: figuras obligatorias

## Script

```text
src/15_make_figures.py
```

Todas las figuras deben guardarse en PNG y PDF, con calidad de publicación.

## Figura 1: estructura de las ego-networks

Panel o distribución de:

- nodos;
- aristas;
- densidad;
- clustering;
- modularidad.

Archivos:

```text
outputs/12_figures/fig_01_network_overview.png
outputs/12_figures/fig_01_network_overview.pdf
```

## Figura 2: similitud y cohesión

Scatterplot o binscatter:

- X: average Jaccard similarity;
- Y: local clustering;
- línea de ajuste;
- transparencia por densidad;
- degree como tamaño o control gráfico.

```text
fig_02_similarity_clustering.*
```

## Figura 3: diversidad y betweenness

- X: diversity;
- Y: log(1 + betweenness);
- ajuste no paramétrico o lineal.

```text
fig_03_diversity_betweenness.*
```

## Figura 4: diversidad y participation coefficient

```text
fig_04_diversity_participation.*
```

## Figura 5: popularidad versus intermediación

Comparar:

- degree rank;
- betweenness rank;
- participation rank.

Resaltar nodos que tienen degree moderado pero betweenness alto.

```text
fig_05_degree_vs_brokerage.*
```

## Figura 6: ejemplos de nodos

Seleccionar automáticamente:

1. nodo con alta similitud y alto clustering;
2. nodo con alta diversidad y alto betweenness;
3. nodo con alto degree pero bajo participation;
4. nodo con degree moderado y alta intermediación.

Mostrar ego-network local coloreada por comunidad.

```text
fig_06_node_archetypes.*
```

## Figura 7: comunidades

Visualización de una ego-network representativa:

- nodos coloreados por comunidad;
- tamaño por betweenness;
- layout reproducible.

```text
fig_07_community_structure.*
```

## Figura 8: permutation tests

Tres paneles o tres figuras separadas:

- similarity-clustering;
- diversity-betweenness;
- diversity-participation.

Mostrar distribución nula y estadístico observado.

```text
fig_08a_null_similarity_clustering.*
fig_08b_null_diversity_betweenness.*
fig_08c_null_diversity_participation.*
```

## Figura 9: heterogeneidad por ego-network

Coeficientes por ego-network con intervalos de confianza.

```text
fig_09_heterogeneity_by_ego.*
```

## Figura 10: robustez

Specification curve o coefplot de todas las especificaciones.

```text
fig_10_robustness_specification_curve.*
```

---

# 21. Ejercicio 16: tablas obligatorias

## Script

```text
src/16_make_tables.py
```

Exportar cada tabla en:

- CSV;
- LaTeX;
- Markdown.

## Tabla 1: definición de muestra

```text
tab_01_sample_flow.*
```

## Tabla 2: estadísticas descriptivas por ego-network

```text
tab_02_network_descriptives.*
```

## Tabla 3: descriptivas a nivel nodo

Variables:

- degree;
- similarity;
- diversity;
- clustering;
- betweenness;
- participation;
- communities reached;
- constraint;
- effective size.

```text
tab_03_node_descriptives.*
```

## Tabla 4: correlaciones

```text
tab_04_correlations.*
```

## Tabla 5: regresiones principales

```text
tab_05_main_regressions.*
```

## Tabla 6: permutation tests

```text
tab_06_permutation_tests.*
```

## Tabla 7: heterogeneidad por ego-network

```text
tab_07_results_by_ego.*
```

## Tabla 8: robustez

```text
tab_08_robustness.*
```

## Tabla 9: top nodes

- top degree;
- top betweenness;
- top participation;
- top effective size.

```text
tab_09_top_nodes.*
```

---

# 22. Ejercicio 17: generación automática de insumos para el informe

## Script

```text
src/17_generate_sample_text.py
```

Crear:

```text
outputs/14_report_inputs/data_section_facts.md
outputs/14_report_inputs/data_section_facts.tex
outputs/14_report_inputs/methodology_facts.md
outputs/14_report_inputs/results_key_numbers.md
outputs/14_report_inputs/results_key_numbers.tex
outputs/14_report_inputs/result_interpretation_flags.json
```

## Contenido

### Data section facts

- número de ego-networks;
- nodos;
- aristas;
- muestra final;
- exclusiones;
- cobertura de atributos;
- componente principal;
- método de comunidad.

### Results key numbers

- correlaciones principales;
- coeficientes;
- p-values;
- permutation p-values;
- modularidad;
- heterogeneidad;
- robustez.

### Flags interpretativos

Ejemplo:

```json
{
  "similarity_clustering_positive": true,
  "similarity_clustering_significant": true,
  "diversity_betweenness_positive": false,
  "diversity_participation_positive": true,
  "results_robust_to_degree": true,
  "heterogeneity_high": false
}
```

No generar conclusiones definitivas. Solo hechos y banderas.

---

# 23. Script maestro

## `src/run_all.py`

Debe ejecutar en orden:

```python
STEPS = [
    "01_extract_and_inventory.py",
    "02_validate_raw_data.py",
    "03_build_ego_graphs.py",
    "04_parse_features.py",
    "05_construct_sample.py",
    "06_descriptive_networks.py",
    "07_detect_communities.py",
    "08_compute_social_similarity.py",
    "09_compute_cohesion.py",
    "10_compute_brokerage.py",
    "11_build_node_level_dataset.py",
    "12_statistical_analysis.py",
    "13_permutation_tests.py",
    "14_robustness_checks.py",
    "15_make_figures.py",
    "16_make_tables.py",
    "17_generate_sample_text.py",
]
```

## Requisitos

- medir tiempo por script;
- registrar memoria;
- guardar status;
- escribir traceback;
- no ocultar warnings;
- resumir outputs generados;
- verificar que cada archivo obligatorio exista.

## Output

```text
outputs/0_logs/pipeline.log
outputs/0_logs/pipeline_status.csv
outputs/0_logs/runtime_summary.csv
outputs/0_logs/output_manifest.csv
outputs/0_logs/warnings.log
```

---

# 24. Auditoría automática de outputs

Al final, verificar:

- todos los scripts ejecutados;
- todos los outputs obligatorios existen;
- no hay tablas vacías;
- no hay figuras vacías;
- no hay métricas fuera de rango;
- no hay duplicados en la base analítica;
- no hay valores imposibles;
- las muestras coinciden entre tablas;
- las cifras del `.md` y `.tex` provienen de archivos reales;
- las seeds están guardadas;
- las versiones de paquetes están registradas.

Crear:

```text
outputs/0_logs/final_audit.csv
outputs/0_logs/final_audit.md
outputs/0_logs/package_versions.txt
```

---

# 25. Reglas de calidad de resultados

## Métricas

- clustering debe estar entre 0 y 1;
- participation coefficient debe estar entre 0 y 1;
- Jaccard debe estar entre 0 y 1;
- betweenness normalizada debe estar entre 0 y 1;
- modularidad debe estar dentro de su rango teórico;
- degree debe ser entero no negativo.

## Regresiones

- reportar N;
- reportar missingness;
- reportar R²;
- no ocultar signos inesperados;
- no seleccionar modelos solo por significancia;
- reportar multicolinealidad;
- reportar observaciones influyentes;
- estandarizar únicamente para comparabilidad, no para reemplazar resultados originales.

## Modelos nulos

- mantener estructura fija en permutaciones;
- permutar dentro de ego-network;
- guardar toda la distribución nula;
- reportar seed;
- no reportar solo p-values.

## Comunidades

- guardar asignaciones;
- guardar modularidad;
- guardar estabilidad;
- no interpretar automáticamente comunidades como grupos sociales reales.

---

# 26. Resultados mínimos que deben existir al finalizar

El pipeline se considera completo solo si produce:

1. Inventario completo de archivos.
2. Diagnóstico de calidad.
3. Definición exacta de muestra.
4. Ego-networks construidas.
5. Atributos parseados.
6. Comunidades detectadas.
7. Base por arista con similitud.
8. Base por nodo con diversidad.
9. Métricas de cohesión.
10. Métricas de intermediación.
11. Base analítica final.
12. Correlaciones.
13. Regresiones principales.
14. Modelos nulos.
15. Permutation tests.
16. Robustez.
17. Heterogeneidad por ego-network.
18. Figuras principales.
19. Tablas principales.
20. Texto automático para completar la sección de datos.
21. Manifest de outputs.
22. Auditoría final.

---

# 27. Orden recomendado para revisar resultados después de la primera corrida

Una vez terminado el pipeline, revisar en este orden:

1. `outputs/0_logs/final_audit.md`
2. `outputs/2_sample_definition/sample_definition.md`
3. `outputs/3_network_descriptives/network_summary_by_ego.csv`
4. `outputs/4_feature_descriptives/comparability_report.md`
5. `outputs/5_communities/community_summary_by_ego.csv`
6. `outputs/6_social_similarity/similarity_summary.csv`
7. `outputs/7_cohesion/cohesion_summary.csv`
8. `outputs/8_brokerage/brokerage_summary.csv`
9. `outputs/9_main_results/correlations.csv`
10. `outputs/9_main_results/regression_main.csv`
11. `outputs/10_null_models/empirical_pvalues.csv`
12. `outputs/11_robustness/robustness_summary.csv`
13. `outputs/12_figures/`
14. `outputs/13_tables/`
15. `outputs/14_report_inputs/results_key_numbers.md`

---

# 28. Instrucción final para el agente de programación

Implementar todo el pipeline descrito arriba, ejecutarlo completamente y corregir errores hasta que:

- todos los scripts terminen;
- todos los outputs obligatorios existan;
- la auditoría final no reporte fallos críticos;
- la base analítica sea consistente;
- las tablas y figuras estén listas para revisión;
- el bloque de definición de muestra esté completamente cuantificado.

No reducir el alcance del análisis sin documentar explícitamente una limitación técnica real. Ante una decisión metodológica ambigua, conservar ambas variantes como análisis principal y robustez, y registrar la decisión en los logs.
