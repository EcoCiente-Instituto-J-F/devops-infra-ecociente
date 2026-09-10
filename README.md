# EcoCiente - DevOps Infrastructure

Repositório central responsável pela infraestrutura, Cloud, orquestração e automações DevOps do projeto EcoCiente.

> Dados que despertam a consciência.

## Objetivo

Este repositório mantém a infraestrutura global utilizada pelos serviços do EcoCiente.

As configurações específicas de cada aplicação, como Dockerfile e manifests Kubernetes próprios do serviço, permanecem nos respectivos repositórios.

Este repositório concentra recursos compartilhados e configurações relacionadas aos ambientes em que o EcoCiente é executado.

## Ambientes

### DEV

Ambiente utilizado pelos desenvolvedores durante o desenvolvimento e testes locais.

Principais tecnologias:

- Docker Desktop
- Kubernetes local
- Android Studio
- APIs executadas localmente quando necessário

Os serviços locais devem ser executados somente quando necessários, evitando consumo desnecessário de recursos e conexões com os bancos compartilhados.

### QA

Ambiente temporário utilizado para validação de infraestrutura e versões candidatas.

Infraestrutura:

- AWS Academy Lab
- Terraform
- Kubernetes

O ambiente de QA é efêmero e não é uma dependência para o funcionamento principal do EcoCiente.

### STAGING

Ambiente principal e persistente do projeto.

Infraestrutura planejada:

- Google Cloud Platform
- Compute Engine
- Kubernetes com k3s
- Ingress
- HTTPS
- APIs do EcoCiente

O aplicativo mobile e demais clientes poderão consumir as APIs hospedadas nesse ambiente através da Internet.

## Banco de Dados

Os ambientes DEV, QA e STAGING utilizam o mesmo banco PostgreSQL gerenciado externamente.

Por esse motivo, o consumo de conexões deve ser controlado entre os ambientes.

O ambiente STAGING é o principal consumidor persistente.

Os ambientes DEV e QA devem executar apenas os serviços necessários durante testes e desenvolvimento.

Outros serviços de dados utilizados pelo projeto, como MongoDB, Redis, Neo4j e Firebase, permanecem externos à infraestrutura deste repositório enquanto não houver necessidade arquitetural de provisioná-los diretamente.

## Responsabilidades

### Este repositório

Responsável por:

- Terraform
- infraestrutura GCP
- infraestrutura AWS QA
- recursos Kubernetes compartilhados
- Ingress
- HTTPS
- scripts de infraestrutura
- automações de implantação
- documentação arquitetural
- documentação operacional
- evidências de DevOps

### Repositórios das aplicações

Cada aplicação continua responsável por sua própria configuração.

Exemplos:

- código-fonte
- Dockerfile
- docker-compose.yml quando aplicável
- configuração de CI
- Deployment Kubernetes
- Service Kubernetes
- ConfigMap específico
- exemplo de Secret

## Estrutura

```text
devops-infra-ecociente/
├── terraform/
│   ├── gcp/
│   └── aws-qa/
├── kubernetes/
│   ├── staging/
│   └── qa/
├── scripts/
├── docs/
│   ├── architecture/
│   ├── runbooks/
│   └── evidences/
├── .gitignore
└── README.md