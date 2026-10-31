#!/usr/bin/env bash
set -euo pipefail
umask 077

NS="ecociente"
DIR="$(mktemp -d)"
trap 'rm -rf "$DIR"' EXIT

if sudo k3s kubectl -n "$NS" get secret redis-auth >/dev/null 2>&1; then
  echo "redis-auth ja existe. Nao sera substituido."
else
  python3 - "$DIR" <<'PY'
import hashlib
import os
import secrets
import sys
from pathlib import Path
p = Path(sys.argv[1])
password = secrets.token_urlsafe(48)
(p / "password").write_text(password, encoding="utf-8")
digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
(p / "users.acl").write_text("user default on #" + digest + " ~* &* +@all\n", encoding="utf-8")
os.chmod(p / "password", 0o600)
os.chmod(p / "users.acl", 0o600)
PY

  sudo k3s kubectl -n "$NS" create secret generic redis-auth \
    --from-file=password="$DIR/password" \
    --from-file=users.acl="$DIR/users.acl" \
    --dry-run=client -o yaml | sudo k3s kubectl -n "$NS" create -f -
  echo "Secret redis-auth criado, senha nao exibida."
fi

sudo k3s kubectl -n "$NS" apply -f kubernetes/aws/platform/redis/redis.yaml
sudo k3s kubectl -n "$NS" rollout status statefulset/redis --timeout=240s
sudo k3s kubectl -n "$NS" get statefulset/redis pvc/data-redis-0 service/redis
echo "Redis implantado. Ainda validar autenticacao, persistencia e jobs antes de conectar APIs."
