\# 14. Medições reais do ambiente



As medições foram realizadas com os quatro workloads permanentes ativos no cluster:



```text

autenticacao-api

cadastro-api

calendario-api

ia-eko

```



Durante a coleta foram observados dois estados diferentes:



1\. cold start da infraestrutura;

2\. regime estabilizado após a inicialização das aplicações.



Essa distinção é importante porque as APIs Java apresentam consumo elevado de CPU durante a inicialização do Spring Boot, mas esse consumo cai significativamente após o startup.



\---



\## 14.1 Estado dos Deployments



Após a estabilização do ambiente:



```text

NAME               READY   UP-TO-DATE   AVAILABLE

autenticacao-api   1/1     1            1

cadastro-api       1/1     1            1

calendario-api     1/1     1            1

ia-eko             1/1     1            1

```



Todos os quatro workloads ficaram disponíveis.



Resultado:



```text

4/4 Deployments disponíveis

```



\---



\## 14.2 Estado dos Pods



Após a estabilização:



```text

autenticacao-api   1/1   Running

cadastro-api       1/1   Running

calendario-api     1/1   Running

ia-eko             1/1   Running

```



Todos os containers ficaram `Ready`.



Os contadores de restart observados foram influenciados pelos ciclos de desligamento e inicialização da instância EC2 realizados durante os testes.



Os containers Java apresentaram anteriormente `Exit Code 143`, compatível com encerramento através de `SIGTERM` durante os ciclos de parada da infraestrutura.



Não foi identificado `OutOfMemoryKilled`.



\---



\## 14.3 Cold start



Logo após a inicialização da EC2, os quatro containers foram iniciados praticamente ao mesmo tempo.



Nesse momento foi registrada a seguinte utilização do node:



```text

CPU:     1515m

CPU:     75%



Memória: 1702Mi

Memória: 21%

```



Utilização dos Pods durante esse período:



```text

Autenticação   495m CPU

Cadastro       494m CPU

Calendário     497m CPU

IA Eko           2m CPU

```



As três aplicações Java estavam próximas do limite individual configurado de:



```text

500m

```



Durante esse período, os Pods Java ainda estavam temporariamente:



```text

0/1

```



Os eventos Kubernetes registraram falhas temporárias nas startup probes enquanto as aplicações ainda não haviam aberto suas respectivas portas.



Os logs mostraram posteriormente a conclusão normal da inicialização das aplicações.



Tempos aproximados de startup observados:



```text

Autenticação: aproximadamente 62 segundos

Cadastro:     aproximadamente 56 segundos

Calendário:   aproximadamente 52 segundos

```



Após o startup, os três serviços passaram para:



```text

1/1 Ready

```



Portanto, o consumo de aproximadamente 75% de CPU representa um pico de inicialização e não o consumo normal das aplicações em regime estabilizado.



\---



\## 14.4 CPU do node em regime estabilizado



Após aguardar a inicialização completa dos workloads, uma nova medição apresentou:



```text

CPU: 83m

Uso: 4%

```



Para reduzir o impacto de uma medição isolada, foram realizadas três amostras adicionais com intervalo de aproximadamente 20 segundos.



\### Amostra 1



```text

CPU: 137m

Uso: 6%

```



\### Amostra 2



```text

CPU: 127m

Uso: 6%

```



\### Amostra 3



```text

CPU: 123m

Uso: 6%

```



Média das três amostras:



```text

(137m + 127m + 123m) / 3

= 129m

```



Portanto, o consumo observado do node em regime estabilizado foi de aproximadamente:



```text

129m CPU

\~6% da capacidade

```



em uma EC2 com 2 vCPU.



A diferença entre cold start e regime estabilizado foi significativa:



```text

Cold start:       \~1515m / 75%

Regime estável:   \~129m / 6%

```



\---



\## 14.5 CPU dos Pods em regime estabilizado



Nas três amostras os quatro workloads apresentaram aproximadamente:



```text

Autenticação   2m

Cadastro       2m

Calendário     2m

IA Eko         2m

```



Total aproximado das aplicações:



```text

8m CPU

```



O restante da utilização do node é relacionado ao sistema operacional e aos componentes da plataforma, incluindo:



\- k3s;

\- Kubernetes API;

\- container runtime;

\- Traefik;

\- CoreDNS;

\- metrics-server;

\- demais componentes internos.



Os valores representam um período sem carga significativa de usuários e não devem ser interpretados como benchmark de produção.



\---



\## 14.6 Memória dos Pods



Em regime estabilizado foram observados:



| Aplicação | Memória observada |

