"""Dois PDFs didáticos de autoria do projeto. Sem questões copiadas do Inep."""
import json,fitz
from pathlib import Path
from scripts.extrair import extrair

cases=[
("Sistemas de Informação","Tecnologia",[
("Uma empresa reutiliza históricos de localização para outra finalidade. Qual decisão respeita a ética no uso desses dados?",["Publicar os históricos completos.","Verificar a finalidade e limitar os dados utilizados."],"B","Ética profissional"),
("Uma fila entrega novamente a mesma mensagem após uma falha. Qual escolha evita duplicar a questão no índice?",["Usar uma chave estável no índice.","Gerar um identificador aleatório a cada tentativa."],"A","Projetar sistemas"),
("Discuta como uma equipe pode avaliar a privacidade de um painel antes da publicação.",[],None,"Ética profissional")]),
("Administração","Ciências Sociais Aplicadas",[
("Um fornecedor oferece um presente à comissão de compras. Que conduta preserva a ética na contratação?",["Registrar o conflito e aplicar os critérios públicos.","Aceitar a oferta e alterar as notas."],"A","Ética profissional"),
("Uma equipe compara decisões pelo mesmo critério moral. Qual procedimento facilita a auditoria?",["Apagar as justificativas anteriores.","Registrar critérios e justificativas de cada decisão."],"B","Ética profissional"),
("Duas unidades registram 18 e 12 atendimentos. Qual é a participação da primeira no total?",["60%.","40%."],"A","Interpretar indicadores")])]
def make(out):
    records=[]
    for idx,(curso,area,items) in enumerate(cases):
        stem=f"didatico-{idx+1}"; doc=fitz.open(); refs={}; gb=fitz.open(); gp=gb.new_page();gy=60
        for pos,(title,opts,ans,comp) in enumerate(items,1):
            disc=not opts; n=1 if disc else pos; ref=("D" if disc else "")+str(n)
            p=doc.new_page(); p.insert_text((52,54),"CADERNO DIDÁTICO | "+curso,fontsize=12)
            header=("QUESTÃO DISCURSIVA " if disc else "QUESTÃO ")+str(n)
            p.insert_text((52,110),header)
            p.insert_textbox((52,140,525,260),title,fontsize=12)
            for j,o in enumerate(opts): p.insert_text((52,290+30*j),chr(65+j)+") "+o)
            if ans: gp.insert_text((40,gy),f"QUESTÃO {n} "+("ANULADA" if idx==1 and pos==2 else ans));gy+=24
            refs[ref]=dict(componente="FG" if pos==1 else "CE",competencias=[comp],objetos=[comp])
            if idx==1 and pos==3: refs[ref]["formula_fracao"]=["18","18+12"]
        doc.save(out/(stem+".pdf"));gb.save(out/(stem+"-gb.pdf"))
        manifest=dict(ano=2021,curso=curso,area=area,caderno="didático",arquivo=stem+".pdf",arquivo_gabarito=stem+"-gb.pdf",pdf=stem+".pdf",questoes=refs)
        (out/(stem+".json")).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
        records.extend(extrair(manifest,out))
    (out/"questoes.jsonl").write_text("".join(q.model_dump_json()+"\n" for q in records))
if __name__=="__main__": make(Path("amostras"))

