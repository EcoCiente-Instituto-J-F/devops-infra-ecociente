#!/usr/bin/env python3
"""Auditoria somente de leitura das chaves de Secrets para migracao Neon.

Nunca exibe, decodifica, modifica ou grava valores de credenciais.
"""
import json
import subprocess
import sys

NAMESPACE = "ecociente"
K = ["sudo", "k3s", "kubectl", "-n", NAMESPACE]
NOMES = [
    "autenticacao-neon-secret",
    "cadastro-neon-secret",
    "calendario-neon-secret",
    "mobile-neon-secret",
    "mobile-secret",
    "esqueceusenha-secret",
    "pontuacao-secret",
    "esqueceusenha-neon-secret",
    "pontuacao-neon-secret",
    "ia-eko-secret",
]
CAMPOS = {
    "esqueceusenha-neon-secret": [
        "DB_URL", "DB_USER", "DB_PASSWORD", "JWT_SECRET",
        "FIREBASE_CREDENCIAIS", "URL_REDEFINICAO_SENHA",
        "MAIL_FROM", "MAIL_HOST", "MAIL_USERNAME", "MAIL_PASSWORD",
    ],
    "pontuacao-neon-secret": [
        "DB_URL", "DB_USER", "DB_PASSWORD", "JWT_SECRET",
        "REDIS_HOST", "REDIS_PORT", "REDIS_USERNAME",
        "REDIS_PASSWORD", "RANKING_CYCLE_EPOCH",
    ],
}
FONTE_BANCO = "autenticacao-neon-secret"
CHAVES_BANCO = {"DB_URL", "DB_USER", "DB_PASSWORD", "JWT_SECRET"}

def ler(nome):
    processo = subprocess.run(
        K + ["get", "secret", nome, "-o", "json"],
        text=True, capture_output=True, check=False, timeout=20,
    )
    if processo.returncode:
        if "NotFound" in processo.stderr or "not found" in processo.stderr.lower():
            return None
        print("ERRO ao consultar o Secret:", nome, file=sys.stderr)
        sys.exit(2)
    try:
        return set(json.loads(processo.stdout).get("data", {}).keys())
    except (ValueError, KeyError):
        print("ERRO ao interpretar as chaves do Secret:", nome, file=sys.stderr)
        sys.exit(2)

def main():
    print("ECOCIENTE - AUDITORIA DE SECRETS (SOMENTE LEITURA)")
    print("Namespace:", NAMESPACE)
    encontrados = {nome: ler(nome) for nome in NOMES}
    for nome in NOMES:
        chaves = encontrados[nome]
        print("\n" + nome + ":")
        print("  AUSENTE" if chaves is None else
              "  Chaves: " + (", ".join(sorted(chaves)) if chaves else "(nenhuma)"))

    fonte = encontrados[FONTE_BANCO]
    print("\nBASE NEON/JWT:")
    if fonte is None or not CHAVES_BANCO <= fonte:
        print("  NAO PRONTA: autenticacao-neon-secret incompleto")
    else:
        print("  PRONTA: quatro chaves presentes, sem verificar valores")

    for destino, campos in CAMPOS.items():
        presentes = encontrados[destino] or set()
        faltantes = [chave for chave in campos if chave not in presentes]
        print("\n" + destino + ":")
        if encontrados[destino] is None:
            print("  STATUS: NAO CRIADO")
        elif not faltantes:
            print("  STATUS: CHAVES PRESENTES (valores e conectividade nao testados)")
        else:
            print("  STATUS: INCOMPLETO")
        print("  CAMPOS FALTANTES:", ", ".join(faltantes) if faltantes else "nenhum")
        for chave in faltantes:
            if chave in CHAVES_BANCO:
                continue
            origens = [
                nome for nome in
                ("mobile-secret", "esqueceusenha-secret", "pontuacao-secret")
                if chave in (encontrados[nome] or set())
            ]
            print("  ORIGEM CANDIDATA", chave + ":", ", ".join(origens) if origens else "NAO ENCONTRADA")

    print("\nNenhum Secret ou Deployment foi alterado.")

if __name__ == "__main__":
    main()
