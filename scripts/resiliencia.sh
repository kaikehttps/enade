#!/bin/bash
# Em um laboratório isolado recém-inicializado. Preserva volumes.
set -euo pipefail
mkdir -p evidencias
dc=(docker compose)
# Professor exporta o total antes e depois por um endpoint autorizado.
url=https://localhost:8443
cookie=$(mktemp); trap 'rm -f "$cookie"' EXIT
fetch(){ curl -fsS --cacert segredos/admin/ca.crt -b "$cookie" "$url$1"; }
python -c 'import json,pathlib; print(json.dumps(dict(usuario="professor",senha=pathlib.Path("segredos/admin/professor").read_text().strip())))' | curl -fsS --cacert segredos/admin/ca.crt -c "$cookie" -H 'Content-Type: application/json' --data-binary @- "$url/api/login" >/dev/null
fetch "/api/busca" > evidencias/antes.json
# Varia o caderno para criar IDs inéditos. O ensaio pode ser refeito.
run=$(date +%s)
python - "$run" <<'PY' > amostras/falha.jsonl
import json,sys
for l in open("amostras/questoes.jsonl"):
 d=json.loads(l); d["caderno"]="falha-"+sys.argv[1]; print(json.dumps(d))
PY
"${dc[@]}" kill -s SIGKILL worker
"${dc[@]}" stop worker
start=$(date +%s)
send(){ "${dc[@]}" run --rm --no-deps produtor sh infra/ticket.sh produtor/producer python -m app.worker /dados/falha.jsonl; }
send
"${dc[@]}" up -d worker
expected=$(python -c 'import json;print(json.load(open("evidencias/antes.json"))["total"]+6)')
wait_total(){ for i in $(seq 1 120); do
 fetch /api/busca >evidencias/depois.json
 test "$(python -c 'import json;print(json.load(open("evidencias/depois.json"))["total"])')" = "$expected" && return 0
 sleep 2
 done; return 1; }
wait_total
echo "6 documentos; recuperação e publicação em $(($(date +%s)-start)) s" >evidencias/tempo-recuperacao.txt
python - <<'PYIDS' >evidencias/ids-esperados.txt
from app.data import Questao
for raw in open("amostras/falha.jsonl"):
 print(Questao.model_validate_json(raw).chave())
PYIDS
while read -r id; do fetch "/api/item/$id" >/dev/null; done < evidencias/ids-esperados.txt
send
sleep 12
wait_total

"${dc[@]}" logs --no-color worker >evidencias/worker.log

