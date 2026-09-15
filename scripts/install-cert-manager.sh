#!/bin/bash

set -euo pipefail

CERT_MANAGER_VERSION="v1.21.2"
KUBECONFIG_PATH="/etc/rancher/k3s/k3s.yaml"

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

echo "======================================"
echo " EcoCiente - Instalacao cert-manager"
echo " Versao: ${CERT_MANAGER_VERSION}"
echo "======================================"

for COMMAND in helm kubectl; do
    if ! command -v "${COMMAND}" >/dev/null 2>&1; then
        echo "Erro: comando ${COMMAND} nao encontrado."
        exit 1
    fi
done

if ! sudo test -f "${KUBECONFIG_PATH}"; then
    echo "Erro: kubeconfig do k3s nao encontrado."
    exit 1
fi

echo
echo "[1/4] Validando cluster..."

"${KUBECTL[@]}" wait \
    --for=condition=Ready \
    node \
    --all \
    --timeout=120s

echo
echo "[2/4] Instalando ou atualizando cert-manager..."

"${HELM[@]}" upgrade \
    --install \
    cert-manager \
    oci://quay.io/jetstack/charts/cert-manager \
    --version "${CERT_MANAGER_VERSION}" \
    --namespace cert-manager \
    --create-namespace \
    --set crds.enabled=true \
    --wait \
    --timeout 5m

echo
echo "[3/4] Validando deployments..."

"${KUBECTL[@]}" wait \
    --for=condition=Available \
    deployment/cert-manager \
    -n cert-manager \
    --timeout=180s

"${KUBECTL[@]}" wait \
    --for=condition=Available \
    deployment/cert-manager-cainjector \
    -n cert-manager \
    --timeout=180s

"${KUBECTL[@]}" wait \
    --for=condition=Available \
    deployment/cert-manager-webhook \
    -n cert-manager \
    --timeout=180s

echo
echo "[4/4] Estado final..."

"${KUBECTL[@]}" get pods \
    -n cert-manager \
    -o wide

echo
echo "======================================"
echo " cert-manager pronto"
echo "======================================"
