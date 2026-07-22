# Proyecto de grafos: similitud social, cohesión e intermediación en Facebook

## 1. Pregunta de investigación

**¿La similitud social genera cohesión dentro de los grupos, mientras la diversidad social genera intermediación entre grupos en una red de Facebook?**

La pregunta busca evaluar dos mecanismos sociales distintos:

1. **Bonding social capital**: los individuos conectados con personas socialmente similares tienden a pertenecer a vecindarios más densos, redundantes y cohesionados.
2. **Bridging social capital**: los individuos cuyos contactos son socialmente diversos tienden a conectar comunidades diferentes y a ocupar posiciones de intermediación.

La idea central es distinguir entre dos formas de centralidad social:

- Estar bien integrado dentro de un grupo.
- Conectar grupos que, de otro modo, estarían separados.

---

## 2. Motivación sociológica

Las redes personales suelen organizarse alrededor de contextos sociales como universidad, trabajo, familia, lugar de origen, religión o afiliación política. La similitud entre individuos puede facilitar la formación de vínculos y producir grupos altamente cohesionados.

Sin embargo, una red compuesta únicamente por vínculos entre personas similares puede ser redundante: muchos contactos conocen a las mismas personas y entregan información parecida. En contraste, los individuos que conectan personas de diferentes entornos pueden acceder a información, oportunidades y recursos más diversos.

El proyecto pretende estudiar si existe un trade-off entre:

\[
\text{cohesión local}
\quad\text{e}\quad
\text{intermediación estructural}.
\]

---

## 3. Datos

### Fuente

Stanford Network Analysis Project (SNAP):

- Dataset: `ego-Facebook`
- Página: https://snap.stanford.edu/data/ego-Facebook.html

### Archivos relevantes

El dataset puede incluir:

- `facebook_combined.txt`: red agregada de amistades.
- `*.edges`: aristas de cada ego-network.
- `*.feat`: atributos de los nodos.
- `*.egofeat`: atributos del ego central.
- `*.featnames`: significado y categoría de cada atributo.
- `*.circles`: círculos sociales declarados por el ego.

### Unidad de análisis

La unidad principal será el **nodo**, entendido como un usuario de Facebook.

### Representación de la red

- Red no dirigida.
- Nodos: usuarios.
- Aristas: relaciones de amistad.
- Sin ponderación, salvo que posteriormente se construya una medida de similitud o solapamiento.

### Primera decisión empírica

Antes de programar el análisis final, se debe verificar:

1. Qué atributos pueden reconstruirse de manera consistente.
2. Cuántos valores faltantes existen.
3. Si los atributos son comparables entre ego-networks.
4. Si conviene trabajar con la red agregada o con ego-networks separadas.

La opción preferida inicialmente es trabajar con las ego-networks por separado para evitar mezclar codificaciones de atributos incompatibles.

---

## 4. Hipótesis

### Hipótesis 1: similitud y cohesión

Los nodos cuyos contactos presentan mayor similitud social tendrán vecindarios más cohesionados.

\[
H_1:
\text{Similitud social}_i
\longrightarrow
\text{mayor clustering local}_i
\]

También se espera:

\[
\text{Similitud social}_i
\longrightarrow
\text{mayor redundancia}_i
\]

### Hipótesis 2: diversidad e intermediación

Los nodos cuyos contactos pertenecen a categorías sociales más diversas tendrán mayor capacidad de conectar comunidades distintas.

\[
H_2:
\text{Diversidad social}_i
\longrightarrow
\text{mayor betweenness}_i
\]

También se espera:

\[
\text{Diversidad social}_i
\longrightarrow
\text{mayor participation coefficient}_i
\]

### Hipótesis 3: mecanismos distintos

El grado no debe interpretarse automáticamente como intermediación.

\[
H_3:
\text{degree centrality}
\neq
\text{bridging centrality}
\]

Un nodo puede tener muchas conexiones dentro de una comunidad homogénea sin conectar grupos diferentes.

