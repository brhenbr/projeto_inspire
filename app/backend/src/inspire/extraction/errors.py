"""Erros da extração, separados por o que fazer a respeito."""


class PortalError(Exception):
    """Base de todos os erros ao falar com o portal."""


class PortalAuthError(PortalError):
    """Chave ausente, inválida ou sem permissão (401/403). Não adianta tentar de novo."""


class PortalRequestError(PortalError):
    """Pedido recusado de forma definitiva (outro 4xx). Não adianta tentar de novo.

    Acontece com itens específicos: alguns conjuntos aparecem na listagem mas o detalhe devolve 400.
    Quem coleta deve registrar o item como indisponível e seguir em frente.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PortalUnavailableError(PortalError):
    """O portal não respondeu de forma utilizável depois de todas as tentativas."""

    def __init__(self, message: str, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


class PersonalDataError(Exception):
    """Tentativa de gravar dados pessoais (ADR-0002, item 7)."""


class ActiveRunExistsError(Exception):
    """Já existe uma execução de extração ativa (ADR-0006)."""
