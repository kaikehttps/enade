"""Executar a partir da raiz do projeto, apenas com os dados incluídos."""
from pathlib import Path
from time import perf_counter
from tempfile import TemporaryDirectory
from statistics import median
from scripts.extrair import respostas,extrair
from app.data import Questao
import json,csv
out=Path("evidencias")
# Transcrição independente, na ordem das questões 1..35. X = anulada.
references={"bacharelado_sistema_informacao":"ECBB AACD CECB DCD ACBAB CEBBEE DAD EACXDD","tecnologia_analise_desenvolvimento_sistemas":"ECBB AACD CDEC CEBE CAAE BABD EECB DCDBDAA"}
rows=[]
for curso,s in references.items():
    pred=respostas((out/(curso+".txt")).read_text())
    letters=s.replace(" ","")
    assert len(letters)==35 and len(pred)==35,(curso,letters,len(pred))
    for n,v in enumerate(letters,1):
        expected="ANULADA" if v=="X" else v
        rows.append([curso,2021,n,expected,pred.get(n),pred.get(n)==expected])
with (out/"validacao_chaves.csv").open("w") as f:
    w=csv.writer(f);w.writerow(["curso","ano","numero","referencia_conferida","extraido","coincide"]);w.writerows(rows)
times=[]
for rep in range(25):
    start=perf_counter(); records=[]
    for m in sorted(Path("amostras").glob("*.json")): records.extend(extrair(json.loads(m.read_text()),m.parent))
    times.append(perf_counter()-start)
summary=dict(chaves=len(rows),corretas=sum(r[-1] for r in rows),pdfs_prova_didaticos=2,questoes_didaticas=len(records),repeticoes=len(times),mediana_segundos=median(times),extracao_docs_s=len(records)/median(times))
(out/"extracao.json").write_text(json.dumps(summary,indent=2)); print(summary)

