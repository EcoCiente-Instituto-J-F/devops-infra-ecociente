#!/bin/bash
set -euo pipefail

APP_NAME="${1:-}"
IMAGE_TAG="${2:-}"

NAMESPACE="ecociente"
REPOSITORY_DIR="/home/ssm-user/devops-infra-ecociente"
CHART_DIR="${REPOSITORY_DIR}/kubernetes/aws/charts/ecociente-api"
KUBECONFIG_PATH="/etc/rancher/k3s/k3s.yaml"

MAX_PLATFORM_ATTEMPTS=60
PLATFORM_RETRY_SECONDS=5

if [ -z "${APP_NAME}" ]; then
    echo "Erro: informe o nome da aplicacao."
    echo "Uso: deploy-app.sh <app> [image-tag]"
    exit 1
fi

if ! [[ "${APP_NAME}" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
    echo "Erro: nome de aplicacao invalido: ${APP_NAME}"
    exit 1
fi

if [ -n "${IMAGE_TAG}" ] && \
   ! [[ "${IMAGE_TAG}" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]; then
    echo "Erro: tag de imagem invalida."
    exit 1
fi

VALUES_FILE="${REPOSITORY_DIR}/kubernetes/aws/apps/${APP_NAME}/values.yaml"

if [ ! -d "${REPOSITORY_DIR}/.git" ]; then
    echo "Erro: repositorio Git nao encontrado em ${REPOSITORY_DIR}."
    exit 1
fi

if [ ! -d "${CHART_DIR}" ]; then
    echo "Erro: Helm Chart nao encontrado:"
    echo "${CHART_DIR}"
    exit 1
fi

if [ ! -f "${VALUES_FILE}" ]; then
    echo "Erro: values.yaml nao encontrado:"
    echo "${VALUES_FILE}"
    exit 1
fi

for COMMAND in git helm kubectl; do
    if ! command -v "${COMMAND}" >/dev/null 2>&1; then
        echo "Erro: comando ${COMMAND} nao encontrado."
        exit 1
    fi
done

if ! sudo test -f "${KUBECONFIG_PATH}"; then
    echo "Erro: kubeconfig do k3s nao encontrado."
    exit 1
fi

KUBECTL=(
    sudo
    env
    "KUBECONFIG=${KUBECONFIG_PATH}"
    kubectl
)

HELM=(
    sudo
    env
    "KUBECONFIG=${KUBECONFIG_PATH}"
    helm
)

wait_for_platform() {
    echo
    echo "Aguardando infraestrutura Kubernetes..."

    for ATTEMPT in $(seq 1 "${MAX_PLATFORM_ATTEMPTS}"); do
        K3S_READY="false"
        API_READY="false"
        NODE_READY="false"
        FLANNEL_READY="false"
        COREDNS_READY="false"
        TRAEFIK_READY="false"

        if sudo systemctl is-active --quiet k3s; then
            K3S_READY="true"
        fi

        if [ "${K3S_READY}" = "true" ] && \
           "${KUBECTL[@]}" get nodes >/dev/null 2>&1; then
            API_READY="true"
        fi

        if [ "${API_READY}" = "true" ] && \
           "${KUBECTL[@]}" wait \
               --for=condition=Ready \
               node \
               --all \
               --timeout=1s >/dev/null 2>&1; then
            NODE_READY="true"
        fi

        if sudo test -f /run/flannel/subnet.env; then
            FLANNEL_READY="true"
        fi

        if [ "${API_READY}" = "true" ]; then
            COREDNS_AVAILABLE="$(
                "${KUBECTL[@]}" get deployment coredns \
                    -n kube-system \
                    -o jsonpath='{.status.availableReplicas}' \
                    2>/dev/null || true
            )"

            TRAEFIK_AVAILABLE="$(
                "${KUBECTL[@]}" get deployment traefik \
                    -n kube-system \
                    -o jsonpath='{.status.availableReplicas}' \
                    2>/dev/null || true
            )"

            if [ "${COREDNS_AVAILABLE:-0}" -ge 1 ] 2>/dev/null; then
                COREDNS_READY="true"
            fi

            if [ "${TRAEFIK_AVAILABLE:-0}" -ge 1 ] 2>/dev/null; then
                TRAEFIK_READY="true"
            fi
        fi

        echo "Tentativa ${ATTEMPT}/${MAX_PLATFORM_ATTEMPTS}:"
        echo "  k3s:      ${K3S_READY}"
        echo "  API:      ${API_READY}"
        echo "  Node:     ${NODE_READY}"
        echo "  Flannel:  ${FLANNEL_READY}"
        echo "  CoreDNS:  ${COREDNS_READY}"
        echo "  Traefik:  ${TRAEFIK_READY}"

        if [ "${K3S_READY}" = "true" ] && \
           [ "${API_READY}" = "true" ] && \
           [ "${NODE_READY}" = "true" ] && \
           [ "${FLANNEL_READY}" = "true" ] && \
           [ "${COREDNS_READY}" = "true" ] && \
           [ "${TRAEFIK_READY}" = "true" ]; then
            echo
            echo "Infraestrutura Kubernetes pronta."
            return 0
        fi

        sleep "${PLATFORM_RETRY_SECONDS}"
    done

    echo
    echo "Erro: infraestrutura Kubernetes nao ficou pronta dentro do tempo esperado."

    echo
    echo "Status do k3s:"
    sudo systemctl status k3s --no-pager || true

    echo
    echo "Estado dos nodes:"
    "${KUBECTL[@]}" get nodes -o wide || true

    echo
    echo "Pods do kube-system:"
    "${KUBECTL[@]}" get pods -n kube-system -o wide || true

    echo
    echo "Flannel:"
    if sudo test -f /run/flannel/subnet.env; then
        echo "/run/flannel/subnet.env encontrado."
    else
        echo "/run/flannel/subnet.env nao encontrado."
    fi

    exit 1
}

cd "${REPOSITORY_DIR}"

echo "======================================"
echo " EcoCiente - Continuous Deployment"
echo " Aplicacao: ${APP_NAME}"

if [ -n "${IMAGE_TAG}" ]; then
    echo " Imagem tag: ${IMAGE_TAG}"
else
    echo " Imagem tag: definida no values.yaml"
fi

echo " Namespace: ${NAMESPACE}"
echo "======================================"

echo
echo "[1/7] Validando plataforma Kubernetes..."

wait_for_platform

echo
echo "[2/7] Sincronizando repositorio..."

git fetch origin main
git checkout main
git reset --hard origin/main

if [ ! -f "${VALUES_FILE}" ]; then
    echo "Erro: values.yaml nao encontrado apos sincronizacao:"
    echo "${VALUES_FILE}"
    exit 1
fi

echo
echo "[3/7] Validando Helm Chart..."

helm lint \
    "${CHART_DIR}" \
    -f "${VALUES_FILE}"

HELM_ARGS=(
    upgrade
    --install
    "${APP_NAME}"
    "${CHART_DIR}"
    -f "${VALUES_FILE}"
    --namespace "${NAMESPACE}"
    --rollback-on-failure
    --timeout 5m
)

if [ -n "${IMAGE_TAG}" ]; then
    HELM_ARGS+=(
        --set-string "image.tag=${IMAGE_TAG}"
    )
fi

echo
echo "[4/7] Executando Helm deployment..."

"${HELM[@]}" "${HELM_ARGS[@]}"

echo
echo "[5/7] Localizando Deployment..."

DEPLOYMENT_NAME="$(
    "${KUBECTL[@]}" get deployment \
        -n "${NAMESPACE}" \
        -l "app.kubernetes.io/instance=${APP_NAME}" \
        -o jsonpath='{.items[0].metadata.name}'
)"

if [ -z "${DEPLOYMENT_NAME}" ]; then
    echo "Erro: nenhum Deployment encontrado para a release ${APP_NAME}."
    exit 1
fi

echo "Deployment encontrado: ${DEPLOYMENT_NAME}"

echo
echo "[6/7] Validando rollout..."

"${KUBECTL[@]}" rollout status \
    "deployment/${DEPLOYMENT_NAME}" \
    -n "${NAMESPACE}" \
    --timeout=240s

echo
echo "Estado do Deployment:"

"${KUBECTL[@]}" get deployment "${DEPLOYMENT_NAME}" \
    -n "${NAMESPACE}"

echo
echo "Pods da release:"

"${KUBECTL[@]}" get pods \
    -n "${NAMESPACE}" \
    -l "app=${DEPLOYMENT_NAME}" \
    -o wide

echo
echo "[7/7] Historico Helm:"

"${HELM[@]}" history "${APP_NAME}" \
    -n "${NAMESPACE}"

echo
echo "======================================"
echo " Deploy concluido com sucesso"
echo " Aplicacao: ${APP_NAME}"
echo " Deployment: ${DEPLOYMENT_NAME}"
echo "======================================"