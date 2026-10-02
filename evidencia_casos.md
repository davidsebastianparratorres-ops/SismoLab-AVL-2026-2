# Evidencia de casos mínimos (sección 16)

Generado por `tests/generate_test_data.py`. Estado inicial común: zonas `[0,500]x[0,1000]` no poblada y `[500,1000]x[0,1000]` poblada, estación EST-01, reloj en 2026-09-07T12:00:00Z, W=48 h, R=40 km, L=3, T=72 h.

## Reporte tardío

| Verificación | Esperado | Obtenido | Resultado |
|---|---|---|---|
| Antes del reporte tardío: referencia del evento 2 | `1` | `1` | OK |
| Antes del reporte tardío: referencia del evento 1 | `None` | `None` | OK |
| Candidatos nuevos del evento 2 | `[1, 3]` | `[1, 3]` | OK |
| Candidatos nuevos del evento 1 | `[3]` | `[3]` | OK |
| Referencia elegida del evento 2 (mayor magnitud) | `3` | `3` | OK |
| Referencia elegida del evento 1 | `3` | `3` | OK |
| Referencia del evento 3 (el más antiguo) | `None` | `None` | OK |
| Nodos en el AVL (no se crea nodo duplicado) | `3` | `3` | OK |
| Tras deshacer: referencia del evento 2 vuelve a | `1` | `1` | OK |
| Tras deshacer: el evento 3 ya no está activo | `False` | `False` | OK |

## Persistencia

| Verificación | Esperado | Obtenido | Resultado |
|---|---|---|---|
| Topología normal: el archivo se acepta | `True` | `True` | OK |
| Topología normal: exportar lo cargado reproduce el mismo JSON | `True` | `True` | OK |
| Topología normal: métrica 'correcciones aceptadas' restaurada | `1` | `1` | OK |
| Topología normal: identificador 4 sigue retirado | `True` | `True` | OK |
| Topología en estrés (modo ESTRES): el archivo se acepta | `True` | `True` | OK |
| Topología en estrés: nodos desbalanceados señalados | `3` | `3` | OK |
| El mismo archivo declarado NORMAL se rechaza | `False` | `False` | OK |

## Consistencia

| Verificación | Esperado | Obtenido | Resultado |
|---|---|---|---|
| Archivo inconsistente (prioridad alterada): se rechaza | `False` | `False` | OK |
| Se informa el problema | `True` | `True` | OK |
| El escenario actual no cambió | `True` | `True` | OK |
| No se registró ninguna acción en el historial | `True` | `True` | OK |

**Total: 21 verificaciones, 0 fallas.**