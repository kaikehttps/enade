# Acervo ENADE · Big Data

Projeto acadêmico da UniCatólica para extração, indexação e pesquisa de questões. O caminho principal usa Kafka KRaft, Elasticsearch, FastAPI e Redis, com Kerberos entre os clientes dos serviços Kafka/Elastic e seus servidores, e usuários no OpenLDAP. O perfil local serve para reproduzir a demonstração sem a infraestrutura. Consulte o relatório para saber quais ensaios foram executados.

## Subir o cluster de laboratório

Pré-requisitos: Docker Engine com Compose v2 em Linux ou Docker Desktop com contêineres Linux, internet para as imagens e pacotes e aproximadamente 6 GB de memória disponíveis. Identidades e certificados de laboratório são gerados no primeiro boot. O Elasticsearch usa uma licença **trial** para o realm Kerberos. Verifique a elegibilidade ou use licença compatível antes de demonstrar. O Compose inclui um nó de cada serviço de dados. Não há tolerância à perda física desse host.

```bash
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=40 topics setup produtor worker
curl --cacert segredos/admin/ca.crt https://localhost:8443/api/saude
```

Abra https://localhost:8443 e /docs para o Swagger. Confie na CA **do seu laboratório** no navegador de testes. Leia localmente os arquivos de senha em `segredos/admin/estudante` e `segredos/admin/professor` com a conta administradora da máquina. Os nomes de login são estudante e professor. Não copie a pasta de segredos. O diretório é criado pelo contêiner e pode exigir privilégios locais para leitura. Somente a API é publicada e fica restrita a localhost. Para encerrar preservando estado, execute `docker compose down`. Mantenha juntos a pasta de segredos e os volumes do KDC e dos bancos entre execuções.

**Inicialização.** O KDC cria tickets de serviço, a CA e as senhas. Os jobs setup e topics preparam índices, papéis e tópicos. O produtor carrega `amostras/questoes.jsonl`. Os jobs devem sair com código zero e o worker deve continuar ativo. Caso o Elastic falhe no bootstrap, confira os logs, os limites do host, a memória e a licença. Uma resposta 503 em saúde identifica uma dependência indisponível.

## Preparar a coleção oficial

1. Em Python 3.11 ou posterior, instale PyMuPDF, pydantic, requests e beautifulsoup4. Na raiz, rode `python -m scripts.coletar`. O coletor percorre o catálogo anual e as páginas de legislação do Inep, salva os PDFs por SHA-256 e lista URLs, diretrizes HTML e falhas em `acervo/inventario.json`. Revise links de portarias externas e páginas heterogêneas. Compare o inventário por ano e curso com o portal antes de declarar cobertura total.
2. Para cada prova, crie um manifesto como `amostras/didatico-1.json`. Use a URL oficial do PDF, curso, área, ano, edição/caderno e os caminhos locais da prova e do gabarito. A chave D1 identifica a primeira discursiva e 1 a primeira objetiva. Classifique FG/CE segundo o caderno da edição. Registre competências e objetos com base na respectiva diretriz. A correspondência entre questão e competência requer curadoria.
3. Gere os registros com `python -m scripts.extrair acervo/manifesto.json > /tmp/questoes.jsonl`. Confira os registros antes de juntá-los ao lote em `amostras/questoes.jsonl`. O produtor pode ser reexecutado com `docker compose run --rm produtor`. A mesma edição, curso, variante, número e tipo mantêm o mesmo ID.
4. PDFs com duas colunas, digitalizações, marcadores gráficos ou material compartilhado precisam de revisão. O extrator identifica cabeçalhos e alternativas em linhas de texto. Use `ignorar_linhas` para cabeçalhos recorrentes e preencha `texto_base` e eventuais correções por questão. O gabarito sem correspondência fica nulo; a marca ANULADA preserva o item. Padrões discursivos podem ser incluídos na curadoria.
5. Para mídia, o manifesto aceita `regiao_tabela: [pagina,[x0,y0,x1,y1]]` em pontos PDF, `formula_fracao: ["numerador","denominador"]`, `arestas: [["Origem","Destino"]]` e objetos `midia` revisados nos formatos latex, mermaid e markdown. Tabelas são lidas por células. Frações e diagramas exigem transcrição estruturada quando não há representação confiável no PDF. O backend dispensa chamadas pagas a LLM.

