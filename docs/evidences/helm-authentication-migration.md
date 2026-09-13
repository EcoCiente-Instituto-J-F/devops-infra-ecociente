# Evidencia - Migracao da API de Autenticacao para Helm

## Objetivo

Migrar a ds-autenticacao-api, anteriormente implantada com manifests Kubernetes aplicados manualmente, para gerenciamento atraves do Helm.

Tambem foram validados o Helm Upgrade, Rolling Update e Helm Rollback sem alteracao funcional da API.

## Ambiente

- Cloud: AWS Academy Learner Lab
- Regiao: us-east-1
- Instancia: EC2 t3.large
- Sistema operacional: Amazon Linux 2023
- Orquestrador: k3s
- Ingress Controller: Traefik
- Namespace: ecociente
- Helm: v4.3.0
- Aplicacao: ds-autenticacao-api
- Imagem: ecociente/ecociente:autenticacao-1.0.0
- Porta: 9801

## Estado inicial

Antes da migracao, os seguintes recursos ja estavam implantados:

- Deployment: autenticacao-api
- Service: autenticacao-api-service
- Ingress: autenticacao-api-ingress
- ConfigMap: autenticacao-config
- Secret: autenticacao-secret

Estado validado:

- Deployment: 1/1
- Pod: 1/1 Running
- Swagger: HTTP 200
- OpenAPI: HTTP 200

## Validacao do Helm Chart

Foi executado:

    helm lint kubernetes/aws/charts/ecociente-api -f kubernetes/aws/apps/autenticacao/values.yaml

Resultado:

    1 chart(s) linted, 0 chart(s) failed

## Dry-run

Antes da instalacao real foi executado um dry-run contra o cluster:

    sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install autenticacao kubernetes/aws/charts/ecociente-api -f kubernetes/aws/apps/autenticacao/values.yaml --namespace ecociente --take-ownership --dry-run=server --hide-secret

Resultado:

- STATUS: pending-install
- DESCRIPTION: Dry run complete

Foram renderizados ConfigMap, Service, Deployment e Ingress.

O Secret real nao e armazenado no Helm Chart. O Deployment apenas referencia:

    autenticacao-secret

## Primeira tentativa de adocao

Na primeira execucao real ocorreram conflitos de field ownership.

Os recursos haviam sido criados anteriormente utilizando kubectl-client-side-apply.

Foram encontrados conflitos em campos do Service e das probes do Deployment.

Mesmo durante a tentativa que falhou, a aplicacao permaneceu disponivel:

- Deployment: 1/1
- Pod: 1/1 Running
- Swagger: HTTP 200

## Transferencia para gerenciamento pelo Helm

Foi realizada explicitamente a transferencia do gerenciamento dos recursos para o Helm.

Comando utilizado:

    sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install autenticacao kubernetes/aws/charts/ecociente-api -f kubernetes/aws/apps/autenticacao/values.yaml --namespace ecociente --take-ownership --server-side=true --force-conflicts --wait --timeout 5m

Resultado:

- STATUS: deployed
- REVISION: 2
- DESCRIPTION: Upgrade complete

Foi validada a annotation:

    meta.helm.sh/release-name = autenticacao

Tambem foi validada a label:

    app.kubernetes.io/managed-by = Helm

Isso confirmou que o Deployment passou a ser gerenciado pelo Helm.

## Teste de Helm Upgrade

Foi realizado um upgrade controlado adicionando temporariamente a label:

    helmRevision=upgrade-test

Resultado:

- STATUS: deployed
- REVISION: 3
- DESCRIPTION: Upgrade complete

O Kubernetes realizou um novo Rolling Update.

Novo Pod observado:

    autenticacao-api-744875fdc8-dmw8j

Estado:

- READY: 1/1
- STATUS: Running
- RESTARTS: 0

A label helmRevision=upgrade-test foi confirmada no novo Pod.

O rollout foi concluido com sucesso.

A aplicacao permaneceu disponivel:

- SWAGGER_STATUS=200
- OPENAPI_STATUS=200

## Helm Rollback

Apos o teste de upgrade, foi realizado rollback para o estado armazenado na revision 2.

Comando:

    sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm rollback autenticacao 2 -n ecociente --wait --timeout 5m

Resultado:

    Rollback was a success! Happy Helming!

O Helm criou a revision 4 representando o estado restaurado.

## Historico final

Revision 1:
- Status: superseded
- Tentativa inicial com conflito de ownership

Revision 2:
- Status: superseded
- Migracao concluida

Revision 3:
- Status: superseded
- Teste de Helm Upgrade

Revision 4:
- Status: deployed
- Rollback to 2

## Validacao apos rollback

Apos o rollback foi criado o Pod:

    autenticacao-api-7cb945bfc6-x7sk9

Estado:

- READY: 1/1
- STATUS: Running
- RESTARTS: 0

A label helmRevision=upgrade-test nao estava mais presente.

A aplicacao permaneceu saudavel:

- SWAGGER_STATUS=200
- OPENAPI_STATUS=200

## Estado final

- Helm Release: autenticacao
- Revision ativa: 4
- Status: deployed
- Deployment: 1/1
- Pod: 1/1 Running
- Swagger: HTTP 200
- OpenAPI: HTTP 200

O Secret autenticacao-secret permanece separado do Helm Chart e fora do versionamento Git.

## Conclusao

Foram validados com sucesso:

- Helm Chart reutilizavel
- adocao de recursos Kubernetes existentes
- Server-Side Apply
- Helm Upgrade
- Rolling Update
- Helm Rollback
- restauracao do estado anterior
- disponibilidade da aplicacao apos upgrade e rollback

A proxima etapa e automatizar esse processo utilizando Continuous Deployment.
