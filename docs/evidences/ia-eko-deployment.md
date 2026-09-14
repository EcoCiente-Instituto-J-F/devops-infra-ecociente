\# Evidência de Deployment — IA Eko



\## 1. Objetivo



Este documento registra as evidências técnicas do deployment da IA Eko na infraestrutura AWS do projeto EcoCiente.



A aplicação foi implantada utilizando o Helm Chart reutilizável do repositório `devops-infra-ecociente`, seguindo o mesmo padrão utilizado pelas APIs de Autenticação, Cadastro e Calendário.



O objetivo desta primeira implantação foi validar:



\- Docker;

\- Helm;

\- Kubernetes;

\- AWS;

\- AWS Systems Manager;

\- GitHub Actions;

\- pipeline de deployment;

\- inicialização da FastAPI;

\- Service Kubernetes;

\- health check;

\- Swagger UI.



Nenhuma alteração funcional foi realizada no código da IA Eko durante esta etapa.



\---



\## 2. Pull Request



Pull Request responsável por adicionar a IA Eko à infraestrutura:



\*\*PR #10 — feat: add IA Eko Helm deployment\*\*



Link:



https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente/pull/10



A Pull Request passou pelo fluxo de revisão e foi aprovada antes do merge na branch `main`.



Commit da implementação:



```text

1d711ff feat: add IA Eko Helm deployment

```



Commit de merge:



```text

a619648 Merge pull request #10 from EcoCiente-Instituto-J-F/feat/deploy-ia-eko

```



\---



\## 3. Configuração Helm



Arquivo de configuração da aplicação:



```text

kubernetes/aws/apps/ia-eko/values.yaml

```



Imagem utilizada:



```text

ecociente/ecociente:ia-eko-1.0.1

```



Porta da aplicação:



```text

8000

```



Número inicial de réplicas:



```text

1

```



Service:



```text

ia-eko-service

```



Tipo:



```text

ClusterIP

```



Ingress:



```text

desabilitado

```



\---



\## 4. Configuração inicial da IA



Para o primeiro deployment de infraestrutura foram utilizadas as seguintes configurações:



```text

LLM\_PROVIDER=mock

EMBEDDING\_PROVIDER=mock

STORAGE\_MODE=memory

ALLOW\_STORAGE\_FALLBACK=true

ENABLE\_EXTERNAL\_SOURCE=false

```



Essa estratégia permite validar completamente o container e a infraestrutura sem depender de serviços externos ainda em evolução funcional.



As integrações externas serão habilitadas posteriormente conforme a equipe responsável pela IA finalizar e validar cada dependência.



\---



\## 5. Recursos Kubernetes



Requests configurados:



```text

CPU: 250m

Memória: 512Mi

```



Limits configurados:



```text

CPU: 1

Memória: 1Gi

```



Configuração preventiva do pool PostgreSQL:



```text

POSTGRES\_POOL\_MIN=1

POSTGRES\_POOL\_MAX=2

POSTGRES\_CONNECT\_TIMEOUT=3

```



O limite reduzido foi adotado para evitar consumo excessivo de conexões no PostgreSQL compartilhado quando essa integração for ativada.



\---



\## 6. Secret Kubernetes



Foi criado no namespace `ecociente`:



```text

ia-eko-secret

```



Tipo:



```text

Opaque

```



Durante o primeiro deployment:



```text

DATA: 0

```



O Secret permanece vazio porque o deployment inicial utiliza providers mock e armazenamento em memória.



Nenhuma credencial real foi adicionada ao Git.



O repositório contém somente:



```text

kubernetes/aws/apps/ia-eko/secret.example.yaml

```



com placeholders.



\---



\## 7. Pipeline de CD



Workflow utilizado:



```text

.github/workflows/deploy-aws.yaml

```



Aplicação selecionada:



```text

ia-eko

```



Execução validada:



```text

Run ID: 34838821604

Status: success

```



Link:



https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente/actions/runs/34838821604



Fluxo executado:



```text

GitHub Actions

&#x20;     ↓

AWS credentials

&#x20;     ↓

AWS Systems Manager

&#x20;     ↓

EC2

&#x20;     ↓

k3s

&#x20;     ↓

Helm

&#x20;     ↓

Deployment

```



A primeira tentativa de execução falhou porque as credenciais temporárias do AWS Academy armazenadas no GitHub Environment haviam expirado.



Após a renovação segura dos Secrets do ambiente `aws-lab`, uma nova execução concluiu o deployment com sucesso.



Isso também validou o comportamento esperado das credenciais temporárias do AWS Academy.



\---



\## 8. Helm



Após o deployment:



```text

NAME        NAMESPACE   REVISION   STATUS

ia-eko      ecociente   1          deployed

```



Chart utilizado:



```text

ecociente-api-0.1.0

```



A aplicação passou a ser gerenciada através do mesmo Helm Chart reutilizável utilizado pelos demais serviços do EcoCiente.



\---



\## 9. Deployment Kubernetes



Resultado validado:



```text

NAME     READY   UP-TO-DATE   AVAILABLE

ia-eko   1/1     1            1

```



Imagem:



```text

ecociente/ecociente:ia-eko-1.0.1

```



Selector:



```text

app=ia-eko

```



\---



\## 10. Pod



Pod validado:



```text

ia-eko-7fc79cb57-7z9bd

```



Estado:



```text

READY: 1/1

STATUS: Running

RESTARTS: 0

```



O Pod foi criado no node:



```text

ip-10-20-1-105.ec2.internal

```



