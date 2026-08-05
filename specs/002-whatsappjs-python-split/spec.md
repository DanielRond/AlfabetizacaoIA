# Feature Specification: WhatsApp JS + Python Split

**Feature Branch**: `development`

**Status**: Draft

**Input**: Rework the current Alfabot Marajoara integration so that a Node service owns the WhatsApp connection through a session-based client (whatsapp.js / whatsapp-web.js style) and a Python backend owns message processing, AI, RAG, and media generation.

## User Stories and Testing

### User Story 1 - WhatsApp session and inbound relay

Como operador do sistema, quero manter a sessao do WhatsApp no Node para receber mensagens e repassar os eventos ao backend Python sem depender da Cloud API da Meta.

**Independent Test**: Iniciar o cliente Node, autenticar via QR, enviar uma mensagem de teste e confirmar que o evento chega ao backend Python com o numero, tipo da mensagem e payload normalizado.

### User Story 2 - Resposta pedagogica pelo backend Python

Como aluno, quero enviar texto ou audio e receber uma resposta adaptada ao meu nivel pedagogico, com contexto marajoara, gerada pelo backend Python.

**Independent Test**: Enviar texto e audio para um aluno cadastrado e verificar que o backend retorna uma resposta estruturada com texto final e metadados de envio.

### User Story 3 - Midia de resposta pelo Node

Como aluno, quero que o sistema consiga responder com audio ou video quando a IA produzir esse tipo de saida, usando o Node para publicar a midia no WhatsApp.

**Independent Test**: Receber uma resposta do backend que solicite envio de audio ou video e confirmar que o Node faz o envio na conta ativa do WhatsApp.

### User Story 4 - Resiliencia e fallback

Como operador, quero que falhas de rede, audio corrompido e erros de integracao sejam tratados sem derrubar nenhum dos servicos.

**Independent Test**: Simular falha no backend, falha no envio do Node e arquivo de audio incompreensivel, confirmando respostas de fallback e logs rastreaveis.

## Requirements

### Functional Requirements

- **FR-001**: O sistema MUST separar a conexao WhatsApp do processamento de IA em dois servicos independentes.
- **FR-002**: O Node MUST manter a sessao WhatsApp, receber mensagens e enviar respostas finais para o usuario.
- **FR-003**: O backend Python MUST expor uma API interna para receber mensagens normalizadas e devolver a acao de resposta.
- **FR-004**: O backend Python MUST continuar responsavel por perfil pedagogico, RAG, transcricao e geracao de resposta.
- **FR-005**: O sistema MUST suportar respostas em texto, audio e video quando a IA ou a regra de negocio solicitar.
- **FR-006**: O sistema MUST tratar audio incompreensivel com uma resposta gentil de novo envio.
- **FR-007**: O sistema MUST registrar o historico minimo necessario para rastrear a interacao de ponta a ponta.
- **FR-008**: O contrato Node -> Python MUST ser estavel e versionado para permitir evolucao independente.
- **FR-009**: Segredos do WhatsApp, IA e armazenamento MUST ficar fora do repositorio.
- **FR-010**: Logs MUST permitir correlacionar um evento do WhatsApp ao processamento no Python e ao envio final no Node.

### Key Entities

- **WhatsAppSession**: representa a sessao ativa do cliente Node, incluindo estado de login e reconexao.
- **InboundMessage**: representa a mensagem recebida do WhatsApp, ja normalizada pelo Node.
- **ProcessingResult**: representa a resposta do backend Python, com acao, conteudo, tipo de midia e metadados.
- **MediaArtifact**: representa um arquivo de audio ou video gerado pelo backend para envio pelo Node.
- **LearnerProfile**: representa o aluno e seu nivel pedagogico no backend Python.

## Success Criteria

- **SC-001**: O Node consegue receber e encaminhar mensagens com sucesso em pelo menos 95% dos testes de integracao locais.
- **SC-002**: O backend Python responde com texto ou instrucoes de midia em menos de 5 segundos para mensagens simples em ambiente local.
- **SC-003**: Em 100% dos casos de audio incompreensivel, o aluno recebe fallback gentil em vez de resposta inventada.
- **SC-004**: O sistema consegue recuperar uma sessao Node apos reinicio sem exigir reconfiguracao completa em cada ciclo de desenvolvimento.

## Assumptions

- O Node sera o ponto de contato com WhatsApp e o Python nao falara diretamente com a Meta.
- O backend Python continuara usando Flask para a API interna, a menos que a equipe decida trocar isso em uma proposta separada.
- Respostas em audio ou video podem ser entregues como caminho local, URL temporaria ou chave de storage, desde que o Node consiga publicar a midia.