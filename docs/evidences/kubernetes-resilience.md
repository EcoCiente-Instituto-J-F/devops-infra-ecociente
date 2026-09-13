\# Evidencia de Resiliencia Kubernetes - EcoCiente



\## Objetivo



Este documento registra os testes praticos de resiliencia executados no cluster Kubernetes do EcoCiente hospedado em uma instancia EC2 na AWS utilizando k3s.



Os testes realizados foram:



\- Self-Healing de Pods

\- Scaling horizontal manual

\- Atualizacao automatica de endpoints do Service

\- Validacao da aplicacao apos recuperacao

\- Retorno ao estado original



Aplicacao utilizada:



```text

ds-calendario-api

```



Helm release:



```text

calendario

```



Deployment:



```text

calendario-api

```



Namespace:



```text

ecociente

```



Porta:



```text

9800

```



\---



\# 1. Estado inicial



Antes dos testes, a release Helm da aplicacao estava implantada com sucesso.



```text

NAME: calendario

REVISION: 1

STATUS: deployed

DESCRIPTION: Install complete

```



O Deployment estava:



```text

READY: 1/1

UP-TO-DATE: 1

AVAILABLE: 1

```



O Pod estava:



```text

READY: 1/1

STATUS: Running

RESTARTS: 0

```



O Service:



```text

calendario-api-service

Type: ClusterIP

Port: 9800

```



possui um EndpointSlice conectado ao Pod da aplicacao.



\---



\# 2. Validacao funcional antes dos testes



Antes da simulacao de falha foram executados testes HTTP internos.



Swagger:



```text

HTTP 200

```



OpenAPI:



```text

HTTP 200

```



A rota raiz respondeu:



```text

HTTP 403

```



Esse comportamento corresponde a uma resposta da camada de seguranca da aplicacao e confirma que o servidor HTTP estava acessivel.



\---



\# 3. Teste de Self-Healing



\## 3.1 Pod original



Antes da exclusao proposital:



```text

POD\_ANTIGO=calendario-api-77d5d7fb7-gk5x8

```



O Pod foi removido manualmente para simular uma falha:



```bash

kubectl delete pod calendario-api-77d5d7fb7-gk5x8 -n ecociente

```



Resultado:



```text

pod "calendario-api-77d5d7fb7-gk5x8" deleted

```



\---



\## 3.2 Recuperacao automatica



O Kubernetes identificou que o numero de replicas estava abaixo do estado desejado definido pelo Deployment.



Um novo Pod foi criado automaticamente:



```text

POD\_NOVO=calendario-api-77d5d7fb7-cdf25

```



Depois da inicializacao:



```text

READY: 1/1

STATUS: Running

RESTARTS: 0

```



O Deployment voltou automaticamente para:



```text

READY: 1/1

UP-TO-DATE: 1

AVAILABLE: 1

```



\---



\# 4. Atualizacao automatica do Service



Antes da exclusao, o EndpointSlice apontava para:



```text

10.42.0.77:9800

```



Depois da recriacao do Pod, o Kubernetes atualizou automaticamente o endpoint para:



```text

10.42.0.78:9800

```



Nao foi necessaria nenhuma alteracao manual no Service.



Fluxo observado:



```text

Pod antigo removido

&#x20;       |

&#x20;       v

Deployment detecta replica ausente

&#x20;       |

&#x20;       v

ReplicaSet cria novo Pod

&#x20;       |

&#x20;       v

Novo Pod fica Ready

&#x20;       |

&#x20;       v

EndpointSlice e atualizado

&#x20;       |

&#x20;       v

Service passa a direcionar para o novo Pod

```



\---



\# 5. Aplicacao apos Self-Healing



Depois da recuperacao automatica, os endpoints foram testados novamente.



Swagger:



```text

HTTP 200

```



OpenAPI:



```text

HTTP 200

```



Isso demonstra que a aplicacao voltou a responder normalmente sem intervencao manual na infraestrutura.



\---



\# 6. Resultado do Self-Healing



O teste demonstrou:



```text

Falha simulada

&#x20;       |

&#x20;       v

Pod removido

&#x20;       |

&#x20;       v

Kubernetes detecta divergencia

&#x20;       |

&#x20;       v

Novo Pod criado automaticamente

&#x20;       |

&#x20;       v

Readiness Probe aprovada

&#x20;       |

&#x20;       v

Service atualizado

&#x20;       |

&#x20;       v

API novamente disponivel

```



Resultado:



```text

SELF-HEALING: SUCESSO

```



