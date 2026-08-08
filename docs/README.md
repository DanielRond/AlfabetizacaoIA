# Documentação do Curumim Marajoara

Índice da documentação do projeto. Leia [`../AGENTS.md`](../AGENTS.md) para o
resumo executivo (visão geral, comandos e convenções) e use os documentos abaixo
para aprofundamento.

## Mapa dos documentos

| Documento | O que cobre |
|---|---|
| [`01-visao-geral.md`](01-visao-geral.md) | Propósito, funcionalidades, stack e estrutura do repositório |
| [`02-arquitetura.md`](02-arquitetura.md) | Os dois serviços, fronteiras de responsabilidade e diagrama ponta a ponta |
| [`03-fluxos.md`](03-fluxos.md) | Fluxos detalhados: onboarding, texto, áudio, imagem, fallback, ack de entrega e ciclo de vida da sessão |
| [`04-contrato-api.md`](04-contrato-api.md) | Contrato HTTP Node → Python: endpoints, envelopes, `action`s, `error_code`s e fixtures |
| [`05-banco-de-dados.md`](05-banco-de-dados.md) | Modelo de dados SQLite: tabelas, colunas, estados e migração |
| [`06-modulos-node.md`](06-modulos-node.md) | Walkthrough de cada módulo do conector Node (`apps/whatsapp-connector/src/`) |
| [`07-modulos-python.md`](07-modulos-python.md) | Walkthrough do backend Python (`src/curumim/`) |
| [`08-decisoes.md`](08-decisoes.md) | Decisões arquiteturais (ADRs) e rationale por trás das escolhas |
| [`09-operacao.md`](09-operacao.md) | Variáveis de ambiente, setup, execução, deploy e testes |

## Como usar

- **Quero saber o que o projeto faz** → [01-visao-geral.md](01-visao-geral.md)
- **Quero entender como os serviços se conectam** → [02-arquitetura.md](02-arquitetura.md) e [04-contrato-api.md](04-contrato-api.md)
- **Quero acompanhar o caminho de uma mensagem** → [03-fluxos.md](03-fluxos.md)
- **Quero ler o código por módulo** → [06-modulos-node.md](06-modulos-node.md) e [07-modulos-python.md](07-modulos-python.md)
- **Quero rodar ou dar deploy** → [09-operacao.md](09-operacao.md)

## Fontes primárias

- Contrato oficial: [`specs/002-whatsappjs-python-split/contracts/node-python-api.md`](../specs/002-whatsappjs-python-split/contracts/node-python-api.md)
- Spec da arquitetura: [`specs/002-whatsappjs-python-split/spec.md`](../specs/002-whatsappjs-python-split/spec.md)
- Modelo de dados: [`specs/002-whatsappjs-python-split/data-model.md`](../specs/002-whatsappjs-python-split/data-model.md)
- Research/decisões: [`specs/002-whatsappjs-python-split/research.md`](../specs/002-whatsappjs-python-split/research.md)
- Fixtures do contrato: [`specs/002-whatsappjs-python-split/contracts/fixtures/`](../specs/002-whatsappjs-python-split/contracts/fixtures/)

> Estes documentos são um mapa do código atual. Se o código e a documentação
> divergirem, o código é a fonte da verdade — atualize os documentos.
