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


class PoliticaInvalida(ErroDominio):
    """Modo de interrupção desconhecido (os válidos são estrito e tolerante)."""


class SessaoAtivaExistente(ErroDominio):
    """O estudante tentou iniciar uma sessão tendo outra em andamento."""


class SessaoNaoEncontrada(ErroDominio):
    """Sessão inexistente ou de outro estudante (as duas respostas são iguais)."""


class SinapseInvalida(ErroDominio):
    """Sinapse mal formada: liga um neurônio a ele mesmo, repete uma ligação, tem
    peso inválido ou envolve um neurônio podado ou fora da rede."""


class RedeNeuralInvalida(ErroDominio):
    """Neurônio que não pode entrar na rede (de outro estudante ou já presente)."""


class NomeMateriaInvalido(ErroDominio):
    """Nome de matéria vazio ou longo demais."""


class CorInvalida(ErroDominio):
    """Código hexadecimal de cor inválido (deve ser #RRGGBB)."""


class MateriaNaoEncontrada(ErroDominio):
    """Matéria inexistente ou de outro estudante."""


class MateriaJaExiste(ErroDominio):
    """O estudante já tem uma matéria cadastrada com este nome."""


class CorNaoEncontrada(ErroDominio):
    """Cor que não está à venda na loja (#34)."""


class SaldoInsuficiente(ErroDominio):
    """O estudante não tem ATP suficiente para comprar a cor."""


class CorJaDesbloqueada(ErroDominio):
    """Compra de uma cor que o estudante já tem."""


class CorBloqueada(ErroDominio):
    """Matéria com uma cor da loja que o estudante ainda não comprou."""


class PeriodoInvalido(ErroDominio):
    """Período de estatísticas desconhecido (os válidos são dia, semana e mes)."""
