import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
import json
from datetime import datetime

import airflow.utils
import airflow.utils.dates

from kafka import KafkaConsumer
from elasticsearch import Elasticsearch


def index_to_elasticsearch(es: Elasticsearch, sensor_data):
    try:
        # Convert timestamp string to ISO 8601 format
        timestamp_str = sensor_data['timestamp']
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        iso_timestamp = timestamp.isoformat() + 'Z' # Add 'Z' to indicate UTC

        # Index the data into Elasticsearch
        es.index(
            index="sensor_data", # Elasticsearch index name
            body={
                'sensor_id': sensor_data['sensor_id'],
                'temperature': sensor_data['temperature'],
                'humidity': sensor_data['humidity'],
                'timestamp': iso_timestamp # Use ISO 8601 timestamp format
            }
        )
    except Exception as e:
        print(f"Failed to index data: {e}")


def consume_data():
    # Initialize the Elasticsearch client
    es = Elasticsearch([{"host":"elastic", "Port":9200, "scheme":"sensor_data"}])

    # Create a Kafka consumer
    consumer = KafkaConsumer(
        'sensor_data',
        bootstrap_servers=['broker:29092'],
        auto_offset_reset='earliest',
        group_id='sensor-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        sensor_data = message.value

        # Index the data into Elasticsearch
        index_to_elasticsearch(es, sensor_data)
        print(f"Indexed to Elasticsearch: {sensor_data}")


dag_args = {
    "owner": "Mine",
    "start_date": airflow.utils.dates.days_ago(1)
    }


with DAG(
    dag_id="Sensor_Data_Consume",
    default_args=dag_args,
    schedule_interval="@yearly",
    catchup=False
) as dag:
    
    start = EmptyOperator(task_id="start")

    python_job = PythonOperator(
        task_id="sensor_data_consumer",
        python_callable=consume_data
    )

    end = EmptyOperator(task_id="finish")


    start >> python_job >> end