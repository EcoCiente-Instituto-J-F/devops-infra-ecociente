# Contribuindo com o devops-infra-ecociente

Ao participar, você concorda em seguir o [Código de Conduta](CODE_OF_CONDUCT.md). Para reportar um problema de segurança, **não** abra uma issue — siga o [SECURITY.md](SECURITY.md).

## Idioma

Documentação, issues, Pull Requests e mensagens ao usuário em português do Brasil.

## Configurando o ambiente

1. Instale as ferramentas conforme a área que for alterar: Terraform 1.6+ (provider AWS `~> 6.0`), `kubectl` e Helm.
2. Clone o repositório:
   ```bash
   git clone https://github.com/EcoCiente-Instituto-J-F/devops-infra-ecociente.git\n   cd devops-infra-ecociente\n   ```\n3. Para o Terraform, copie `terraform/aws/terraform.tfvars.example` para `terraform/aws/terraform.tfvars` (ignorado pelo Git).\n4. O ambiente é o AWS Academy Learner Lab; o passo a passo operacional está em `docs/runbooks/aws-lab.md`.

## Testando sua mudança

Este repositório não tem testes automatizados. Valide a mudança antes da PR:

```bash
terraform -chdir=terraform/aws fmt -check
terraform -chdir=terraform/aws validate
helm lint kubernetes/aws/charts/ecociente-api
```

Faça `terraform plan` e revise o resultado. Não aplique mudanças em um ambiente real sem aprovação de um mantenedor.

Mudanças de infraestrutura devem registrar na PR o impacto esperado e como reverter.

## Regras do projeto

- Nenhum segredo (chaves, tokens, senhas) no repositório.
- Nenhum dado pessoal real em testes, fixtures ou exemplos.
- Nenhuma dependência nova sem discussão prévia.
- Nenhum segredo no repositório: use apenas arquivos `*.example` (por exemplo, `secret.example.yaml`, `terraform.tfvars.example`); `*.tfvars`, estado do Terraform e credenciais ficam fora do Git.
- Cada aplicação tem seu `values.yaml` em `kubernetes/aws/apps/<app>/`; o chart compartilhado é `kubernetes/aws/charts/ecociente-api`.
- As tags das imagens são atualizadas pelo workflow `update-image-tag.yaml` (PR automática de um bot); não edite a tag manualmente sem necessidade.
- Mudanças em Security Groups, portas ou permissões exigem justificativa na PR.
- Documente decisões e evidências em `docs/`.

## Pull requests

1. Crie uma branch a partir da `main` (ex.: `feat/nome-da-mudanca`).
2. Faça commits focados com prefixos `feat:`, `fix:`, `chore:`, `docs:`, `test:` ou `refactor:`.
3. Abra a PR para a `main`. Descreva o que mudou e por quê.
4. O CI precisa passar (quando houver) e um mantenedor revisa antes do merge.

## Reportando bugs e propondo funcionalidades

Abra uma issue com o comportamento esperado, o observado, os passos para reproduzir e a versão. Use dados fictícios. Para vulnerabilidades, siga o [SECURITY.md](SECURITY.md).
