#!/bin/bash
set -euo pipefail

APP_NAME="${1:-}"
IMAGE_TAG="${2:-}"

NAMESPACE="ecociente"
REPOSITORY_DIR="/home/ssm-user/devops-infra-ecociente"
CHART_DIR="${REPOSITORY_DIR}/kubernetes/aws/charts/ecociente-api"
KUBECONFIG_PATH="/etc/rancher/k3s/k3s.yaml"

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
echo "[1/6] Sincronizando repositorio..."

git fetch origin main
git checkout main
git reset --hard origin/main

echo
echo "[2/6] Validando Helm Chart..."

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
echo "[3/6] Executando Helm deployment..."

sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
    helm "${HELM_ARGS[@]}"

echo
echo "[4/6] Localizando Deployment..."

DEPLOYMENT_NAME="$(
    sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
        kubectl get deployment \
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
echo "[5/6] Validando rollout..."

sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
    kubectl rollout status \
    "deployment/${DEPLOYMENT_NAME}" \
    -n "${NAMESPACE}" \
    --timeout=240s

echo
echo "Estado do Deployment:"

sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
    kubectl get deployment "${DEPLOYMENT_NAME}" \
    -n "${NAMESPACE}"

echo
echo "Pods da release:"

sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
    kubectl get pods \
    -n "${NAMESPACE}" \
    -l "app=${DEPLOYMENT_NAME}" \
    -o wide

echo
echo "[6/6] Historico Helm:"

sudo env KUBECONFIG="${KUBECONFIG_PATH}" \
    helm history "${APP_NAME}" \
    -n "${NAMESPACE}"

echo
echo "======================================"
echo " Deploy concluido com sucesso"
echo " Aplicacao: ${APP_NAME}"
echo " Deployment: ${DEPLOYMENT_NAME}"
echo "======================================"