\---



\# 7. Teste de Scaling Horizontal



Depois do teste de Self-Healing, o Deployment foi escalado manualmente de:



```text

1 replica

```



para:



```text

2 replicas

```



Comando utilizado:



```bash

kubectl scale deployment/calendario-api \\

&#x20; -n ecociente \\

&#x20; --replicas=2

```



\---



\# 8. Resultado do Scaling



O Kubernetes criou uma segunda replica e o Deployment atingiu:



```text

READY: 2/2

UP-TO-DATE: 2

AVAILABLE: 2

```



Os Pods ativos eram:



```text

calendario-api-77d5d7fb7-cdf25

calendario-api-77d5d7fb7-znkzb

```



Ambos:



```text

READY: 1/1

STATUS: Running

RESTARTS: 0

```



\---



\# 9. Service com multiplos endpoints



Com duas replicas ativas, o EndpointSlice passou a possuir:



```text

10.42.0.78

10.42.0.79

```



ambos na porta:



```text

9800

```



Fluxo:



```text

&#x20;                   +--> Pod 1 - 10.42.0.78

Service ClusterIP --|

&#x20;                   +--> Pod 2 - 10.42.0.79

```



Isso demonstra que o Service Kubernetes acompanha dinamicamente as replicas disponiveis.



\---



\# 10. Validacao da aplicacao durante o Scaling



Com duas replicas ativas, o Swagger permaneceu disponivel.



Resultado:



```text

SWAGGER\_STATUS=200

```



Isso demonstra que o aumento do numero de replicas nao interrompeu o acesso a aplicacao.



\---



\# 11. Retorno para uma replica



Depois do teste, o Deployment foi restaurado para o estado original:



```bash

kubectl scale deployment/calendario-api \\

&#x20; -n ecociente \\

&#x20; --replicas=1

```



O rollout foi concluido com sucesso:



```text

deployment "calendario-api" successfully rolled out

```



Estado final:



```text

READY: 1/1

UP-TO-DATE: 1

AVAILABLE: 1

```



Pod final:



```text

calendario-api-77d5d7fb7-cdf25

READY: 1/1

STATUS: Running

```



\---



\# 12. Resultado do Scaling



O teste demonstrou:



```text

1 replica

&#x20;  |

&#x20;  v

scale --replicas=2

&#x20;  |

&#x20;  v

2 Pods criados

&#x20;  |

&#x20;  v

Service recebe 2 endpoints

&#x20;  |

&#x20;  v

Aplicacao permanece acessivel

&#x20;  |

&#x20;  v

scale --replicas=1

&#x20;  |

&#x20;  v

Estado original restaurado

```



Resultado:



```text

SCALING HORIZONTAL: SUCESSO

```



\---



\# 13. Recursos Kubernetes validados



Durante os testes foram validados:



```text

Deployment

ReplicaSet

Pods

Service

EndpointSlice

Startup Probe

Readiness Probe

Liveness Probe

```



\---



\# 14. Resultado geral



Os testes praticos comprovaram:



```text

Self-Healing              OK

Scaling Horizontal        OK

Service Discovery         OK

Atualizacao de Endpoints  OK

Readiness                 OK

Recuperacao automatica    OK

Aplicacao apos falha      OK

Retorno a 1 replica       OK

```



\---



\# 15. Arquitetura validada



```text

AWS EC2

&#x20;  |

&#x20;  v

k3s

&#x20;  |

&#x20;  +-- Deployment

&#x20;  |      |

&#x20;  |      +-- Pod 1

&#x20;  |      |

&#x20;  |      +-- Pod 2

&#x20;  |

&#x20;  +-- Service

&#x20;         |

&#x20;         +-- EndpointSlice

```



O estado desejado e controlado pelo Kubernetes.



Quando um Pod e removido, o Deployment cria automaticamente uma nova replica.



Quando o numero de replicas aumenta, o Service passa automaticamente a reconhecer os novos endpoints.



\---



\# 16. Conclusao



A infraestrutura do EcoCiente demonstrou capacidade de:



```text

detectar falhas de Pod

recuperar automaticamente workloads

escalar horizontalmente uma API

atualizar endpoints de Service

manter a aplicacao disponivel

retornar ao estado original

```



Esses testes complementam as evidencias ja existentes de:



```text

Containerizacao Docker

Kubernetes

Helm

Rolling Update

Rollback

Continuous Deployment

AWS

```



e comprovam na pratica mecanismos fundamentais de resiliencia e orquestracao do Kubernetes.

