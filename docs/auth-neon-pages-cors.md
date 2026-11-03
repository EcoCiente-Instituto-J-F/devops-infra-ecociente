# Autenticacao Neon 1.0.2 e CORS no GitHub Pages

## Validado no canario
- Autenticacao 1.0.2, banco Neon: Pod Ready.
- Login ADMIN: HTTP 200, perfil ADMIN.
- DAD AWS com token do canario: HTTP 200.
- JWT_SECRET Aiven e Neon equivalentes.
- DAD HTTPS e CORS validados separadamente.

## Nesta PR
- Atualiza a imagem da autenticacao para 1.0.2.
- Seleciona autenticacao-neon-secret.
- Adiciona Middleware Traefik gerenciado pelo mesmo Helm release.
- Aplica anotacao do Ingress para o Middleware, autorizando a origem do Pages nos metodos POST e OPTIONS.
- O Middleware fica desativado por padrao para as outras APIs.
- Nenhuma alteracao Java, SQL, credenciais ou outros Deployments.

## Gates de revisao
- CI Helm aprovada.
- Secret autenticacao-neon-secret presente no cluster.
- Middleware CRD instalado e canario 1.0.2 saudavel.
- Credenciais temporarias AWS Learner Lab atualizadas.
- O merge altera values.yaml e dispara Auto Deploy AWS.

## Pos-deploy: verificacoes
Na AWS via SSM:

```bash
sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm status autenticacao -n ecociente
sudo k3s kubectl -n ecociente get deployment autenticacao-api
sudo k3s kubectl -n ecociente get pods -l app=autenticacao-api
sudo k3s kubectl -n ecociente get middleware autenticacao-pages-cors
sudo k3s kubectl -n ecociente get ingress autenticacao-api-ingress
```

Na maquina Windows:

```powershell
curl.exe -i -X OPTIONS "https://api.52.71.117.143.sslip.io/auth/login" -H "Origin: https://ecociente-instituto-j-f.github.io" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type"
```

Esperado: status 200 ou 204 e Access-Control-Allow-Origin da origem GitHub Pages. Fazer login administrativo real via HTTPS e testar a DAD.

## Rollback
Se surgir erro, consultar o historico Helm:
```bash
sudo env KUBECONFIG=/etc/rancher/k3s/k3s.yaml helm history autenticacao -n ecociente
```
O deploy usa --rollback-on-failure. Se necessario, revisar retorno para revisao anterior; isso reativa Aiven. Manter canario ate validacao completa.

## Frontend
No dad-crud, configurar GitHub Actions Variables:
- VITE_AUTH_API_URL=https://api.52.71.117.143.sslip.io
- VITE_DAD_API_URL=https://api.52.71.117.143.sslip.io

Recompilar GitHub Pages apos configurar. Cadastro ainda usa Aiven e EsqueceuSenha nao tem Ingress publico; revisar separadamente.