---

## 5. Construcción de variables

## 5.1. Similitud social entre dos nodos

Para cada par de nodos conectados \(i,j\), construir una medida de similitud a partir de sus atributos.

Opciones:

### Opción A: coincidencia simple

\[
S_{ij}
=
\frac{1}{K}
\sum_{k=1}^{K}
\mathbf{1}(x_{ik}=x_{jk})
\]

donde \(K\) es el número de dimensiones sociales comparables.

### Opción B: similitud de Jaccard

Si los atributos son vectores binarios:

\[
J_{ij}
=
\frac{|A_i\cap A_j|}
{|A_i\cup A_j|}
\]

Esta opción puede ser más adecuada para los archivos `.feat`.

### Recomendación

Usar Jaccard para atributos binarios y coincidencia categórica cuando pueda reconstruirse la categoría original.

---

## 5.2. Similitud social del vecindario de un nodo

Para cada nodo \(i\):

\[
\overline{S}_i
=
\frac{1}{k_i}
\sum_{j\in N(i)}
S_{ij}
\]

donde:

- \(N(i)\): conjunto de vecinos.
- \(k_i\): grado del nodo.

Interpretación: similitud promedio entre el nodo y sus contactos.

---

## 5.3. Diversidad social del vecindario

Se pueden construir varias medidas.

### Entropía

Para un atributo categórico:

\[
D_i
=
-\sum_{g=1}^{G} p_{ig}\log(p_{ig})
\]

donde \(p_{ig}\) es la proporción de vecinos de \(i\) pertenecientes al grupo \(g\).

Se puede normalizar:

\[
D_i^{norm}
=
\frac{-\sum_g p_{ig}\log(p_{ig})}
{\log(G)}
\]

### Diversidad basada en similitud

\[
D_i = 1-\overline{S}_i
\]

Esta será útil cuando los atributos no permitan reconstruir grupos categóricos de manera limpia.

### Número de círculos alcanzados

Si se usan los archivos `.circles`:

\[
C_i
=
\text{número de círculos distintos conectados por } i
\]

---

## 5.4. Cohesión local

### Clustering coefficient

\[
C_i
=
\frac{2T_i}{k_i(k_i-1)}
\]

donde \(T_i\) es el número de triángulos que contienen al nodo \(i\).

### Densidad del ego-network

Para el subgrafo formado por los vecinos de \(i\):

\[
Density_i
=
\frac{2m_i}
{k_i(k_i-1)}
\]

### Redundancia

Puede aproximarse con:

- Número medio de vecinos comunes.
- Ego-network density.
- Burt's constraint, si se implementa.

---

## 5.5. Intermediación

### Betweenness centrality

\[
BC_i
=
\sum_{s\neq i\neq t}
\frac{\sigma_{st}(i)}
{\sigma_{st}}
\]

Interpretación: proporción de caminos geodésicos que pasan por el nodo.

### Participation coefficient

Después de detectar comunidades:

\[
P_i
=
1-
\sum_{c=1}^{M}
\left(
\frac{k_{ic}}{k_i}
\right)^2
\]

donde \(k_{ic}\) es el número de conexiones del nodo \(i\) con la comunidad \(c\).

- \(P_i\approx 0\): conexiones concentradas dentro de una sola comunidad.
- \(P_i\) alto: conexiones distribuidas entre varias comunidades.

### Posibles medidas adicionales

- Bridging coefficient.
- Número de comunidades conectadas.
- Burt's effective size.
- Burt's constraint.
- Articulation points.

---

## 6. Metodología propuesta

## Paso 1. Cargar y validar los datos

- Leer archivos de nodos, aristas, atributos y círculos.
- Confirmar que los identificadores sean consistentes.
- Revisar duplicados y self-loops.
- Identificar valores faltantes.
- Verificar si los atributos tienen significado comparable entre ego-networks.

## Paso 2. Construir las redes