Durante a validação não houve reinicializações.



\---



\## 11. Service Kubernetes



Service:



```text

ia-eko-service

```



Tipo:



```text

ClusterIP

```



Porta:



```text

8000/TCP

```



Selector:



```text

app=ia-eko

```



Durante a validação, o ClusterIP atribuído foi:



```text

10.43.172.230

```



Esse IP é interno e dinâmico do Kubernetes e não deve ser considerado um endereço permanente da aplicação.



\---



\## 12. Logs da aplicação



Os logs confirmaram o início correto da FastAPI:



```text

Started server process

Waiting for application startup.

Application startup complete.

Uvicorn running on http://0.0.0.0:8000

```



O FAISS tentou inicialmente carregar variantes otimizadas para AVX512 e AVX2.



Essas variantes específicas não estavam disponíveis, mas a biblioteca realizou fallback e foi carregada corretamente:



```text

Successfully loaded faiss.

```



Portanto, esse comportamento não impediu a inicialização da aplicação.



\---



\## 13. Teste do endpoint raiz



Endpoint:



```text

/

```



Resultado:



```text

HTTP/1.1 200 OK

```



Resposta:



```json

{

&#x20; "name": "EcoCiente Eko Chatbot",

&#x20; "version": "1.9.0",

&#x20; "status": "online",

&#x20; "docs": "/docs"

}

```



Isso comprovou que o Service Kubernetes conseguiu encaminhar corretamente a requisição até o Pod da FastAPI.



\---



\## 14. Health Check



Endpoint:



```text

/health

```



Resultado:



```text

HTTP/1.1 200 OK

```



Resposta:



```json

{

&#x20; "status": "ok",

&#x20; "services": {

&#x20;   "mongodb": "memory\_fallback",

&#x20;   "redis": "memory\_fallback",

&#x20;   "rag": "ok\_local\_fallback",

&#x20;   "llm": "mock",

&#x20;   "postgres": "not\_configured",

&#x20;   "calendar\_api": "not\_configured"

&#x20; }

}

```



O resultado é compatível com o modo inicial configurado.



MongoDB e Redis aparecem como:



```text

memory\_fallback

```



porque o deployment utiliza:



```text

STORAGE\_MODE=memory

```



O LLM aparece como:



```text

mock

```



porque:



```text

LLM\_PROVIDER=mock

```



PostgreSQL e Calendar API não foram configurados nesta etapa.



Esses estados não representam falha de infraestrutura.



\---



\## 15. Swagger UI



Endpoint:



```text

/docs

```



Resultado:



```text

HTTP/1.1 200 OK

```



Content-Type:



```text

text/html; charset=utf-8

```



A página retornada corresponde ao Swagger UI da aplicação:



```text

EcoCiente Eko Chatbot - Swagger UI

```



\---



\## 16. Dependências ainda não ativadas



Durante a preparação da infraestrutura foram analisados Qdrant e Neo4j.



\### Qdrant



Existe atualmente:



```text

src/services/qdrant\_service.py

```



com uso de:



```python

from qdrant\_client import QdrantClient

```



Porém `qdrant-client` não está declarado nos arquivos de requirements utilizados pela aplicação.



Também não foi encontrada integração do serviço com o runtime principal atualmente inicializado pela FastAPI.



Por isso Qdrant não foi considerado uma dependência ativa deste deployment.



\### Neo4j



Existem variáveis relacionadas ao Neo4j no `.env.example`.



Entretanto, durante a análise não foram encontrados:



\- configuração correspondente no objeto `Settings`;

\- utilização no runtime principal;

\- importação do cliente Neo4j;

\- dependência Python `neo4j` nos requirements.



Por isso Neo4j também não foi incluído como dependência ativa da infraestrutura desta etapa.



Esses pontos deverão ser tratados pela equipe responsável pela implementação funcional da IA caso façam parte da versão final.



\---



\## 17. Segurança



Nenhum Secret real foi adicionado ao repositório.



As credenciais AWS utilizadas pelo pipeline estão armazenadas como GitHub Environment Secrets no ambiente:



```text

aws-lab

```



Secrets utilizados:



```text

AWS\_ACCESS\_KEY\_ID

AWS\_SECRET\_ACCESS\_KEY

AWS\_SESSION\_TOKEN

```



A identificação da EC2 é armazenada como Environment Variable:



```text

EC2\_INSTANCE\_ID

```



As credenciais do AWS Academy são temporárias e precisam ser renovadas quando a sessão expira.



Os valores das credenciais não devem ser registrados em documentação, commits ou logs públicos.



\---



\## 18. Encerramento da infraestrutura



Após concluir os testes, a instância EC2 foi parada para evitar utilização desnecessária dos recursos do laboratório.



Estado final validado:



```text

stopped

```



\---



\## 19. Resultado final



O deployment da IA Eko foi considerado bem-sucedido.



Foram comprovados:



```text

Docker image                OK

GitHub Pull Request         OK

Code Review                 OK

Merge na main               OK

GitHub Actions CD           OK

AWS credentials             OK

AWS Systems Manager         OK

k3s                         OK

Helm                        OK

Deployment                  OK

Pod                         OK

Service                     OK

FastAPI                     OK

Health Check                OK

Swagger                     OK

HTTP 200                    OK

Secret management           OK

Encerramento da EC2         OK

```



Com isso, a IA Eko passa a integrar oficialmente a infraestrutura Kubernetes do EcoCiente junto às APIs de Autenticação, Cadastro e Calendário.

