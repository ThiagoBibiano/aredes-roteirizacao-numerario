from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from roteirizacao.domain.optimization import InstanciaRoteirizacaoBase


class SolverAdapter(ABC):
    @abstractmethod
    def build_payload(self, instancia: InstanciaRoteirizacaoBase) -> Any:
        """Traduz a instancia solver-agnostic para um payload do solver."""

    @abstractmethod
    def build_model(self, instancia: InstanciaRoteirizacaoBase) -> Any:
        """Instancia o objeto nativo do solver, quando disponivel."""
