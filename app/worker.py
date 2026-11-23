import json,logging,sys,time,base64
from kafka import KafkaProducer,KafkaConsumer,TopicPartition,OffsetAndMetadata
from pydantic import ValidationError
from app.data import Questao
from app.services import elastic,Cluster
from app.search import INDEX
cfg=dict(bootstrap_servers=["kafka:9092"],security_protocol="SASL_SSL",sasl_mechanism="GSSAPI",sasl_kerberos_service_name="kafka",ssl_cafile="/run/cred/ca.crt")
def producer(): return KafkaProducer(**cfg,acks="all",retries=10,max_in_flight_requests_per_connection=1)
def publicar(path):
    p=producer()
    with open(path,"rb") as f:
        for raw in f:
            try: key=Questao.model_validate_json(raw).chave().encode()
            except ValidationError: key=None
            p.send("questoes",value=raw,key=key).get(timeout=40)
    p.close()
def consumir():
    import requests
    c=KafkaConsumer("questoes",**cfg,group_id="indexadores-v1",enable_auto_commit=False,auto_offset_reset="earliest",max_poll_records=1)
    dlq=producer(); redis=Cluster().redis
    for m in c:
        invalid=None
        try: q=Questao.model_validate_json(m.value)
        except ValidationError as err: invalid=str(err)
        if not invalid:
            try: elastic("PUT",f"/{INDEX}/_doc/{q.chave()}?refresh=wait_for",q.model_dump())
            except requests.HTTPError as err:
                if err.response.status_code!=400: raise
                invalid="Documento rejeitado pelo mapping"
        if invalid:
            rid=f"{m.topic}:{m.partition}:{m.offset}".encode()
            dlq.send("questoes-erros",key=rid,value=json.dumps(dict(erro=invalid,raw=base64.b64encode(m.value).decode())).encode()).get(timeout=40)
        else: redis.incr("geracao")
        tp=TopicPartition(m.topic,m.partition)
        c.commit({tp:OffsetAndMetadata(m.offset+1,"")})
        logging.warning("particao=%d offset=%d lag=%d dlq=%s",m.partition,m.offset,max(0,c.end_offsets([tp])[tp]-m.offset-1),bool(invalid))
if __name__=="__main__":
    if len(sys.argv)>1: publicar(sys.argv[1])
    else: consumir()