Para cada ego-network:

1. Cargar las aristas.
2. Añadir el ego central cuando corresponda.
3. Mantener la red no dirigida.
4. Seleccionar la componente conexa principal si existen nodos aislados o componentes pequeñas.
5. Guardar estadísticas básicas.

## Paso 3. Describir la estructura

Calcular:

- Número de nodos.
- Número de aristas.
- Densidad.
- Grado medio.
- Clustering global.
- Número de componentes.
- Tamaño de la componente principal.
- Distribución del grado.

Esto sirve como contexto, no como respuesta principal.

## Paso 4. Detectar comunidades

Aplicar un algoritmo consistente en todas las redes:

- Louvain, si está disponible.
- Greedy modularity, como alternativa en NetworkX.
- Spectral clustering, si el curso exige específicamente este método.

Guardar:

- Número de comunidades.
- Tamaño de cada comunidad.
- Modularidad.
- Comunidad asignada a cada nodo.

## Paso 5. Construir medidas sociales

Para cada nodo:

- Similitud promedio con sus vecinos.
- Diversidad del vecindario.
- Número de círculos o categorías alcanzadas.
- Porcentaje de vecinos socialmente similares.

## Paso 6. Construir medidas estructurales

Para cada nodo:

- Degree centrality.
- Clustering local.
- Ego-network density.
- Betweenness centrality.
- Participation coefficient.
- Número de comunidades conectadas.
- Effective size o constraint, si resulta viable.

## Paso 7. Evaluar las hipótesis

### Relación entre similitud y cohesión

Analizar:

\[
Clustering_i
=
\alpha
+
\beta_1 Similarity_i
+
\beta_2 \log(Degree_i)
+
\varepsilon_i
\]

Hipótesis:

\[
\beta_1>0
\]

También puede usarse correlación de Spearman.

### Relación entre diversidad e intermediación

Analizar:

\[
Betweenness_i
=
\alpha
+
\gamma_1 Diversity_i
+
\gamma_2 \log(Degree_i)
+
\varepsilon_i
\]

Hipótesis:

\[
\gamma_1>0
\]

Para reducir la fuerte asimetría de betweenness:

\[
Y_i=\log(1+Betweenness_i)
\]

### Participation coefficient

\[
Participation_i
=
\alpha
+
\delta_1 Diversity_i
+
\delta_2 \log(Degree_i)
+
\varepsilon_i
\]

Hipótesis:

\[
\delta_1>0
\]

### Importancia del control por grado

El grado debe incluirse porque:

- Los nodos con más conexiones tienen mecánicamente más posibilidades de conectar comunidades.
- El clustering suele disminuir con el grado.
- Betweenness y degree pueden estar fuertemente correlacionados.

---

## 7. Pruebas estadísticas y modelos nulos

## 7.1. Correlaciones

Usar preferiblemente Spearman:

- Similitud vs clustering.
- Diversidad vs betweenness.
- Diversidad vs participation coefficient.
- Degree vs betweenness.

## 7.2. Regresiones

Estimaciones simples con errores robustos.

Posibles especificaciones:

\[
Y_i
=
\alpha
+
\beta X_i
+
\gamma \log(1+k_i)
+
\mu_e
+
\varepsilon_i
\]

donde \(\mu_e\) representa efectos fijos por ego-network cuando se agrupen todas las redes.

## 7.3. Permutation test

Reasignar aleatoriamente los atributos entre nodos, manteniendo fija la estructura de la red.

Para cada permutación:

1. Mezclar atributos.
2. Recalcular similitud o diversidad.
3. Reestimar la relación con clustering o intermediación.
4. Comparar el estadístico observado con la distribución nula.

Esto permite evaluar si la asociación social observada excede lo que surgiría por azar dada la estructura de la red.

Número sugerido:

- 500 permutaciones como mínimo.
- 1.000 o más si el costo computacional lo permite.

## 7.4. Robustez

