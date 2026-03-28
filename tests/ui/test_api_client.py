from __future__ import annotations

import unittest

import httpx

from apps.ui_streamlit.client.api_client import PlanningApiClient, UiApiError


class ApiClientTest(unittest.TestCase):
    def make_client(self, handler) -> PlanningApiClient:
        return PlanningApiClient("http://testserver", transport=httpx.MockTransport(handler))

    def test_health_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok", "application": "api"}, request=request)

        with self.make_client(handler) as client:
            response = client.health()

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["application"], "api")

    def test_run_inline_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/v1/planning/run")
            return httpx.Response(200, json={"id_execucao": "exec-1", "result": {}}, request=request)

        with self.make_client(handler) as client:
            response = client.run_inline({"contexto": {"id_execucao": "exec-1"}})

        self.assertEqual(response["id_execucao"], "exec-1")

    def test_run_dataset_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/api/v1/planning/run-dataset")
            return httpx.Response(200, json={"id_execucao": "exec-dataset", "result": {}}, request=request)

        with self.make_client(handler) as client:
            response = client.run_dataset({"dataset_dir": "data/fake_smoke"})

        self.assertEqual(response["id_execucao"], "exec-dataset")

    def test_run_inline_422_is_mapped(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                422,
                json={"detail": "campo 'contexto.id_execucao' e obrigatorio", "error_type": "validation_error"},
                request=request,
            )

        with self.make_client(handler) as client:
            with self.assertRaises(UiApiError) as raised:
                client.run_inline({})

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.error_type, "validation_error")
        self.assertIn("contexto.id_execucao", raised.exception.detail)

    def test_run_dataset_404_is_mapped(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                404,
                json={"detail": "arquivo nao encontrado: data/fake_smoke/contexto.json", "error_type": "file_not_found"},
                request=request,
            )

        with self.make_client(handler) as client:
            with self.assertRaises(UiApiError) as raised:
                client.run_dataset({"dataset_dir": "data/fake_smoke"})

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.error_type, "file_not_found")
        self.assertIn("arquivo nao encontrado", raised.exception.detail)

    def test_http_error_without_expected_payload_is_mapped_to_generic_ui_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom", request=request)

        with self.make_client(handler) as client:
            with self.assertRaises(UiApiError) as raised:
                client.health()

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.error_type, "http_error")
        self.assertEqual(raised.exception.detail, "Erro HTTP 500 ao chamar a API.")

    def test_fastapi_422_list_is_mapped(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                422,
                json={
                    "detail": [
                        {"loc": ["body", "contexto"], "msg": "Field required"},
                    ]
                },
                request=request,
            )

        with self.make_client(handler) as client:
            with self.assertRaises(UiApiError) as raised:
                client.run_inline({})

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(raised.exception.error_type, "request_validation_error")
        self.assertIn("body.contexto", raised.exception.detail)
