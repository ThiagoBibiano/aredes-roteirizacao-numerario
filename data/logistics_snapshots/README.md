# Snapshots de Matriz Logistica

Cada arquivo deve usar o nome `YYYY-MM-DD.json`, referente ao dia operacional.

Formato minimo:

```json
{
  "snapshot_id": "snap-2026-03-21",
  "generated_at": "2026-03-20T17:00:00+00:00",
  "strategy_name": "snapshot_json_v1",
  "arcs": [
    {
      "id_origem": "dep-BASE-01",
      "id_destino": "no-ORD-01",
      "distancia_metros": 4321,
      "tempo_segundos": 777,
      "custo": "12.34",
      "disponivel": true,
      "restricao": null
    }
  ]
}
```

O provider persistido filtra os arcos relevantes para a instancia do dia, mas exige cobertura completa para todos os pares ordenados entre depositos e nos solicitados.