|---|---:|

| Autenticação | 272Mi |

| Cadastro | 256Mi |

| Calendário | 238Mi |

| IA Eko | 146Mi |

| \*\*Total\*\* | \*\*912Mi\*\* |



Os requests agregados configurados são:



```text

1280Mi

```



O consumo observado dos quatro Pods foi:



```text

912Mi

```



Isso corresponde a aproximadamente:



```text

71% dos requests agregados

```



Os limits agregados são:



```text

2560Mi

```



Portanto, o consumo observado permaneceu significativamente abaixo do limite total configurado.



A API de Autenticação apresentou consumo ligeiramente superior ao seu request individual de `256Mi`, utilizando aproximadamente `272Mi`.



Isso não representa falha, pois o request não é um limite máximo.



Seu limit é:



```text

512Mi

```



\---



\## 14.7 Memória do node



O `metrics-server` registrou aproximadamente:



```text

1919Mi a 1938Mi

24%

```



nas medições estabilizadas.



Média aproximada das três amostras principais:



```text

1932Mi

```



O sistema operacional apresentou através do `free -h`:



```text

Total:       7.6Gi

Usada:       1.6Gi

Livre:       4.9Gi

Cache:       1.1Gi

Disponível:  5.8Gi

Swap:        0

```



Isso indica uma margem confortável de memória para o ambiente atual.



\---



\## 14.8 Disco da EC2



O filesystem raiz apresentou:



```text

Tamanho:     30G

Usado:       5.0G

Disponível:  25G

Uso:         17%

```



Portanto:



```text

83% do disco permanece disponível

```



O armazenamento atual apresenta margem suficiente para:



\- imagens dos containers;

\- layers;

\- logs;

\- arquivos do sistema;

\- componentes do k3s.



O uso deve continuar sendo acompanhado conforme novas imagens e versões forem adicionadas.



\---



\# 15. Análise das medições



\## CPU



A análise mostrou dois comportamentos distintos.



\### Durante cold start



```text

\~75% de CPU

```



Esse pico ocorre principalmente porque as três aplicações Spring Boot realizam simultaneamente:



\- inicialização da JVM;

\- inicialização do Spring;

\- scanning de repositories;

\- criação do contexto;

\- inicialização do Hibernate;

\- conexão com PostgreSQL;

\- inicialização do Tomcat.



Durante esse período, cada API Java chegou próximo do limite de `500m`.



\### Após estabilização



A média observada foi:



```text

\~129m

\~6%

```



Portanto, o pico de startup é temporário.



O node apresenta ampla margem de CPU em repouso e baixa carga.



Entretanto, não foi realizado teste de carga de usuários nesta etapa.



Por isso, as medições comprovam capacidade suficiente para o ambiente acadêmico atual, mas não representam dimensionamento para produção em larga escala.



\---



\## Memória



O uso do node permaneceu em aproximadamente:



```text

24%

```



com cerca de:



```text

5.8Gi disponíveis

```



O consumo dos quatro Pods foi aproximadamente:



```text

912Mi

```



A memória não representa atualmente um gargalo para o cluster.



\---



\## Disco



O filesystem raiz apresentou:



```text

17% utilizado

```



com:



```text

25G disponíveis

```



O armazenamento também não representa um gargalo atualmente.



\---



\# 16. Avaliação final de capacidade



A capacidade teórica configurada anteriormente é:



```text

Requests:

CPU:     550m

Memória: 1280Mi

```



A utilização observada em regime estabilizado foi aproximadamente:



```text

Node:

CPU média:      129m

CPU:            \~6%

Memória:        \~1932Mi

Memória:        24%



Pods EcoCiente:

CPU:            \~8m em repouso

Memória:        \~912Mi

```



A EC2 utilizada possui:



```text

2 vCPU

8 GiB de memória

30 GiB gp3

```



Com base nessas medições, o `t3.large` é considerado adequado para os quatro workloads atuais no ambiente acadêmico.



O ambiente possui ampla margem em:



\- memória;

\- armazenamento;

\- CPU em regime estabilizado.



Existe um pico de CPU importante durante cold start:



```text

\~75%

```



porém ele é temporário e ocorre enquanto as três aplicações Java inicializam simultaneamente.



Após a inicialização, o consumo retorna para aproximadamente:



```text

4% a 6% de CPU

```



nas condições observadas.



\---



\# 17. PostgreSQL e escalabilidade



O PostgreSQL externo continua sendo um fator importante de capacidade.



As três APIs Java possuem pools pequenos, planejados em aproximadamente:



