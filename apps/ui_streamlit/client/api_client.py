from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import httpx


DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0)


@dataclass(slots=True)
class UiApiError(RuntimeError):
    message: str
    status_code: int | None = None
    error_type: str = "api_error"
    detail: str | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.message)
        if self.detail is None:
            self.detail = self.message


class PlanningApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        if client is not None and transport is not None:
            raise ValueError("client e transport nao podem ser usados juntos")
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=timeout or DEFAULT_TIMEOUT,
            transport=transport,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "PlanningApiClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        payload = self._request("GET", "/health")
        if not isinstance(payload, dict):
            raise UiApiError("Resposta invalida recebida do endpoint /health.")
        return payload

    def run_inline(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/v1/planning/run", json=dict(payload))
        if not isinstance(response, dict):
            raise UiApiError("Resposta invalida recebida do endpoint de execucao inline.")
        return response

    def run_dataset(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/v1/planning/run-dataset", json=dict(payload))
        if not isinstance(response, dict):
            raise UiApiError("Resposta invalida recebida do endpoint de execucao por dataset.")
        return response

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc.response) from exc
        except httpx.HTTPError as exc:
            raise UiApiError(
                "Nao foi possivel conectar ao backend HTTP.",
                error_type="network_error",
                detail=str(exc),
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise UiApiError(
                f"A API retornou JSON invalido em {path}.",
                status_code=response.status_code,
                error_type="invalid_json",
            ) from exc

    def _map_http_error(self, response: httpx.Response) -> UiApiError:
        detail: str | None = None
        error_type = "http_error"
        context: dict[str, Any] = {"path": str(response.request.url), "status_code": response.status_code}
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            payload_detail = payload.get("detail")
            if isinstance(payload_detail, str):
                detail = payload_detail
            elif isinstance(payload_detail, list):
                detail = self._format_validation_details(payload_detail)
                error_type = "request_validation_error"
            if payload.get("error_type"):
                error_type = str(payload["error_type"])
            context["payload"] = payload
        elif isinstance(payload, list):
            detail = self._format_validation_details(payload)
            error_type = "request_validation_error"
            context["payload"] = payload

        if not detail:
            detail = f"Erro HTTP {response.status_code} ao chamar a API."

        return UiApiError(
            detail,
            status_code=response.status_code,
            error_type=error_type,
            detail=detail,
            context=context,
        )

    def _format_validation_details(self, details: list[Any]) -> str:
        messages: list[str] = []
        for item in details:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", ()))
                message = str(item.get("msg") or "valor invalido")
                if location:
                    messages.append(f"{location}: {message}")
                else:
                    messages.append(message)
            else:
                messages.append(str(item))
        rendered = "; ".join(message for message in messages if message)
        return f"Requisicao invalida: {rendered}" if rendered else "Requisicao invalida."
