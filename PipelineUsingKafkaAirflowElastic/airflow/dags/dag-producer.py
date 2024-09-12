import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator

import random, time, json
from datetime import datetime
import airflow.utils
import airflow.utils.dates
from kafka import KafkaProducer
import logging


# Function to simulate sensor data
def generate_sensor_data(id):
    sensor_data ={
        "sensor_id": id,
        "temperature": round(random.uniform(20.0, 30.0), 2), # Random temperature between 20.0 and 30.0 degrees
        "humidity": round(random.uniform(30.0, 60.0), 2), # Random humidity betwen 30.0% and 60.0%
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return sensor_data


def stream_data():
    producer = KafkaProducer(bootstrap_servers=["broker:29092"], max_block_ms=5000)
    current_time = time.time()
    id = 0
    while True:
        if time.time() > current_time + 60:
            break
        try:
            id+=1
            res = generate_sensor_data(id)
            if id >= 5:
                id = 0
            print(res, end="\r")

            producer.send('sensor_data', json.dumps(res).encode('utf-8'))
            time.sleep(1)
        except Exception as e:
            logging.error(f"An error occured: {e}")
            continue


dag_args = {
    "owner": "Mine",
    "start_date": airflow.utils.dates.days_ago(1)
}


with DAG (
    dag_id = "Sensor_Data",
    default_args = dag_args,
    schedule_interval = "*/5 * * * *",
    catchup = False) as dag:

    start = EmptyOperator(task_id = "start")

    streaming = PythonOperator(
        task_id = "sensor_data_streaming",
        python_callable=stream_data
    ) 

    end = EmptyOperator(task_id = "end")


    start >> streaming >> end