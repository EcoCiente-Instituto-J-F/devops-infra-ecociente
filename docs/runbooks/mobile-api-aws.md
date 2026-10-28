# EcoCiente — primeiro deploy interno da ds-mobile-api na AWS

## Objetivo

Preparar uma implantação inicial **sem acesso publico** da API Java 21/Spring Boot no k3s, preservando os serviços existentes de Autenticação, Cadastro, Calendário e IA Eko.

- Helm: `kubernetes/aws/apps/mobile/values.yaml`
- Release: `mobile`; Deployment: `mobile-api`; Service: `mobile-api-service`
- Imagem esperada: `ecociente/ecociente:mobile-1.0.1`
- Namespace: `ecociente`
- GitHub Actions: [Deploy AWS](../../.github/workflows/deploy-aws.yaml)
- Alterações de infraestrutura relacionadas: [PR #38](https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente/pull/38). A PR automática [#39](https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente/pull/39) apenas atualiza a mesma tag para `mobile-1.0.1` e deve ser encerrada como redundante **após** integração da #38.

## Atenção: não fazer merge antes do pré-deploy

O workflow `Auto Deploy AWS` reage a alterações de `kubernetes/aws/apps/*/values.yaml` na `main`. O merge desta PR pode iniciar um deploy automaticamente. Verificar previamente:

1. CI da `ds-mobile-api` na `main` aprovada, **incluindo Testcontainers**.
2. Imagem `ecociente/ecociente:mobile-1.0.1` publicada e disponível no Docker Hub.
3. AWS Learner Lab ativo, EC2 `running`, SSM `Online` e secrets temporários válidos no environment `aws-lab` do GitHub.
4. Secret Kubernetes `mobile-secret` criado no namespace `ecociente` (sem gravar credenciais no repositório).
5. Banco PostgreSQL compartilhado alcançável e schema real compatível com as entidades JPA. A API usa `spring.jpa.hibernate.ddl-auto=validate`, **não** `create` ou `update`.

### Chaves obrigatórias do mobile-secret

| Nome | Significado |
| --- | --- |
| `DB_URL` | JDBC PostgreSQL |
| `DB_USERNAME` | Nome do usuário do banco; atenção: outras APIs usam `DB_USER` |
| `DB_PASSWORD` | Senha do banco |
| `JWT_SECRET` | Mesmo segredo que assina os tokens emitidos pela Autenticação |

Criar o Secret **somente em sessão privada e autorizada da EC2/SSM**; nunca compartilhar valores no chat, logs ou Pull Requests.

As integrações `PONTUACAO_BASE_URL`, `PONTUACAO_TOKEN_SERVICO`, `VALIDADOR_BASE_URL` e `VALIDADOR_CHAVE_API` podem ser configuradas mais tarde; algumas funções de pontuação/voto não funcionarão até então. Os nomes foram conferidos em `ds-mobile-api/src/main/resources/application.properties`. Não confundir `PONTUACAO_TOKEN_SERVICO` com o `JWT_SECRET`.

O segredo `JWT_SECRET` deve ser o mesmo da API Autenticação implantada, pois esta API apenas valida os JWTs emitidos por ela. O `DB_USERNAME` deve ter permissão sobre as tabelas usadas pelo Mobile; não presuma que um usuário restrito à Autenticação já tenha esse acesso.

O `SERVER_PORT=8080` definido no ConfigMap desta PR prevalece sobre a porta `9654` declarada em `application.properties`. O Service e o container devem continuar usando porta 8080.

## Diagnóstico sem revelar valores

Executar na EC2 pelo SSM (Linux):

```bash
sudo systemctl is-active k3s
sudo k3s kubectl -n ecociente get deployments,pods,services,ingresses
sudo k3s kubectl -n ecociente get secret mobile-secret
sudo k3s kubectl -n ecociente describe secret mobile-secret
```

O comando `describe secret` mostra nomes de chaves e tamanhos, sem exibir seus conteúdos. Não executar `-o yaml` nem decodificar credenciais para compartilhar resultados.

Na cópia atualizada do repositório da infraestrutura, validar o Chart:

```bash
cd /home/ssm-user/devops-infra-ecociente
git fetch origin main
helm lint kubernetes/aws/charts/ecociente-api -f kubernetes/aws/apps/mobile/values.yaml
```

Esse comando apenas valida a configuração e não altera o cluster. Antes do merge, a versão da branch desta PR deve estar disponível na EC2 para que o lint valide **a configuração nova**, não a versão antiga ainda presente na `main`.

Antes do deploy, também confirme em consulta **somente de leitura** ao PostgreSQL a existência das tabelas consumidas pelo Mobile e eventuais diferenças de schema. O `ddl-auto=validate` não cria nem corrige tabelas.

## Deploy

Depois de CI, imagem `mobile-1.0.1`, Secret, k3s e banco validados, a equipe pode aprovar e fazer merge. Conferir o workflow **Auto Deploy AWS** antes de disparar qualquer deploy manual. Este merge poderá disparar o primeiro deploy **interno**, portanto deve acontecer somente depois de toda a pré-checagem.

Se não houve implantação automática, abrir o workflow **Deploy AWS**, escolher `application=mobile` e usar `image_tag` vazio para ler a tag do `values.yaml`.

Acompanhar SSM, Helm e rollout sem imprimir segredos.

## Verificação interna

```bash
sudo k3s kubectl -n ecociente get deployment mobile-api
sudo k3s kubectl -n ecociente get pods -l app.kubernetes.io/instance=mobile
sudo k3s kubectl -n ecociente get service mobile-api-service
sudo k3s kubectl -n ecociente rollout status deployment/mobile-api --timeout=240s
sudo k3s kubectl -n ecociente logs deployment/mobile-api --since=10m --tail=100
```

Inspecionar os logs antes de compartilhá-los. Para testar o OpenAPI sem acesso externo, usar dois terminais SSM na mesma EC2:

Terminal 1:

```bash
sudo k3s kubectl -n ecociente port-forward service/mobile-api-service 8080:8080
```

Terminal 2:

```bash
curl -i http://127.0.0.1:8080/api-docs
```

O retorno HTTP 200 comprova conectividade e inicialização básica, **não** valida os fluxos de negócio.

## Próxima etapa

Este primeiro deploy não habilita Ingress: `ingress.enabled=false`. Habilitar HTTPS em PR separada após verificar os caminhos públicos compartilhados (`/auth`, `/api/cadastro`, `/api/v1/agendamentos`, `/api/v1` da IA Eko). Não mudar a URL do Android até que a API interna e o roteamento estejam comprovadamente funcionando.

Em falha, inspecionar Deployment/Pods/Helm e manter as APIs antigas em funcionamento; rollback deve ser aprovado e executado conscientemente, sem apagar banco ou Secrets.
