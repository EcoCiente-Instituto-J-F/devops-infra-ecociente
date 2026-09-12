#!/bin/bash

set -euo pipefail

K3S_VERSION="v1.36.4+k3s1"

echo "======================================"
echo " EcoCiente - Instalacao do k3s"
echo " Versao: ${K3S_VERSION}"
echo "======================================"

if command -v k3s >/dev/null 2>&1; then
    echo "k3s ja esta instalado."
    k3s --version
else
    echo "Instalando k3s..."

    curl -sfL https://get.k3s.io | \
        INSTALL_K3S_VERSION="${K3S_VERSION}" sh -
fi

echo "Habilitando servico k3s..."

sudo systemctl enable k3s
sudo systemctl start k3s

echo "Aguardando o cluster ficar disponivel..."

for tentativa in $(seq 1 30); do
    if sudo kubectl get nodes >/dev/null 2>&1; then
        break
    fi

    echo "Tentativa ${tentativa}/30..."
    sleep 2
done

echo
echo "Status do servico:"
sudo systemctl status k3s --no-pager

echo
echo "Nodes:"
sudo kubectl get nodes -o wide

echo
echo "Pods do sistema:"
sudo kubectl get pods -A

echo
echo "Instalacao e validacao concluidas."