```text

3 conexões máximas por aplicação

```



Total teórico:



```text

3 APIs x 3 = 9 conexões

```



A IA Eko foi preparada para futuramente utilizar:



```text

POSTGRES\_POOL\_MIN=1

POSTGRES\_POOL\_MAX=2

```



Com a IA conectada:



```text

9 + 2 = 11 conexões

```



Considerando um limite de aproximadamente:



```text

20 conexões

```



a margem teórica seria:



```text

9 conexões

```



Esse limite deve ser considerado antes de aumentar réplicas.



Embora CPU e memória permitam expansão, o banco pode se tornar um limitador antes da EC2.



Por isso, o aumento de réplicas não deve ser realizado apenas com base na disponibilidade de CPU e RAM.



\---



\# 18. Decisões de arquitetura relacionadas à capacidade



As medições reforçam as decisões adotadas.



\## Uma réplica por aplicação



Para o cenário acadêmico atual, uma réplica é suficiente.



A infraestrutura permite escalabilidade horizontal quando necessária, mas manter réplicas adicionais permanentemente aumentaria:



\- consumo de memória;

\- conexões PostgreSQL;

\- quantidade de containers;

\- complexidade operacional.



\---



\## Utilitários fora do runtime permanente



Os projetos:



```text

md-rpa-integration

md-populador-pgsql

```



não permanecem ativos no cluster.



Essa decisão evita consumo desnecessário de recursos.



\---



\## Recursos diferenciados para IA



A IA Eko possui:



```text

CPU request:     250m

CPU limit:       1000m

Memory request:  512Mi

Memory limit:    1Gi

```



Os valores maiores fornecem margem para evolução dos componentes de IA sem obrigar as APIs Java a utilizar os mesmos limites.



\---



\## Cold start conhecido



O cold start simultâneo dos serviços produz um pico relevante de CPU.



A infraestrutura conseguiu concluir normalmente a inicialização dos quatro workloads.



As startup probes permitiram que as aplicações Java tivessem tempo para concluir seus processos de inicialização antes de serem consideradas disponíveis.



\---



\# 19. Limitações da análise



As medições realizadas representam:



```text

cluster ativo

4 workloads ativos

baixa carga de usuários

ambiente acadêmico

```



Não foram realizados nesta etapa:



\- testes de carga intensivos;

\- testes com centenas ou milhares de usuários simultâneos;

\- benchmark de throughput;

\- benchmark de latência sob carga;

\- autoscaling automático;

\- alta disponibilidade multi-node.



Portanto, a conclusão deste documento se aplica ao ambiente atual do projeto.



Caso o EcoCiente seja utilizado em produção com carga significativa, um novo capacity planning deverá ser realizado.



\---



\# 20. Conclusão final



O inventário demonstrou que apenas quatro aplicações precisam permanecer executando continuamente na infraestrutura:



```text

ds-autenticacao-api

ds-cadastro-api

ds-calendario-api

ia-eko

```



Os demais repositórios possuem responsabilidades diferentes, como:



\- cliente Mobile;

\- migração de dados;

\- população de banco;

\- infraestrutura;

\- automação;

\- templates;

\- criação de repositórios.



Os requests Kubernetes dos quatro workloads totalizam:



```text

CPU:     550m

Memória: 1280Mi

```



Durante o cold start foi observado:



```text

CPU:     \~1515m / 75%

Memória: \~1702Mi / 21%

```



Após a estabilização, três amostras consecutivas apresentaram:



```text

CPU:

137m

127m

123m



Média:

129m

\~6%

```



A memória permaneceu em aproximadamente:



```text

24%

```



e o disco apresentou:



```text

17% utilizado

83% disponível

```



Os quatro Pods consumiram aproximadamente:



```text

912Mi de memória

```



no período medido.



Com base nessas evidências, a instância:



```text

t3.large

2 vCPU

8 GiB RAM

30 GiB gp3

```



possui capacidade suficiente para o ambiente acadêmico atual do EcoCiente.



A maior utilização de CPU ocorre durante a inicialização simultânea das aplicações Java, mas o consumo reduz significativamente após o startup.



No estado estabilizado e sem carga significativa, CPU, memória e disco apresentam margem confortável.



A infraestrutura atual, portanto, é considerada adequada para os quatro workloads permanentes definidos no inventário, mantendo como principais pontos de atenção futuros:



1\. crescimento da carga real;

2\. limite de conexões PostgreSQL;

3\. novas aplicações permanentes;

4\. aumento de réplicas;

5\. crescimento das integrações e processamento da IA.

