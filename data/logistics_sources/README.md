# Fontes de snapshots logisticos

Este diretorio representa a fonte operacional bruta consumida pelo materializador da Etapa 8.

## Convencao de arquivos

- Nome do arquivo: `YYYY-MM-DD.json`
- Um arquivo por `data_operacao`
- Conteudo em JSON UTF-8

## Campos esperados

```json
{
  "snapshot_id": "snap-source-2026-03-21",
  "generated_at": "2026-03-20T17:00:00+00:00",
  "strategy_name": "real_snapshot_v1",
  "source_name": "arquivo_operacional",
  "arcs": [
    {
      "id_origem": "dep-BASE-01",
      "id_destino": "no-ORD-01",
      "distancia_metros": 2400,
      "tempo_segundos": 420,
      "custo": "8.40",
      "disponivel": true,
      "restricao": null
    }
  ]
}
```

## Responsabilidade da Etapa 8

- Ler o snapshot bruto desta pasta.
- Canonicalizar e versionar o conteudo em `data/logistics_snapshots/`.
- Atualizar o snapshot corrente do dia.
- Registrar historico por `snapshot_id` em `versions/YYYY-MM-DD/manifest.json`.

O provider persistido continua lendo apenas `data/logistics_snapshots/`.
