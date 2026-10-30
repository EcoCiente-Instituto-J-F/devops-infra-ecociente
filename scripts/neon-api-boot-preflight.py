#!/usr/bin/env python3
"""Testa boot das quatro APIs com Neon em Pods isolados e descartaveis.

Nao atualiza Deployments, Services, Ingress, Secrets, Helm ou dados.
Nao executa chamadas de escrita; consulta somente a documentacao HTTP.
Nao imprime logs crus nem valores de credenciais.
"""
import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import uuid

NS = "ecociente"
K = ["sudo", "env", "KUBECONFIG=/etc/rancher/k3s/k3s.yaml", "kubectl"]
APPS = (
    ("autenticacao", "/v3/api-docs"),
    ("cadastro", "/api-docs"),
    ("calendario", "/v3/api-docs"),
    ("mobile", "/api-docs"),
)
TEST_MOBILE_IMAGE = "ecociente/ecociente:mobile-1.0.2"
READY_TIMEOUT_SECONDS = 160


def call(args, input_data=None, timeout=40):
    try:
        return subprocess.run(
            args, input=input_data, text=True, capture_output=True,
            timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def kubectl_json(args):
    p = call(K + args)
    if p is None or p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def environmental_overrides(container):
    forced = {
        "SPRING_JPA_HIBERNATE_DDL_AUTO": "validate",
        "SPRING_SQL_INIT_MODE": "never",
        "SPRING_FLYWAY_ENABLED": "false",
        "SPRING_LIQUIBASE_ENABLED": "false",
        "SPRING_MAIN_LAZY_INITIALIZATION": "false",
        "SPRING_DATASOURCE_HIKARI_READ_ONLY": "true",
        "SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE": "1",
        "SPRING_DATASOURCE_HIKARI_MINIMUM_IDLE": "0",
        "SPRING_DATASOURCE_HIKARI_CONNECTION_TIMEOUT": "12000",
    }
    existing = [
        item for item in container.get("env", [])
        if item["name"] not in forced
    ]
    return existing + [
        {"name": key, "value": value}
        for key, value in forced.items()
    ]


def create_audit_pod(app, deployment):
    spec = deployment["spec"]["template"]["spec"]
    if len(spec["containers"]) != 1:
        raise RuntimeError("Deployment com mais de um container")
    original = spec["containers"][0]
    if not original.get("ports"):
        raise RuntimeError("Porta do container nao identificada")
    port = original["ports"][0]["containerPort"]

    # Preserva ConfigMaps, mas substitui SOMENTE a referencia ao Secret.
    envfrom = []
    replaced = 0
    for ref in original.get("envFrom", []):
        if "configMapRef" in ref:
            envfrom.append(ref)
        elif ref.get("secretRef", {}).get("name") == app + "-secret":
            newref = {"secretRef": {"name": app + "-neon-secret"}}
            envfrom.append(newref)
            replaced += 1
        else:
            raise RuntimeError("Referencia envFrom inesperada")

    if replaced != 1:
        raise RuntimeError("Referencia do Secret original nao encontrada")

    name = "neon-boot-" + app + "-" + uuid.uuid4().hex[:8]
    image = TEST_MOBILE_IMAGE if app == "mobile" else original["image"]
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name, "namespace": NS,
            "labels": {"ecociente-audit": "neon-boot-preflight"}
        },
        "spec": {
            "automountServiceAccountToken": False,
            "restartPolicy": "Never",
            "activeDeadlineSeconds": 330,
            "containers": [{
                "name": "app",
                "image": image,
                "imagePullPolicy": "IfNotPresent",
                "ports": [{"name": "http", "containerPort": port}],
                "envFrom": envfrom,
                "env": environmental_overrides(original),
                "readinessProbe": {
                    "tcpSocket": {"port": port},
                    "periodSeconds": 3,
                    "timeoutSeconds": 2,
                    "failureThreshold": 5,
                },
                "resources": {
                    "requests": {"cpu": "100m", "memory": "256Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"},
                },
            }]
        },
    }
    return name, port, image, pod


