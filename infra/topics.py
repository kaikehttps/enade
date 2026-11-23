import time
from kafka.admin import KafkaAdminClient,NewTopic
from kafka.errors import KafkaError,TopicAlreadyExistsError
from app.worker import cfg
for attempt in range(90):
    try:
        admin=KafkaAdminClient(**cfg)
        for name in ["questoes","questoes-erros"]:
            try: admin.create_topics([NewTopic(name,3,1)])
            except TopicAlreadyExistsError: pass
        break
    except KafkaError:
        if attempt==89: raise
        time.sleep(3)

