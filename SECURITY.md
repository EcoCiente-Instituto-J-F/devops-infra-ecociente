# Política de Segurança

O devops-infra-ecociente define a infraestrutura do EcoCiente na AWS (Terraform, k3s e manifests/charts Kubernetes) e os workflows de deploy. Ele não guarda dados de usuários, mas manipula credenciais de acesso à AWS, ao banco e às aplicações, que ficam fora do repositório.

## Versões suportadas

| Versão | Suporte |
| --- | --- |
| `main` (mais recente) | Sim |
| Demais branches | Não |

## Reportando uma vulnerabilidade

**Não abra issue, Pull Request ou discussão pública** para relatar vulnerabilidades.

Use o relato privado do GitHub: <https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente/security/advisories/new> (Security → Advisories → Report a vulnerability).

> Mantenedores: ative *Private vulnerability reporting* em Settings → Code security.

Inclua no relato:

- o impacto da falha;
- os passos para reproduzir, usando **dados fictícios**;
- o commit testado e a configuração;
- se possível, uma ideia de correção.

Depois do relato: confirmaremos o recebimento, corrigiremos de forma privada e publicaremos um advisory com crédito a quem reportou, se desejado. Pedimos um prazo razoável para a correção antes de qualquer divulgação pública.

## Escopo

**Dentro do escopo**

- Segredos, credenciais AWS, tokens ou senhas commitados no repositório ou expostos em logs de workflows
- Workflows que permitam execução de código não confiável com acesso aos segredos (`deploy-aws.yaml`, `auto-deploy-aws.yaml`, `update-image-tag.yaml`)
- Injeção de comandos nos scripts (`scripts/deploy-app.sh` e demais)
- Regras de rede ou permissões excessivas (Security Group, IAM)
- Manifests que exponham serviços ou segredos indevidamente

**Fora do escopo**

- Bugs sem impacto de segurança
- Falhas em serviços de terceiros (AWS, GitHub, Let's Encrypt)
- Limitações do AWS Academy Learner Lab
- Negação de serviço no próprio ambiente

## Como o sistema protege os dados

| Camada | Onde | O que faz |
| --- | --- | --- |
| Rede | `terraform/aws/security.tf` | Security Group libera entrada apenas nas portas 80 (HTTP) e 443 (HTTPS) |
| Acesso à instância | `.github/workflows/deploy-aws.yaml` | O deploy usa AWS Systems Manager (`ssm send-command`), sem abrir porta SSH |
| Segredos | `.gitignore`, `kubernetes/aws/**/secret.example.yaml` | Estado do Terraform e `*.tfvars` ignorados; só há exemplos de Secret com valores `<...>` |
| Validação de entrada | `scripts/deploy-app.sh` | Valida o nome da aplicação e a tag da imagem antes de usá-los |
| Deploy | `deploy-aws.yaml` | `environment: aws-lab` e `concurrency` para impedir deploys simultâneos |
| TLS | `kubernetes/aws/cert-manager/` | Certificados via cert-manager |

## Checklist de deploy

- Credenciais AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`) apenas como *Secrets* do GitHub; as do Learner Lab são temporárias.
- Secrets Kubernetes criados a partir dos exemplos, com valores reais fora do Git.
- Manter só as portas 80 e 443 abertas ao público; não expor endpoints internos (por exemplo, `/metrics`).
- Revisar permissões dos workflows (`permissions:`) e proteger o *environment* `aws-lab`.
- Encerrar o laboratório quando não estiver em uso (veja `docs/runbooks/aws-lab.md`).