def pod_status(name):
    data = kubectl_json(["get", "pod", name, "-n", NS, "-o", "json"])
    if not data:
        return "NOT_FOUND", "NOT_FOUND"
    phase = data.get("status", {}).get("phase", "?")
    conditions = data.get("status", {}).get("conditions", [])
    if any(c.get("type") == "Ready" and c.get("status") == "True"
           for c in conditions):
        return "READY", "READY"
    for cs in data.get("status", {}).get("containerStatuses", []):
        state = cs.get("state", {})
        if "terminated" in state:
            return "FAILED", state["terminated"].get("reason", "EXIT")
        if "waiting" in state:
            reason = state["waiting"].get("reason", "")
            if reason in ("ImagePullBackOff", "InvalidImageName",
                          "CreateContainerConfigError",
                          "CreateContainerError"):
                return "FAILED", reason
    return "WAITING", phase


def wait_until_ready(name):
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    reason = "TIMEOUT"
    while time.monotonic() < deadline:
        state, reason = pod_status(name)
        if state == "READY":
            return True, reason
        if state == "FAILED":
            return False, reason
        time.sleep(4)
    return False, "TIMEOUT"


def safe_log_checks(name):
    result = call(K + [
        "logs", "pod/" + name, "-n", NS, "--tail=600"
    ], timeout=30)
    if result is None or result.returncode != 0:
        return "NAO DISPONIVEL", "INDETERMINADO", "NAO CONFIRMADO"
    logs = result.stdout
    jpa = bool(re.search(
        r"(Initialized JPA EntityManagerFactory|"
        r"Initialized JPA EntityManagerFactory for persistence unit)",
        logs, re.IGNORECASE))
    pool = bool(re.search(
        r"HikariPool-\d+.*Start completed", logs, re.IGNORECASE))
    spring = bool(re.search(
        r"Started [A-Za-z][A-Za-z0-9]*Application in ",
        logs, re.IGNORECASE))
    causes = [
        ("SCHEMA", r"Schema-validation:|missing table|wrong column type"),
        ("AUTENTICACAO_DB", r"password authentication failed|SQLState: 28P01"),
        ("SEM_CONEXAO_DB", r"too many clients|remaining connection slots|"
         r"Connection is not available|Connection refused|"
         r"Failed to obtain JDBC Connection|Unable to open JDBC Connection"),
        ("CONFIGURACAO", r"Failed to configure a DataSource|"
         r"Could not resolve placeholder"),
        ("JAVA_MEMORIA", r"OutOfMemoryError|Java heap space"),
        ("INICIALIZACAO", r"Application run failed|"
         r"APPLICATION FAILED TO START"),
    ]
    issues = [title for title, pattern in causes
              if re.search(pattern, logs, re.IGNORECASE)]
    app = "SIM" if spring else "NAO CONFIRMADO"
    db = "SIM" if (jpa and pool) else (
        "PARCIAL" if (jpa or pool) else "NAO CONFIRMADO"
    )
    issue = ",".join(issues) if issues else "NENHUM IDENTIFICADO"
    return app, issue, db


