# Redis interno do EcoCiente (k3s / AWS Academy)

## Situacao
A auditoria via `kubectl get pods,svc,statefulsets -A | grep -i redis` nao encontrou Redis. Esta PR prepara uma instalacao interna **manual**; nao modifica o cluster ao fazer merge. Nao e parte da PR #44 de Neon.

## Arquitetura
- Redis 7.4 Alpine, StatefulSet com **1 replica** (sem alta disponibilidade).
- Namespace `ecociente`; Service `redis.ecociente.svc.cluster.local:6379` tipo ClusterIP; sem Ingress, LoadBalancer ou NodePort.
- `local-path` PVC de 2 GiB e AOF com `appendfsync everysec`, `maxmemory=256mb`, politica `noeviction`; preserva dados em reinicio normal, **nao** oferece backup ou replicacao.
- ACL no Secret `redis-auth`, chave `users.acl`, com senha gerada aleatoriamente; chave `password` para consumo pelas APIs.
- NetworkPolicy restringe ingress de Pods pontuacao-api, mobile-api e ia-eko **apenas se o CNI implementar enforcement de NetworkPolicy**. K3s com Flannel sem controlador de politicas pode ignorar essa restricao. Em qualquer caso manter ClusterIP, namespace privado e credencial forte.
- Tráfego interno TCP do Redis **nao tem TLS** neste manifesto. Nao usar com clientes fora do cluster.

## PRE-REQUISITOS (antes de instalar)
1. Validar o StorageClass: `sudo k3s kubectl get storageclass`, e confirmar `local-path`.
2. Conferir capacidade de disco e memoria disponivel na EC2. PersistentVolume local pode nao sobreviver a destruicao da instancia/volume.
3. Realizar snapshot de backup do volume EC2 e definir restauracao/backup de Redis. Redis e cache/ranking derivado de PostgreSQL, mas deve haver estrategia de reconstrucao; sessoes e locks sao volateis.
4. Confirmar que nenhum Redis de producao externo precisa ser migrado e revisar quem sera o unico executor dos jobs de pontuacao.
5. Nao utilizar `scripts/deploy-app.sh redis`; este nao e o chart de APIs.

## Instalacao autorizada, somente apos revisao
Nao fazer deploy automatico. Apos merge **desta PR de Redis** (separada da PR #44), conectar por SSM, dentro do repositorio de infraestrutura atualizado na `main`, executar:

```bash
cd /home/ssm-user/devops-infra-ecociente
sudo -u ssm-user -H git -C "$PWD" fetch origin main
sudo -u ssm-user -H git -C "$PWD" checkout main
sudo -u ssm-user -H git -C "$PWD" pull --ff-only origin main
bash scripts/install-redis-k3s.sh
```

O script verifica se `redis-auth` ja existe (nao rotaciona automaticamente), gera senha aleatoria com Python e ACL usando SHA-256, cria o Secret, apaga arquivos temporarios e aplica os recursos. Nao imprime a senha. **No GitHub nao ha senha real.** Kubernetes Secrets nao substituem criptografia de backup/etcd.

## Verificacao sem exibir senhas
```bash
sudo k3s kubectl -n ecociente get pods,svc,pvc,statefulset -l app=redis
sudo k3s kubectl -n ecociente get pvc data-redis-0
sudo k3s kubectl -n ecociente rollout status statefulset/redis --timeout=240s
sudo k3s kubectl -n ecociente logs statefulset/redis --tail=30
```

O Pod precisa estar Ready; o PVC, Bound. Nenhuma rota publica do Redis deve existir. Probes autenticam via `REDISCLI_AUTH` e `redis-cli ping`.

## Integracao com Pontuacao e Mobile
- Host: `redis.ecociente.svc.cluster.local`
- Porta: `6379`
- Username: default (usar valor `default` caso a biblioteca exija, ou configurar omitido)
- Senha: `redis-auth.data.password` injetada no Secret/Deployment, **nunca impressa**.
- A configuracao da API de Pontuacao tambem exige PostgreSQL Neon e JWT. Nao alterar um Deployment sem preflight de Hibernate/Redis.
- Os jobs `RedisPendingSyncJob` e `PostValidationClosingJob` existem em Pontuacao e Mobile: garantir apenas um executor por responsabilidade na migracao, para evitar processamento duplicado.

## Integracao com IA Eko
- `REDIS_URL` sera injetada via Secret; `STORAGE_MODE=external` requer tambem MongoDB e demais servicos externos.
- Redis nao substitui PostgreSQL nem MongoDB, e nao habilita um provedor LLM real automaticamente.

## Desinstalacao / restauracao
Nao deletar `PVC` nem `redis-auth` durante rollbacks sem backup validado. Desinstalar manifests nao equivale a restaurar rankings ou sessoes. AOF com `everysec` pode perder ate aproximadamente um segundo de gravacoes em uma queda abrupta, alem de nao substituir um backup.
