import base64
import glob
import hmac
import json
import os
import subprocess
import uuid

NS = 'ecociente'
APPS = ('autenticacao', 'cadastro', 'calendario', 'mobile')
K = ['sudo', 'env', 'KUBECONFIG=/etc/rancher/k3s/k3s.yaml', 'kubectl']
REPO = '/home/ssm-user/devops-infra-ecociente'


def run(cmd, inp=None, timeout=60):
    try:
        p = subprocess.run(cmd, input=inp, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 99, ''


def get_json(args, inp=None):
    rc, out = run(args, inp, 90)
    if rc:
        raise RuntimeError('Falha ao consultar infraestrutura')
    return json.loads(out)


def enc(s):
    return base64.b64encode(str(s).encode()).decode()


print('=== ECOCIENTE | PRE-CORTE AIVEN X NEON ===')
print('Modo: auditoria, sem alteracao de Deployments ou Secrets.')
print()

try:
    deployments = get_json(K + ['get', 'deployments', '-n', NS, '-o', 'json'])
    dep = {x['metadata']['name']: x for x in deployments['items']}
    print('[1] ESTADO ATUAL')
    for app in APPS:
        d = dep.get(app + '-api')
        if not d:
            print(app + ': DEPLOYMENT AUSENTE')
            continue
        spec = d['spec']['template']['spec']['containers'][0]
        refs = [x['secretRef']['name'] for x in spec.get('envFrom', [])
                if 'secretRef' in x]
        print('%s: %s/%s Ready | Secret=%s | imagem=%s' % (
            app, d['status'].get('readyReplicas', 0), d['spec'].get('replicas', 1),
            ','.join(refs) or 'NENHUM', spec['image'].split(':')[-1]))
    outras = [d for d in deployments['items']
              if d['metadata']['name'] not in [a + '-api' for a in APPS]]
    print('Outros deployments:', len(outras),
          '| todos disponiveis:', all(x['status'].get('availableReplicas', 0) >= 1
                                     for x in outras))
    print()

    print('[2] SEGREDOS / JWT / AWS')
    nomes = [n for app in APPS for n in (app + '-secret', app + '-neon-secret')]
    objetos = get_json(K + ['get', 'secret', *nomes, '-n', NS, '-o', 'json'])
    secrets = {x['metadata']['name']: x['data'] for x in objetos['items']}
    rc, aws_str = run(['aws', 'secretsmanager', 'get-secret-value',
                       '--secret-id', 'ecociente/neon/postgres', '--region', 'us-east-1',
                       '--query', 'SecretString', '--output', 'text'])
    if rc:
        raise RuntimeError('EC2 nao conseguiu acessar AWS Secrets Manager')
    aws = json.loads(aws_str)
    if (aws.get('host') != 'ep-cold-band-b59ez0ii-pooler.c-7.us-east-2.aws.neon.tech'
            or str(aws.get('port')) != '5432'
            or aws.get('dbname') != 'ecociente'):
        raise RuntimeError('O destino no Secrets Manager nao e o Neon esperado')
    expected = ('jdbc:postgresql://%s:%s/%s?sslmode=require' %
                (aws['host'], aws['port'], aws['dbname']))
    jwt = secrets['autenticacao-secret']['JWT_SECRET']
    all_good = True
    for app in APPS:
        old = secrets[app + '-secret']
        new = secrets[app + '-neon-secret']
        userkey = 'DB_USERNAME' if app == 'mobile' else 'DB_USER'
        changed = {'DB_URL', userkey, 'DB_PASSWORD'}
        checks = [hmac.compare_digest(new.get('DB_URL', ''), enc(expected)),
                  hmac.compare_digest(new.get(userkey, ''), enc(aws['username'])),
                  hmac.compare_digest(new.get('DB_PASSWORD', ''), enc(aws['password'])),
                  hmac.compare_digest(old.get('JWT_SECRET', ''), jwt),
                  hmac.compare_digest(new.get('JWT_SECRET', ''), jwt),
                  set(old) == set(new),
                  all(new.get(k) == v for k, v in old.items() if k not in changed)]
        ok = all(checks)
        all_good &= ok
        print('%s: %s' % (app, 'OK' if ok else 'REVISAR'))
    print('Auditoria Secrets:', 'APROVADA' if all_good else 'REPROVADA')
    print()

    print('[3] SIMULACAO HELM (SEM DEPLOY)')
    chart = os.path.join(REPO, 'kubernetes/aws/charts/ecociente-api')
    for app in APPS:
        v = os.path.join(REPO, 'kubernetes/aws/apps', app, 'values.yaml')
        if not os.path.isfile(v) or not os.path.isdir(chart):
            print(app + ': ARQUIVOS HELM NAO DISPONIVEIS')
            continue
        rc, rendered = run(['helm', 'template', app, chart, '-f', v,
                            '-n', NS, '--set-string',
                            'secret.existingSecret=' + app + '-neon-secret'])
        passed = rc == 0 and ('name: ' + app + '-neon-secret') in rendered
        print('%s: %s' % (app, 'OK' if passed else 'REVISAR'))
    print()

    print('[4] BACKUPS LOCAIS')
    pastas = glob.glob(os.path.expanduser('~/ecociente-rollback-*'))
    print('Diretorios de rollback:', len(pastas))
    print('Backup dos dados PostgreSQL: NAO VERIFICADO POR ESTE TESTE')
    print()

except (KeyError, ValueError, RuntimeError) as e:
    print('ERRO no inventario inicial:', str(e))
    raise SystemExit(1)

print('[5] TESTE ISOLADO DO BANCO (LEITURA, 1 CONEXAO POR VEZ)')
print('Pode haver falha no Aiven se o limite de conexoes estiver cheio.')
name = 'neon-preflight-' + uuid.uuid4().hex[:8]

def env_secret(name, key, secret):
    return {'name': name, 'valueFrom': {'secretKeyRef': {
        'name': secret, 'key': key}}}

pod = {
    'apiVersion': 'v1', 'kind': 'Pod',
    'metadata': {'name': name, 'namespace': NS,
                 'labels': {'app': 'neon-preflight-temp'}},
    'spec': {
        'automountServiceAccountToken': False,
        'restartPolicy': 'Never', 'activeDeadlineSeconds': 600,
        'containers': [{
            'name': 'pg', 'image': 'postgres:16-alpine',
            'command': ['sh', '-c', 'sleep 500'],
            'env': [
                env_secret('AIVEN_URL', 'DB_URL', 'autenticacao-secret'),
                env_secret('AIVEN_USER', 'DB_USER', 'autenticacao-secret'),
                env_secret('AIVEN_PASS', 'DB_PASSWORD', 'autenticacao-secret'),
                env_secret('NEON_URL', 'DB_URL', 'mobile-neon-secret'),
                env_secret('NEON_USER', 'DB_USERNAME', 'mobile-neon-secret'),
                env_secret('NEON_PASS', 'DB_PASSWORD', 'mobile-neon-secret')
            ],
            'resources': {'requests': {'cpu': '10m', 'memory': '32Mi'},
                          'limits': {'cpu': '150m', 'memory': '128Mi'}}
        }]
    }
}

shell = r'''#!/bin/sh
set -u
run_db() {
  label="$1"
  jdbc="$2"
  usuario="$3"
  senha="$4"
  case "$jdbc" in
    jdbc:postgresql://*) ;;
    *) printf 'DB_FAIL:%s:INVALID_JDBC_URL\n' "$label"; return ;;
  esac
  uri="${jdbc#jdbc:postgresql://}"
  hostport="${uri%%/*}"
  db="${uri#*/}"
  db="${db%%\?*}"
  host="${hostport%%:*}"
  port="${hostport##*:}"
  [ "$port" = "$hostport" ] && port=5432
  export PGHOST="$host" PGPORT="$port" PGDATABASE="$db"
  export PGUSER="$usuario" PGPASSWORD="$senha"
  export PGSSLMODE=require PGCONNECT_TIMEOUT=7
  if result="$(psql -X -Atq -F '|' -P pager=off -v ON_ERROR_STOP=1 2>&1 <<'SQL'
BEGIN READ ONLY;
SET LOCAL statement_timeout = '20s';
\echo SCHEMA_BEGIN
SELECT table_name, column_name, udt_name,
       coalesce(character_maximum_length::text, '-'), is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
\echo COUNTS_BEGIN
SELECT string_agg(
  format('SELECT %L, count(*)::bigint FROM %I.%I',
         n.nspname || '.' || c.relname, n.nspname, c.relname),
  E'\nUNION ALL\n' ORDER BY c.relname
)
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p')
  AND NOT c.relispartition
\gexec
COMMIT;
SQL
  )"; then
    printf 'DB_BEGIN:%s\n%s\nDB_END:%s\n' "$label" "$result" "$label"
  else
    case "$result" in
      *"remaining connection slots"*|*"too many clients"*|*"too many connections"*)
        motivo=CONNECTION_LIMIT ;;
      *"password authentication failed"*|*"authentication failed"*)
        motivo=AUTH_FAILED ;;
      *"could not translate host name"*|*"Name or service not known"*)
        motivo=DNS ;;
      *"timeout expired"*|*"Connection timed out"*|*"Operation timed out"*|*"connection timeout"*)
        motivo=TIMEOUT ;;
      *"Connection refused"*|*"connection refused"*)
        motivo=CONNECTION_REFUSED ;;
      *"no pg_hba.conf entry"*)
        motivo=ACCESS_RULE ;;
      *"server closed the connection unexpectedly"*|*"server closed the connection"*)
        motivo=SERVER_CLOSED ;;
      *"permission denied"*)
        motivo=PERMISSION ;;
      *"SSL"*|*"ssl"*)
        motivo=TLS ;;
      *"does not exist"*)
        motivo=NOT_FOUND ;;
      *)
        motivo=UNKNOWN ;;
    esac
    printf 'DB_FAIL:%s:%s\n' "$label" "$motivo"
  fi
  unset PGPASSWORD
}
run_db AIVEN "$AIVEN_URL" "$AIVEN_USER" "$AIVEN_PASS"
run_db NEON "$NEON_URL" "$NEON_USER" "$NEON_PASS"
'''

made = False
try:
    rc, out = run(K + ['create', '-f', '-'], json.dumps(pod), 60)
    if rc:
        raise RuntimeError('Falha ao criar Pod temporario')
    made = True
    rc, out = run(K + ['wait', '-n', NS, '--for=condition=Ready',
                       'pod/' + name, '--timeout=120s'], timeout=135)
    if rc:
        raise RuntimeError('Pod temporario nao ficou Ready')
    rc, output = run(K + ['exec', '-i', '-n', NS, name, '--', 'sh'],
                     shell, timeout=170)
    if rc:
        raise RuntimeError('Falha ao executar psql no Pod')

    def parse(label):
        if 'DB_FAIL:' + label in output:
            return None
        start = 'DB_BEGIN:' + label + '\n'
        end = '\nDB_END:' + label
        if start not in output or end not in output:
            return None
        data = output.split(start, 1)[1].split(end, 1)[0]
        part = ''
        columns = {}
        counts = {}
        for line in data.splitlines():
            line = line.strip()
            if line == 'SCHEMA_BEGIN':
                part = 'columns'
            elif line == 'COUNTS_BEGIN':
                part = 'counts'
            elif part == 'columns' and line:
                f = line.split('|')
                if len(f) == 5:
                    columns[f[0] + '.' + f[1]] = tuple(f[2:])
            elif part == 'counts' and line:
                f = line.split('|')
                if len(f) == 2:
                    try:
                        counts[f[0]] = int(f[1])
                    except ValueError:
                        pass
        return {'counts': counts, 'columns': columns}

    aiven = parse('AIVEN')
    neon = parse('NEON')
    def motivo_falha(label):
        for linha in output.splitlines():
            prefixo = 'DB_FAIL:' + label + ':'
            if linha.startswith(prefixo):
                return linha[len(prefixo):].strip()
        return 'INDETERMINADA'

    print('AIVEN:', 'CONECTOU (leitura)' if aiven
          else 'FALHOU (' + motivo_falha('AIVEN') + ')')
    print('NEON:', 'CONECTOU (leitura)' if neon
          else 'FALHOU (' + motivo_falha('NEON') + ')')
    if aiven and neon:
        at, nt = aiven['counts'], neon['counts']
        ac, nc = aiven['columns'], neon['columns']
        print('Tabelas contadas: Aiven=%d | Neon=%d' % (len(at), len(nt)))
        missing = sorted(set(at) - set(nt))
        extra = sorted(set(nt) - set(at))
        print('Tabelas apenas no Aiven:', len(missing))
        print('Tabelas apenas no Neon:', len(extra))
        if missing:
            print('  Ausentes no Neon:', ', '.join(missing[:10]))
        if extra:
            print('  Extras no Neon:', ', '.join(extra[:10]))
        print('Colunas: Aiven=%d | Neon=%d' % (len(ac), len(nc)))
        col_diff = [c for c in sorted(set(ac) | set(nc)) if ac.get(c) != nc.get(c)]
        print('Diferencas de estrutura em colunas:', len(col_diff))
        for c in col_diff[:12]:
            print('  ESTRUTURA DIFERENTE:', c)
        if len(col_diff) > 12:
            print('  ... outras', len(col_diff) - 12, 'diferencas')
        diffs = [(t, at.get(t), nt.get(t)) for t in sorted(set(at) | set(nt))
                 if at.get(t) != nt.get(t)]
        print('Tabelas com contagens diferentes:', len(diffs))
        for t, av, ne in diffs[:15]:
            print('  %s: Aiven=%s Neon=%s' % (t, av, ne))
        if len(diffs) > 15:
            print('  ... outras', len(diffs) - 15, 'tabelas')
        print('ATENCAO: contagens iguais nao garantem dados identicos.')
    else:
        print('Comparacao de dados INCONCLUSIVA.')
except RuntimeError as e:
    print('ERRO no teste PostgreSQL:', str(e))
finally:
    if made:
        rc, out = run(K + ['delete', 'pod', name, '-n', NS,
                           '--ignore-not-found=true', '--wait=true', '--timeout=40s'], timeout=50)
        rc2, remaining = run(K + ['get', 'pod', name, '-n', NS,
                                  '--ignore-not-found=true', '-o', 'name'], timeout=30)
        print('Pod temporario:', 'REMOVIDO' if rc2 == 0 and not remaining.strip()
              else 'VERIFICAR REMOCAO')

print()
print('=== DECISAO ===')
print('PR #44: NAO MERGEAR AINDA (risco de corte parcial).')
print('PR #43: AGUARDAR VALIDACAO DA MOBILE NO NEON.')
print('Pendencias externas: confirmacao da equipe BD sobre dados,')
print('credencial exposta e janela de troca coordenada.')