## Rodar a demonstração local

```bash
python -m venv .venv
. .venv/bin/activate
pip install fastapi uvicorn pydantic pymupdf
export MODO=local
read -rsp 'Senha temporária do modo local: ' DEMO_PASSWORD; echo
export DEMO_PASSWORD
uvicorn app.api:app --port 8000
```

Abra http://127.0.0.1:8000. Os dois usuários de teste usam a senha digitada. Neste modo, os dados vêm dos seis registros didáticos, e o índice e a sessão são reiniciados a cada execução. A renderização avançada de mídia é empacotada na imagem Docker; fora dela, o cliente mostra a representação textual quando as bibliotecas não estão presentes.

## Reproduzir as evidências

- `python -m scripts.avaliar` compara 70 respostas objetivas de dois gabaritos definitivos com a referência transcrita e mede a extração dos dois cadernos didáticos. Os arquivos de texto oficiais são recortes tabulares de gabarito. A auditoria dos 70 campos não valida o conteúdo integral de 70 questões.
- `python -m scripts.amostra acervo/lote_completo.jsonl` seleciona 50 IDs únicos com semente fixa. O avaliador deve abrir cada PDF/página e preencher a ficha por campo. Separe “inaplicável” de erro. Taxa por campo = acertos / campos aplicáveis; taxa por questão = questões com todos os campos aplicáveis corretos / questões revisadas.
- Para medições no cluster, defina `BASE=https://localhost:8443`, `CA=$PWD/segredos/admin/ca.crt` e carregue `SENHA` do arquivo local do professor. Rode `python -m scripts.medir > evidencias/latencia-cluster.json`. O script usa quatro clientes por padrão, mede p50/p95/p99 e confirma HIT/MISS pelo cabeçalho. Ajuste N e CLIENTES se necessário. Para o ensaio local, use BASE=http://127.0.0.1:8000 e SENHA igual a DEMO_PASSWORD.
- `docker compose run --rm -e SENHA produtor sh infra/ticket.sh produtor/producer python -m scripts.vazao` mede publicação até visibilidade de todos os novos IDs. O ensaio cria novos cadernos de benchmark. Execute em um laboratório descartável e não misture a contagem com a cobertura oficial.
- `bash scripts/resiliencia.sh` interrompe o consumidor, publica seis IDs novos, reinicia o consumidor e republica o mesmo lote. O teste espera acréscimo de seis documentos e salva contagens e logs de lag. Execute em instância de laboratório sem outros produtores. A retenção dos tópicos precisa cobrir o período de parada. Para testar a janela entre gravação e commit, interrompa o worker durante um lote maior e confira os mesmos IDs depois da recuperação.
- Para a DLQ, adicione uma linha inválida a **uma cópia** do lote, seguida de uma linha válida. Publique a cópia pela mesma rota do produtor. O log do worker registra dlq=True, partição, offset e lag. Mensagens que excedem o limite do broker requerem tratamento antes da publicação.
- `python -m scripts.demo_http` reproduz o teste da gravação com BASE e SENHA no modo local. Para usuários LDAP, defina SENHA_ESTUDANTE e SENHA_PROFESSOR e disponibilize a CA pelo ambiente CA. A pasta evidencias reúne os resultados locais já obtidos.

## Estrutura e entrega

`app/` contém o cliente e o backend; `infra/` configura os serviços; `scripts/` contém coleta, extração e ensaios; `amostras/` contém o corpus didático; `evidencias/` traz os resultados brutos; `relatorio/` inclui o fonte LaTeX. A API oferece login, fim de sessão, busca, detalhe, carrinho, exportação JSON, agregações, saúde e métricas. Os scripts de laboratório não enviam nada ao AVA.

O ZIP inclui o diretório Git com um commit inicial. Para entregar, publique o repositório da equipe e confirme acesso do professor. Compartilhe separadamente o vídeo e o relatório. A autoria dos cadernos didáticos e o uso de IA são declarados no relatório.

