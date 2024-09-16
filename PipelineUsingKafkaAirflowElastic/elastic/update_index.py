from elasticsearch import Elasticsearch


es = Elasticsearch(["http://localhost:9200"])
es_index = 'sensor_data'
es_id = 'Ye8K-pEBgwghPijEHK6H'


es.update(
    index=es_index,
    id=es_id,
    doc={
        "sensor_id": 10,
        "temperature": 0,
        "humidity": 0,
        "timestamp": '2024-09-01 00:00:00' 
    }
)