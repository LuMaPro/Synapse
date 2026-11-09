"""Confere o diagrama de classes (docs/uml/classes.puml) contra o código (issue #40).

Lê as classes do código pela árvore sintática (sem importar nada) e as do diagrama
pelo texto do PlantUML. Se alguém criar, renomear ou apagar uma classe, um método ou
um atributo sem atualizar o diagrama, um destes testes falha.

O contêiner do backend só monta a pasta backend/; lá o diagrama não existe e os testes
são pulados. No CI e na máquina de quem desenvolve, rodam.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
DIAGRAMA = BACKEND.parent / "docs" / "uml" / "classes.puml"

pytestmark = pytest.mark.skipif(
    not DIAGRAMA.exists(), reason="docs/uml/classes.puml fora do contêiner"
)

# Onde estão as classes que o diagrama deve mostrar.
CAMADAS = [BACKEND / "app" / "domain", BACKEND / "app" / "application"]
IMPLEMENTACOES = [*sorted((BACKEND / "app" / "infra" / "repositorios").glob("*.py"))]
IMPLEMENTACOES.append(BACKEND / "app" / "infra" / "senhas.py")

# Nomes do diagrama que não são classes do projeto.
EXTERNAS = {"Exception", "InfraRepositorios"}
# Toda entidade guarda o id do dono; o diagrama não desenha essa ligação.
NAO_DESENHADOS = {"usuario_id"}

PADROES = {
    "EstadoSessao": "State",
    "PoliticaInterrupcao": "Strategy",
    "RegraFormacaoSinapses": "Strategy",
    "FabricaNeuronio": "Factory Method",
    "TipoNeuronio": "Factory Method",
    "PublicadorEventos": "Observer",
    "ObservadorSessao": "Observer",
    "RepositorioSessao": "Repository",
    "RegraConquista": "Template Method",
}


# --- Código ------------------------------------------------------------------------


@dataclass
class ClasseCodigo:
    nome: str
    bases: list[str]
    metodos: dict[str, set[str]] = field(default_factory=dict)
    atributos_classe: set[str] = field(default_factory=set)
    atributos_instancia: set[str] = field(default_factory=set)

    @property
    def abstrata(self) -> bool:
        return any("abstractmethod" in d for d in self.metodos.values())

    @property
    def enum(self) -> bool:
        return any(b.endswith("Enum") for b in self.bases)


def _nome(no: ast.expr) -> str:
    if isinstance(no, ast.Call):
        no = no.func
    if isinstance(no, ast.Subscript):
        no = no.value
    if isinstance(no, ast.Attribute):
        return no.attr
    return no.id if isinstance(no, ast.Name) else ""


def _ler_classe(no: ast.ClassDef) -> ClasseCodigo:
    classe = ClasseCodigo(no.name, [_nome(b) for b in no.bases])
    for item in no.body:
        if isinstance(item, ast.FunctionDef):
            decoradores = {_nome(d) for d in item.decorator_list}
            if "setter" not in decoradores:
                classe.metodos[item.name] = decoradores
            for sub in ast.walk(item):
                alvos = []
                if isinstance(sub, ast.Assign):
                    alvos = sub.targets
                elif isinstance(sub, ast.AnnAssign | ast.AugAssign):
                    alvos = [sub.target]
                for alvo in alvos:
                    if (
                        isinstance(alvo, ast.Attribute)
                        and isinstance(alvo.value, ast.Name)
                        and alvo.value.id == "self"
                    ):
                        classe.atributos_instancia.add(alvo.attr)
        elif isinstance(item, ast.Assign):
            for alvo in item.targets:
                if isinstance(alvo, ast.Name):
                    classe.atributos_classe.add(alvo.id)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            classe.atributos_classe.add(item.target.id)
    return classe


def _classes_do_codigo() -> dict[str, ClasseCodigo]:
    arquivos = [a for pasta in CAMADAS for a in sorted(pasta.rglob("*.py"))]
    classes: dict[str, ClasseCodigo] = {}
    for arquivo in [*arquivos, *IMPLEMENTACOES]:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        for no in arvore.body:
            if isinstance(no, ast.ClassDef):
                assert no.name not in classes, f"classe repetida: {no.name}"
                classes[no.name] = _ler_classe(no)
    return classes


# --- Diagrama ----------------------------------------------------------------------

DECLARACAO = re.compile(
    r'^(abstract class|class|interface|enum)\s+(?:"[^"]*"\s+as\s+)?(\w+)(.*?)(\{)?$'
)
HERANCA = re.compile(r"^(\w+)\s+<\|(--|\.\.)\s+(\w+)$")
ASSOCIACAO = re.compile(
    r'^(\w+)\s+(?:"[^"]*"\s+)?(\*--|o--|-->)\s+(?:"[^"]*"\s+)?\w+\s*:\s*(\w+)'
)
MEMBRO = re.compile(r"^([+\-#~])\s*(/)?(\w+)(\()?")


@dataclass
class ClasseDiagrama:
    nome: str
    tipos: set[str] = field(default_factory=set)
    estereotipos: str = ""
    corpos: list[list[str]] = field(default_factory=list)

    @property
    def membros(self) -> list[str]:
        return [linha for corpo in self.corpos for linha in corpo]


@dataclass
class Diagrama:
    vistas: list[str]
    classes: dict[str, ClasseDiagrama]
    herancas: set[tuple[str, str, str]]
    rotulos: dict[str, set[str]]


def _ler_diagrama() -> Diagrama:
    vistas, herancas = [], set()
    classes: dict[str, ClasseDiagrama] = {}
    rotulos: dict[str, set[str]] = {}
    corpo: list[str] | None = None
    em_nota = False
    for bruta in DIAGRAMA.read_text(encoding="utf-8").splitlines():
        linha = bruta.strip()
        if not linha or linha.startswith("'"):
            continue
        if em_nota:
            em_nota = linha != "end note"
            continue
        if corpo is not None:
            if linha == "}":
                corpo = None
            else:
                corpo.append(linha)
            continue
        if linha.startswith("@startuml"):
            vistas.append(linha.split()[1])
        elif linha.startswith("note ") and ":" not in linha:
            em_nota = True
        elif m := DECLARACAO.match(linha):
            tipo, nome, resto, abre = m.groups()
            classe = classes.setdefault(nome, ClasseDiagrama(nome))
            classe.tipos.add(tipo)
            classe.estereotipos += resto
            if abre:
                corpo = []
                classe.corpos.append(corpo)
        elif m := HERANCA.match(linha):
            pai, linha_tipo, filho = m.groups()
            herancas.add((pai, linha_tipo, filho))
        elif m := ASSOCIACAO.match(linha):
            origem, _, rotulo = m.groups()
            rotulos.setdefault(origem, set()).add(rotulo)
    return Diagrama(vistas, classes, herancas, rotulos)


@dataclass
class Membro:
    visibilidade: str
    nome: str
    metodo: bool
    derivado: bool
    estatico: bool
    abstrato: bool


def _membros(classe: ClasseDiagrama) -> list[Membro]:
    membros = []
    for linha in classe.membros:
        if m := MEMBRO.match(linha):
            visibilidade, barra, nome, parentese = m.groups()
            membros.append(
                Membro(
                    visibilidade,
                    nome,
                    metodo=bool(parentese),
                    derivado=bool(barra),
                    estatico="{static}" in linha,
                    abstrato="{abstract}" in linha,
                )
            )
    return membros


# --- Fixtures ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def codigo() -> dict[str, ClasseCodigo]:
    return _classes_do_codigo()


@pytest.fixture(scope="module")
def diagrama() -> Diagrama:
    return _ler_diagrama()


def _ancestrais(nome: str, codigo: dict[str, ClasseCodigo]) -> list[str]:
    linha = [nome]
    for base in codigo[nome].bases:
        if base in codigo:
            linha += _ancestrais(base, codigo)
    return linha


# --- Testes ------------------------------------------------------------------------


def test_diagrama_tem_as_mesmas_classes_que_o_codigo(codigo, diagrama):
    no_diagrama = set(diagrama.classes) - EXTERNAS
    assert sorted(set(codigo) - no_diagrama) == [], "classes faltando no diagrama"
    assert sorted(no_diagrama - set(codigo)) == [], "classes que não existem mais"


def test_herancas_e_implementacoes_batem_com_o_codigo(codigo, diagrama):
    no_codigo = {
        (base, classe.nome)
        for classe in codigo.values()
        for base in classe.bases
        if base in codigo or base in EXTERNAS
    }
    no_diagrama = {
        (pai, filho)
        for pai, _, filho in diagrama.herancas
        if "InfraRepositorios" not in (pai, filho)
    }
    assert sorted(no_codigo - no_diagrama) == [], "heranças faltando no diagrama"
    assert sorted(no_diagrama - no_codigo) == [], "heranças que o código não tem"


def test_seta_tracejada_so_para_implementar_interface(diagrama):
    for pai, linha, filho in diagrama.herancas:
        interface = "interface" in diagrama.classes[pai].tipos
        assert (linha == "..") == interface, f"{pai} <|{linha} {filho}"


def test_abstratas_interfaces_e_enums_batem_com_o_codigo(codigo, diagrama):
    for nome, classe in codigo.items():
        tipos = diagrama.classes[nome].tipos
        assert len(tipos) == 1, f"{nome} declarada como {tipos}"
        tipo = next(iter(tipos))
        if classe.enum:
            assert tipo == "enum", nome
        elif not classe.abstrata:
            assert tipo == "class", f"{nome} não tem método abstrato"
        elif tipo == "interface":
            concretos = [
                m
                for m, decoradores in classe.metodos.items()
                if "abstractmethod" not in decoradores and m != "__init__"
            ]
            assert concretos == [], f"interface {nome} tem métodos concretos"
        else:
            assert tipo == "abstract class", f"{nome} tem método abstrato"


def test_cada_classe_e_detalhada_em_uma_vista_so(diagrama):
    repetidas = [c.nome for c in diagrama.classes.values() if len(c.corpos) > 1]
    assert repetidas == []


def test_membros_do_diagrama_existem_no_codigo(codigo, diagrama):
    erros = []
    for nome, classe_diagrama in diagrama.classes.items():
        if nome in EXTERNAS:
            continue
        classe = codigo[nome]
        if classe.enum:
            assert set(classe_diagrama.membros) <= classe.atributos_classe, nome
            continue
        for membro in _membros(classe_diagrama):
            local = f"{nome}.{membro.nome}"
            privado = membro.nome.startswith("_") and not membro.nome.endswith("__")
            if membro.metodo or membro.derivado:
                decoradores = classe.metodos.get(membro.nome)
                if decoradores is None:
                    erros.append(f"{local}: método não existe")
                    continue
                if membro.derivado != ("property" in decoradores):
                    erros.append(f"{local}: '/' é só para propriedade")
                if membro.abstrato != ("abstractmethod" in decoradores):
                    erros.append(f"{local}: {{abstract}} não bate com o código")
                estatico = decoradores & {"staticmethod", "classmethod"}
                if membro.estatico != bool(estatico):
                    erros.append(f"{local}: {{static}} não bate com o código")
                if privado != (membro.visibilidade in "-~"):
                    erros.append(f"{local}: visibilidade errada")
            else:
                no_codigo = (
                    f"_{membro.nome}" if membro.visibilidade == "-" else membro.nome
                )
                if membro.estatico:
                    existe = no_codigo in classe.atributos_classe
                else:
                    existe = no_codigo in (
                        classe.atributos_classe | classe.atributos_instancia
                    )
                if not existe:
                    erros.append(f"{local}: atributo {no_codigo} não existe")
    assert erros == []


def test_codigo_nao_tem_membro_fora_do_diagrama(codigo, diagrama):
    """Atributos e métodos de domínio e aplicação aparecem na classe ou num ancestral.

    Um atributo também conta se for o rótulo de uma associação que sai da classe
    (ex.: `SessaoFoco *-- EstadoSessao : estado`).
    """
    erros = []
    for nome, classe in codigo.items():
        if classe.enum or nome.endswith("Django"):
            continue
        mostrados = set(NAO_DESENHADOS)
        for ancestral in _ancestrais(nome, codigo):
            mostrados |= {m.nome for m in _membros(diagrama.classes[ancestral])}
            mostrados |= diagrama.rotulos.get(ancestral, set())
        for metodo in classe.metodos:
            dunder = metodo.startswith("__") and metodo.endswith("__")
            if not dunder and metodo not in mostrados:
                erros.append(f"{nome}.{metodo}()")
        for atributo in classe.atributos_classe | classe.atributos_instancia:
            if atributo.startswith("__"):
                continue
            if atributo.lstrip("_") not in mostrados and atributo not in mostrados:
                erros.append(f"{nome}.{atributo}")
    assert sorted(erros) == [], "membros do código que o diagrama não mostra"


def test_padroes_de_projeto_aparecem_como_estereotipo(diagrama):
    for nome, padrao in PADROES.items():
        assert f"<<{padrao}" in diagrama.classes[nome].estereotipos, nome


def test_cada_vista_foi_exportada_em_png_e_svg(diagrama):
    pasta = DIAGRAMA.parent
    faltando = [
        f"{vista}.{extensao}"
        for vista in diagrama.vistas
        for extensao in ("png", "svg")
        if not (pasta / f"{vista}.{extensao}").exists()
    ]
    assert faltando == []