- Repetir análisis excluyendo nodos de grado 1.
- Repetir usando la componente conexa principal.
- Comparar resultados por ego-network.
- Usar más de una medida de diversidad.
- Usar betweenness aproximada si el cálculo exacto es costoso.

---

## 8. Figuras principales

## Figura 1. Esquema conceptual

Dos ejemplos visuales:

- Nodo con vecinos similares y alto clustering.
- Nodo con vecinos diversos y alta intermediación.

## Figura 2. Similitud social y clustering

Scatterplot o binscatter:

- Eje X: similitud social promedio.
- Eje Y: clustering local.
- Tamaño o transparencia: grado.

## Figura 3. Diversidad social y betweenness

- Eje X: diversidad del vecindario.
- Eje Y: \(\log(1+\text{betweenness})\).
- Control visual por grado.

## Figura 4. Diversidad y participation coefficient

- Eje X: diversidad social.
- Eje Y: participation coefficient.

## Figura 5. Ejemplos de nodos

Mostrar dos ego-networks:

1. Un nodo con alta cohesión y baja diversidad.
2. Un nodo con alta diversidad y alta intermediación.

Colorear por comunidad o círculo social.

## Figura 6. Distribución nula

Histograma de coeficientes o correlaciones obtenidos mediante permutaciones, con una línea vertical para el valor observado.

---

## 9. Tablas

## Tabla 1. Estadísticas descriptivas de las redes

Columnas sugeridas:

- Ego-network.
- Nodos.
- Aristas.
- Densidad.
- Grado medio.
- Clustering medio.
- Número de comunidades.
- Modularidad.

## Tabla 2. Correlaciones principales

- Similitud y clustering.
- Diversidad y betweenness.
- Diversidad y participation coefficient.
- Degree y betweenness.

## Tabla 3. Regresiones

Modelos:

1. Clustering sobre similitud.
2. Clustering sobre similitud y grado.
3. Betweenness sobre diversidad.
4. Betweenness sobre diversidad y grado.
5. Participation coefficient sobre diversidad y grado.

## Tabla 4. Permutation tests

- Estadístico observado.
- Media de la distribución nula.
- Percentil.
- p-value empírico.

---

## 10. Interpretación esperada

Un resultado consistente con las hipótesis mostraría que:

- Los nodos socialmente similares a sus vecinos pertenecen a entornos más triangulados y redundantes.
- Los nodos con contactos diversos atraviesan más fronteras comunitarias.
- Los usuarios populares no son necesariamente quienes más conectan comunidades.
- La cohesión y la intermediación representan formas diferentes de capital social.

No obstante, el proyecto no debe asumir estas conclusiones. Los datos pueden mostrar:

- Ausencia de relación.
- Relaciones heterogéneas entre ego-networks.
- Un papel dominante del grado.
- Mayor cohesión entre contactos diversos.
- Atributos poco informativos o demasiado incompletos.

---

## 11. Limitaciones

1. Los atributos están anonimizados.
2. No es posible identificar directamente ideologías, religiones o instituciones concretas.
3. La red corresponde a una muestra de ego-networks y no a todo Facebook.
4. Los vínculos representan amistad declarada, no intensidad de la relación.
5. La información es transversal y no permite establecer causalidad.
6. La similitud observada puede reflejar homofilia o contextos compartidos.
7. Los ego-networks pueden tener mecanismos de muestreo distintos.
8. La betweenness puede ser sensible al tamaño de la red.
9. Los círculos sociales pueden solaparse.
10. Las codificaciones de atributos deben validarse antes de combinar redes.

Conclusión permitida:

> Existe una asociación estructural entre similitud social y cohesión, o entre diversidad e intermediación.

Conclusión no permitida:

> La similitud social causa cohesión o la diversidad causa intermediación.

---

## 12. Criterio de éxito del proyecto

El proyecto será exitoso si logra responder de manera convincente:

