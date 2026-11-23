from app.data import Questao

INDEX="enade-v1"
TEXT=["enunciado","texto_base","competencias","objetos"]
properties={k:{"type":"keyword"} for k in ["curso","area","caderno","componente","tipo","pdf","gabarito","competencias","objetos"]}
for k in ["competencias","objetos"]: properties[k]["fields"]={"busca":{"type":"text","analyzer":"pt"}}
properties.update({k:{"type":"integer"} for k in ("ano","numero","pagina","pagina_final")})
properties.update({k:{"type":"text","analyzer":"pt"} for k in ("enunciado","texto_base")})
properties.update(anulada={"type":"boolean"},alternativas={"type":"object","enabled":False},midia={"type":"object","enabled":False})
mapping={"settings":{"number_of_shards":3,"number_of_replicas":0,"analysis":{
    "filter":{"sin":{"type":"synonym","synonyms":["ética, moral","privacidade, proteção de dados"]},"rad":{"type":"stemmer","language":"light_portuguese"}},
    "analyzer":{"pt":{"tokenizer":"standard","filter":["lowercase","sin","asciifolding","rad"]}}}},
    "mappings":{"dynamic":"strict","properties":properties}}
def consulta(q,filters,page):
    clauses=[{"term":{k:v}} for k,v in filters.items() if v is not None and v!="" ]
    boolean={"filter":clauses}
    if q: boolean["must"]=[{"multi_match":{"query":q,"fields":["enunciado^3","texto_base","competencias.busca^2","objetos.busca"],"operator":"and"}}]
    return {"query":{"bool":boolean},"size":10,"from":10*(page-1),"track_total_hits":True,"highlight":{"pre_tags":["⟦"],"post_tags":["⟧"],"fields":{"enunciado":{},"texto_base":{}}}}

