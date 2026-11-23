"""Gera ficha para auditoria humana das questões completas. Mantém referência verificável."""
import argparse,csv,json,random
from pathlib import Path
from app.data import Questao
p=argparse.ArgumentParser();p.add_argument('arquivo');p.add_argument('--saida',default='evidencias/amostra_manual.csv');args=p.parse_args()
docs={};rng=random.Random(20261123)
for raw in Path(args.arquivo).read_text().splitlines():
    q=Questao.model_validate_json(raw); docs[q.chave()]=q
if len(docs)<50: raise SystemExit("São necessárias ao menos 50 questões diferentes.")
with open(args.saida,'x') as f:
    w=csv.writer(f);w.writerow(["id","curso","ano","tipo","numero","pdf","pagina","pagina_final","texto_ok","alternativas_ok","chave_ok","midia_ok","metadados_ok","observacao"])
    for k in rng.sample(sorted(docs),50):
        d=docs[k];w.writerow([k,d.curso,d.ano,d.tipo,d.numero,d.pdf,d.pagina,d.pagina_final,"","","","","",""])