1. Si la similitud social está asociada con cohesión local.
2. Si la diversidad social está asociada con intermediación.
3. Si estas relaciones se mantienen después de controlar por grado.
4. Si los patrones observados son mayores que los esperados bajo una asignación aleatoria de atributos.
5. Si los resultados son consistentes o heterogéneos entre ego-networks.

La hipótesis no necesita confirmarse para que el proyecto sea válido.

---

## 13. Estructura del informe final

### 1. Introduction

- Motivación.
- Pregunta de investigación.
- Conceptos de bonding y bridging social capital.
- Hipótesis.

### 2. Data

- Fuente.
- Construcción de la red.
- Atributos.
- Selección de muestra.
- Limitaciones.

### 3. Methodology

- Similitud.
- Diversidad.
- Cohesión.
- Intermediación.
- Comunidades.
- Regresiones.
- Permutation tests.

### 4. Results

- Descriptivas.
- Figuras.
- Correlaciones.
- Regresiones.
- Pruebas de permutación.
- Ejemplos de nodos.

### 5. Discussion

- Interpretación sociológica.
- Diferencia entre popularidad e intermediación.
- Resultados inesperados.
- Heterogeneidad entre redes.
- Limitaciones.

### 6. Conclusion

Respuesta breve y directa a la pregunta de investigación.

---

## 14. Instrucciones para el agente de programación

El agente debe trabajar por etapas y no asumir que los atributos son directamente comparables.

### Entregables de código

1. Script de inspección de archivos.
2. Funciones de carga para `.edges`, `.feat`, `.egofeat`, `.featnames` y `.circles`.
3. Tabla de calidad y cobertura de atributos.
4. Construcción de grafos por ego-network.
5. Cálculo de estadísticas descriptivas.
6. Detección de comunidades.
7. Construcción de similitud y diversidad.
8. Cálculo de clustering, betweenness y participation coefficient.
9. Base analítica a nivel nodo.
10. Correlaciones y regresiones.
11. Permutation tests.
12. Figuras reproducibles.
13. Tablas exportables a CSV y LaTeX.
14. Archivo final de resultados y log de decisiones.

### Reglas

- No combinar ego-networks hasta validar codificaciones.
- No eliminar nodos o atributos sin documentarlo.
- Mantener seeds fijas.
- Guardar resultados intermedios.
- Separar funciones de procesamiento, análisis y visualización.
- Evitar recalcular betweenness si ya fue almacenada.
- Usar nombres de variables claros.
- Crear una tabla de metadatos por ego-network.
- Registrar cualquier aproximación computacional.
- No interpretar causalmente las asociaciones.

---

## 15. Decisiones pendientes

Antes de implementar el análisis definitivo, resolver:

- [ ] ¿Se trabajará con todas las ego-networks o una selección?
- [ ] ¿Los atributos son comparables entre ego-networks?
- [ ] ¿Qué categorías sociales tienen suficiente cobertura?
- [ ] ¿La diversidad se medirá con entropía, Jaccard o ambas?
- [ ] ¿Se utilizarán círculos declarados, comunidades detectadas o ambos?
- [ ] ¿Se calculará betweenness exacta o aproximada?
- [ ] ¿Se incluirá Burt's constraint?
- [ ] ¿Se usarán regresiones agrupadas con efectos fijos por ego-network?
- [ ] ¿Cuántas permutaciones son computacionalmente viables?
- [ ] ¿Qué algoritmo de comunidades coincide mejor con lo enseñado en el curso?

---

## 16. Versión breve de la estrategia

1. Construir las ego-networks.
2. Recuperar atributos sociales.
3. Medir similitud y diversidad de cada vecindario.
4. Medir cohesión mediante clustering.
5. Detectar comunidades.
6. Medir intermediación mediante betweenness y participation coefficient.
7. Controlar por grado.
8. Comparar con permutaciones aleatorias.
9. Mostrar ejemplos visuales.
10. Interpretar los resultados desde bonding y bridging social capital.
