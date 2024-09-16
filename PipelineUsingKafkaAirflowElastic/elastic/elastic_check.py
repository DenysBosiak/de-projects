import elasticsearch
from elasticsearch import Elasticsearch


print(elasticsearch.__version__)

es = Elasticsearch("http://localhost:9200")

print(es.info())

res = es.index (
    index="sensor_data",
    document={
        "sensor_id": 1,
        "temperature": 21.15,
        "humidity": 30.74,
        "timestamp": '2024-09-16 09:55:44'
        }
    )

print(res['result'])