def check_http_docs(name, port, path):
    # O port-forward existe apenas na loopback da propria EC2.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        local_port = sock.getsockname()[1]
    pf = subprocess.Popen(
        K + [
            "port-forward", "-n", NS, "pod/" + name,
            str(local_port) + ":" + str(port),
            "--address", "127.0.0.1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        available = False
        while time.monotonic() < deadline:
            if pf.poll() is not None:
                break
            try:
                with socket.create_connection(
                    ("127.0.0.1", local_port), timeout=1
                ):
                    available = True
                    break
            except OSError:
                time.sleep(0.5)
        if not available:
            return "FALHA_PORT_FORWARD"

        req = urllib.request.Request(
            "http://127.0.0.1:" + str(local_port) + path,
            headers={"Accept": "application/json"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(req, timeout=18) as response:
                return "HTTP_" + str(response.status)
        except urllib.error.HTTPError as ex:
            return "HTTP_" + str(ex.code)
        except (urllib.error.URLError, TimeoutError, OSError):
            return "FALHA_HTTP"
    finally:
        if pf.poll() is None:
            pf.terminate()
            try:
                pf.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pf.kill()
                pf.wait(timeout=5)


def delete_pod(name):
    call(K + [
        "delete", "pod", name, "-n", NS,
        "--ignore-not-found=true", "--wait=true", "--timeout=45s"
    ], timeout=55)
    remaining = call(K + [
        "get", "pod", name, "-n", NS, "-o", "name",
        "--ignore-not-found=true"
    ], timeout=20)
    return bool(remaining and remaining.returncode == 0
                and not remaining.stdout.strip())


def main():
    print("=== ECOCIENTE | TESTE DE BOOT DAS 4 APIS NO NEON ===", flush=True)
    print("ISOLADO: sem Services, sem Ingress, sem deploy e sem escrita HTTP.")
    print("Um Pod temporario por vez; limpeza ao finalizar cada teste.")
    print("Os logs de aplicacao nao serao exibidos.", flush=True)

    deps = kubectl_json(["get", "deployments", "-n", NS, "-o", "json"])
    if not deps:
        print("FALHA: nao foi possivel consultar Deployments")
        return 1
    indexed = {x["metadata"]["name"]: x for x in deps["items"]}
    results = {}
    for app, path in APPS:
        name = None
        print("\n[%s] Preparando teste..." % app.upper(), flush=True)
        try:
            deployment = indexed.get(app + "-api")
            if not deployment:
                raise RuntimeError("Deployment original ausente")
            if deployment.get("status", {}).get("readyReplicas", 0) < 1:
                raise RuntimeError("Deployment original nao esta Ready")
            secret = kubectl_json([
                "get", "secret", app + "-neon-secret",
                "-n", NS, "-o", "json"
            ])
            if not secret:
                raise RuntimeError("Secret Neon nao encontrado")
            name, port, image, pod = create_audit_pod(app, deployment)
            print("Imagem:", image, "| Porta:", port, flush=True)
            created = call(K + ["create", "-f", "-"],
                           json.dumps(pod), timeout=30)
            if created is None or created.returncode != 0:
                raise RuntimeError("Falha na criacao do Pod de teste")
            print("Pod temporario criado. Validando inicializacao...",
                  flush=True)
            ready, reason = wait_until_ready(name)
            app_start, issue, db = safe_log_checks(name)
            http = check_http_docs(name, port, path) if ready else "NAO_TESTADO"
            ok = ready and http == "HTTP_200" and db == "SIM" and issue == "NENHUM IDENTIFICADO"
            results[app] = ok
            print(
                "RESULTADO %s: %s | pod=%s | docs=%s | "
                "Spring=%s | JDBC+JPA=%s | alerta=%s"
                % (app, "APROVADO" if ok else "REVISAR",
                   "READY" if ready else reason, http, app_start, db, issue),
                flush=True
            )
        except (ValueError, TypeError, KeyError, RuntimeError) as error:
            results[app] = False
            print("RESULTADO %s: REVISAR (%s)" % (app, str(error)),
                  flush=True)
        finally:
            if name:
                print("Pod temporario:", "REMOVIDO" if delete_pod(name)
                      else "VERIFICAR REMOCAO", flush=True)

    passed = sum(1 for value in results.values() if value)
    print("\n=== RESUMO FINAL ===")
    for app, _ in APPS:
        print(app + ":", "APROVADO" if results.get(app)
              else "REVISAR", flush=True)
    print("APROVADOS: %d/4" % passed)
    print("Nenhum Deployment ou Secret foi alterado.")
    print("Ainda falta validar dados, credencial final e plano de corte.")
    print("PR #44 E PR #43: NAO MERGEAR AINDA.")
    return 0 if passed == 4 else 2


if __name__ == "__main__":
    raise SystemExit(main())
