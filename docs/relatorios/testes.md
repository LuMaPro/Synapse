# Testes de Software

> Enunciado, seção 2.5.3: descrever a estratégia de testes adotada, as ferramentas utilizadas, o que foi coberto e o que ficou fora do escopo, e apresentar evidências de execução.

Cada PR que adicionar testes registra aqui o que foi testado e em qual nível. A versão final é consolidada na issue #47, com as evidências da #43 em `evidencias/`.

## Estratégia

### Testes unitários

- **Domínio** (`backend/tests/unit/domain/`, issue #9): um arquivo por classe (`Usuario`, `SessaoFoco`, `Neuronio`, `Duracao` e as exceções). Cobrem valores válidos e inválidos (com `pytest.mark.parametrize`), atributos somente leitura e igualdade por identidade. Não usam banco nem Django.
- **Arquitetura** (`backend/tests/unit/domain/test_dominio_puro.py`, issue #9): lê os imports de cada arquivo de `app/domain/` com o módulo `ast` e falha se algum importar `django` ou `rest_framework`.
- **Timer da sessão de foco** (`frontend/src/hooks/useSessaoFoco.test.ts`, issue #17): testa o hook isolado com `renderHook` e o relógio falso do Vitest (`vi.useFakeTimers`). Inclui o critério de aceite da issue: o relógio avança sem o intervalo disparar, como numa aba em segundo plano, e o tempo restante continua certo ao voltar para a aba. Também cobre a regra do modo tolerante: saldo de 10% da sessão para ficar fora da tela, descontado a cada saída sem voltar ao valor inicial, e poda quando a saída passa do saldo.
- **Neurônio animado** (`frontend/src/utils/geometriaNeuronio.test.ts` e `frontend/src/components/NeuronioAnimado.test.tsx`, issue #19): a geometria é testada como função pura (o desenho é sempre o mesmo para o mesmo tipo; o corpo celular cresce primeiro, os dendritos nível a nível e o axônio só depois de 80%; podado, recolhe até 42%, sem axônio nem pontas). No componente, verifica que a poda e o brilho forte só entram depois do primeiro quadro, para a transição acontecer na tela.
- **Detecção de saída da tela** (`frontend/src/hooks/useDeteccaoSaida.test.ts`, issue #18): como o jsdom não troca de aba nem entra em tela cheia, os testes simulam o que o navegador informa (`visibilityState`, `fullscreenElement`, `hasFocus`) e disparam os eventos. Cobrem cada sinal, a junção de sinais simultâneos numa saída só (trocar de aba dispara `blur` e `visibilitychange`), o caso do iPhone sem tela cheia e o aviso nativo ao fechar a página.
- **Tela de foco** (`frontend/src/pages/Foco.test.tsx`, issues #17 e #18): usa a Testing Library para clicar como o estudante faria (escolher duração e modo, começar, desistir com confirmação, ver as telas de sucesso e de poda), buscando os elementos pelo papel acessível (`getByRole`). O bloco "saída da tela" verifica os critérios de aceite da #18: trocar de aba no modo estrito poda a sessão; no modo tolerante, saídas somando até 10% da sessão mantêm a sessão viva, com o saldo restante na tela, e passar disso poda.
- **Integração da tela de foco com a API** (`frontend/src/hooks/useSessaoFoco.test.ts`, `frontend/src/services/sessoes.test.ts` e `frontend/src/pages/Foco.test.tsx`, issue #20): o `fetch` é trocado por um servidor falso (`frontend/src/test/servidorFalso.ts`) com as mesmas regras da API (uma sessão ativa por vez, poda no estrito, saldo de 10% no tolerante, conclusão só no fim previsto), que guarda as chamadas recebidas. Cobre os critérios de aceite da issue (iniciar → concluir cria o neurônio no servidor; a poda funciona nos dois modos) e os casos de falha: sem rede, o aviso de saída fica guardado e é entregue antes da próxima sessão ou ao reabrir a tela, e a conclusão é tentada de novo; se o servidor podar, a tela mostra a poda; o relógio do navegador atrasado não atrapalha. Para conferir que os testes pegam erros, cada regra foi quebrada de propósito no hook e o teste correspondente falhou.
- **Serviço de sessões** (`backend/tests/unit/application/test_sessoes.py`, issue #16): o `SessaoService` é testado com repositórios em memória e um relógio controlado pelo teste, sem banco. Cobre uma sessão ativa por usuário, conclusão antes da hora (recusada) e dentro da tolerância de 2 s, criação do neurônio, poda por saída nos dois modos, saídas no futuro ou antes do início (recusadas), sessão de outro usuário e a expiração de sessões abandonadas.

### Testes de integração

- **API de sessões** (`backend/tests/integration/test_api_sessoes.py`, issue #16): os endpoints com o `APIClient` do DRF e o banco de teste, trocando o relógio do servidor (`monkeypatch` em `app.api.sessoes.agora`). Inclui os critérios de aceite da issue (concluir antes da hora retorna 409; sessão de outro usuário retorna 404) e confere que o histórico de interrupções do modo tolerante sobrevive entre requisições. Na issue #20, também que reenviar a mesma interrupção (o app tenta de novo quando a rede falha) não desconta o saldo duas vezes.

### Testes de aceitação (E2E)

## Ferramentas

## O que foi coberto

## O que ficou fora do escopo

- **Aparência e fluidez das animações** (issue #19): o jsdom não desenha nem roda transições CSS, então os testes automatizados conferem os valores (quanto de cada traço está desenhado, classes de poda e de brilho), não o resultado visual. A comparação com o protótipo e a fluidez num celular real são verificadas manualmente.
- **Comportamento de cada navegador ao sair da tela** (issue #18): os eventos são simulados nos testes, então as diferenças reais entre Chrome, Firefox, Android e iPhone (por exemplo, o iPhone não tem tela cheia para páginas, e celulares costumam ignorar o aviso de `beforeunload`) são verificadas manualmente e registradas na issue.

## Evidências de execução
