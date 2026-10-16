"""Exceções de regra de negócio. A camada api/ as traduz para HTTP (issue #12)."""


class ErroDominio(Exception):
    """Base de todas as exceções do domínio."""


class DuracaoInvalida(ErroDominio):
    """Duração de sessão fora das regras (10 a 120 minutos, de 5 em 5)."""


class NomeInvalido(ErroDominio):
    """Nome de usuário vazio ou longo demais."""


class EmailInvalido(ErroDominio):
    """E-mail vazio, mal formado ou longo demais."""


class HorarioInvalido(ErroDominio):
    """Horário sem fuso horário ou fora de ordem (ex.: fim antes do início)."""


class TransicaoInvalida(ErroDominio):
    """Tentativa de mudar o estado da sessão de forma não permitida."""


class EmailJaCadastrado(ErroDominio):
    """Cadastro com um e-mail que já pertence a outro usuário."""


class SenhaInvalida(ErroDominio):
    """Senha que não atende às regras de segurança (curta, comum, só números...)."""
