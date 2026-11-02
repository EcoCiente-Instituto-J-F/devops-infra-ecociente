# Validação da autenticação Neon e CORS do GitHub Pages

Esta preparação **não modifica código Java nem efetua migração automática**.
A DAD 1.0.1 está implantada na AWS, enquanto a release autenticacao permanece com `autenticacao-secret` (Aiven).
O `autenticacao-neon-secret` existe, e o operador confirmou que os JWT_SECRET em Aiven/Neon são iguais.
A origem do Pages é `https://ecociente-instituto-j-f.github.io`.

## Primeiro: canário isolado, sem Ingress

Conferir que o cluster aceita o Helm chart e verificar a autorização de uso do Secret. Em uma sessão SSM:

```bash
sudo k3s kubectl -n ecociente get secret autenticacao-neon-secret
sudo k3s kubectl api-resources | grep -i middleware
sudo k3s kubectl -n ecociente get deployment autenticacao-api
sudo k3s kubectl -n ecociente get ingress autenticacao-api-ingress -o yaml
```

**Não mudar a release autenticacao antes de validar a conectividade com Neon e a conta ADMIN no banco destino.**

O canário usa apenas o `values.yaml` existente na main, sob nomes próprios, sem Ingress. Verifique primeiro disponibilidade de memória, compatibilidade do Java e autorização de intervenção:

```bash
cd /home/ssm-user/devops-infra-ecociente
git fetch origin main
git checkout main
git pull --ff-only origin main
sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm upgrade --install autenticacao-neon-canary kubernetes/aws/charts/ecociente-api \
  -n ecociente -f kubernetes/aws/apps/autenticacao/values.yaml \
  --set fullnameOverride=autenticacao-neon-canary \
  --set configMap.nameOverride=autenticacao-neon-canary-config \
  --set secret.existingSecret=autenticacao-neon-secret \
  --set ingress.enabled=false \
  --set service.enabled=true \
  --wait --timeout 5m
sudo k3s kubectl -n ecociente get pods -l app.kubernetes.io/instance=autenticacao-neon-canary
sudo k3s kubectl -n ecociente logs deployment/autenticacao-neon-canary --tail=80
```

Se o canário não subir, investigar eventos/logs. Não alterar a autenticação principal.

Após testar login com credenciais de **teste** pela rede interna, remover o canário:

```bash
sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm uninstall autenticacao-neon-canary -n ecociente
```

## Segundo: CORS no Ingress, sem alterar o Java

O arquivo `kubernetes/aws/autenticacao/pages-cors-middleware.yaml` cria um Middleware isolado de CORS limitado ao Pages e `POST /auth/login`. A configuração não surtirá efeito até **aplicar** o arquivo e **associar** o middleware ao Ingress de autenticação. Isso deve ser feito numa alteração separada e revisada (evitar substituir annotations existentes).

```bash
sudo k3s kubectl api-resources | grep -i middleware
```

Depois da validação da CRD, aplicar o middleware e anexar a annotation:

```yaml
traefik.ingress.kubernetes.io/router.middlewares: ecociente-autenticacao-pages-cors@kubernetescrd
```

Atenção: a annotation do Ingress é gerida por Helm; adicionar através do `values.yaml` da autenticação em PR separada. Não editar o Ingress em produção manualmente sem controle de mudanças.

Teste após rollout:

```powershell
curl.exe -i -X OPTIONS "https://api.52.71.117.143.sslip.io/auth/login" -H "Origin: https://ecociente-instituto-j-f.github.io" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"
```

Exigir cabeçalho `Access-Control-Allow-Origin: https://ecociente-instituto-j-f.github.io`. CORS no Traefik não é controle de autenticação; Spring Security e JWT continuam responsáveis.

## Terceiro: cutover e frontend

Somente após canário validado, preparar PR de `kubernetes/aws/apps/autenticacao/values.yaml` trocando `existingSecret: autenticacao-secret` por `autenticacao-neon-secret` e vinculando o Middleware do Pages. O merge dispara Auto Deploy AWS; revisar impactos antes.

No repositório `dad-crud`, configurar como **Actions Variables**:
- `VITE_DAD_API_URL=https://api.52.71.117.143.sslip.io`
- `VITE_AUTH_API_URL=https://api.52.71.117.143.sslip.io`

As duas variáveis restantes dependem da publicação real das rotas de cadastro e senha. Não colocar URLs de API privada ou localhost no Pages.
Depois executar `Deploy GitHub Pages` novamente para recompilar as variáveis.

Validar login ADMIN em Neon, leitura da DAD, atualização controlada e consulta independente do registro no Neon; restaurar dados de teste ao final.
