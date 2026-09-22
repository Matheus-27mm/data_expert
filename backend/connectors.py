"""Provider-independent contracts. Vendor adapters must be registered explicitly."""
from dataclasses import dataclass
from typing import Iterable, Literal, Protocol

@dataclass(frozen=True)
class SourceEvent:
    external_id: str
    entity: Literal['products','sales','expenses']
    operation: Literal['create','update','cancel']
    values: dict
    revision: str

class Connector(Protocol):
    """Secrets are supplied server-side, never accepted from a browser endpoint.

    Adapters must define pagination, rate limits, a resumable cursor and explicit
    normalization of money/dates. Mutations and cancellations require business
    rules specific to the ERP; they must never be treated as another new sale.
    """
    def fetch(self, *, credentials: dict, cursor: str | None) -> tuple[Iterable[SourceEvent], str | None]: ...

CONNECTORS: dict[str, Connector] = {}

def connector_for(provider: str) -> Connector:
    if provider not in CONNECTORS:
        raise ValueError('Este ERP ainda não tem um conector implementado.')
    return CONNECTORS[provider]

def require_supported_event(event: SourceEvent):
    if event.operation != 'create':
        raise ValueError('Atualizações e cancelamentos exigem uma regra explícita do conector; nenhum registro foi alterado.')
    if not event.external_id or not event.revision:
        raise ValueError('Identificador e revisão da origem são obrigatórios.')
