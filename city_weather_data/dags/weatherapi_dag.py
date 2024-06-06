from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import timedelta, datetime
import json
import pandas as pd



# Convert temperature from kelvin to fahrenheit
def convert_kelvin_to_fahrenheit(temp_in_kelvin):
    temp_in_fahrenheit = (temp_in_kelvin - 273.15) * (9/5) + 32
    return round(temp_in_fahrenheit, 3)


# Transform extracted data
def transform_load_data(task_instance):
    data = task_instance.xcom_pull(task_ids = "group_a.extract_weather_data")

    city = data["name"]
    weather_description = data["weather"][0]["description"]
    temp = convert_kelvin_to_fahrenheit(data["main"]["temp"])
    feels_like = convert_kelvin_to_fahrenheit(data["main"]["feels_like"])
    min_temp = convert_kelvin_to_fahrenheit(data["main"]["temp_min"])
    max_temp = convert_kelvin_to_fahrenheit(data["main"]["temp_max"])
    pressure = data["main"]["pressure"]
    humidity = data["main"]["humidity"]
    wind_speed = data["wind"]["speed"]
    time_of_record = datetime.utcfromtimestamp(data["dt"] + data["timezone"])
    sunrise_time = datetime.utcfromtimestamp(data["sys"]["sunrise"] + data["timezone"])
    sunset_time = datetime.utcfromtimestamp(data["sys"]["sunset"] + data["timezone"])

    transformed_data = {
        "city": city,
        "description": weather_description,
        "temperature_farenheit": temp,
        "feels_like_farenheit": feels_like,
        "minimum_temp_farenheit": min_temp,
        "maximum_temp_farenheit": max_temp,
        "pressure": pressure,
        "humidity": humidity,
        "wind_speed": wind_speed,
        "time_of_record": time_of_record,
        "sunrise_local_time": sunrise_time,
        "sunset_local_time": sunset_time
    }
    transformed_data_list = [transformed_data]
    df_data = pd.DataFrame(transformed_data_list)

    df_data.to_csv(f"current_weather_data_kyiv.csv", index=False, header=False)


def load_data():
    hook = PostgresHook(postgres_conn_id="postgres_conn")    

    hook.copy_expert(sql="COPY weather_data FROM stdin WITH DELIMITER AS ','",
                     filename="current_weather_data_kyiv.csv")
    

def save_joined_data_into_S3(task_instance):
    data = task_instance.xcom_pull(task_ids="join_data_in_postgres")
    df = pd.DataFrame(data, columns=['city', 'description', 'temperature_farenheit', 'feels_like_farenheit', 'minimun_temp_farenheit', 'maximum_temp_farenheit', 'pressure','humidity', 'wind_speed', 'time_of_record', 'sunrise_local_time', 'sunset_local_time', 'state', 'census_2020', 'land_area_sq_mile_2020'])

    now = datetime.now()
    dt_string = now.strftime("%d%m%Y%H%M%S")
    dt_string = "joined_weather_data_kyiv_" + dt_string
    df.to_csv(f"s3://mybucketfordeveloping/{dt_string}.csv", index=False)


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 5, 22),
    'email': ['test@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2)
}


with DAG("weather_dag_parallel",
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False
         ) as dag:
    
    start_pipeline = EmptyOperator(
        task_id="task_start_pipeline"
    )

    join_data = PostgresOperator(
        task_id="join_data_in_postgres",
        postgres_conn_id="postgres_conn",
        sql='''
                SELECT 
                    weather.city,                    
                    description,
                    temperature_farenheit,
                    feels_like_farenheit,
                    minimum_temp_farenheit,
                    maximum_temp_farenheit,
                    pressure,
                    humidity,
                    wind_speed,
                    time_of_record,
                    sunrise_local_time,
                    sunset_local_time,
                    state,
                    census_2020,
                    land_area_sq_mile_2020                    
                FROM weather_data AS weather
                INNER JOIN city_look_up AS city ON city.city = weather.city;
            '''
    )       

    load_joined_data = PythonOperator(
        task_id='load_joined_data',
        python_callable=save_joined_data_into_S3
    )

    end_pipeline = EmptyOperator(
        task_id="task_end_pipeline"
    )    

    with TaskGroup(group_id="group_a", tooltip="Extract_from_S3_and_WeatherApi") as group_a:
        create_table_1 = PostgresOperator(
            task_id="task_create_table_1",
            postgres_conn_id="postgres_conn",
            sql='''
                CREATE TABLE IF NOT EXISTS city_look_up (
                    city text NOT NULL,
                    state text NOT NULL,
                    census_2020 numeric NOT NULL,
                    land_Area_sq_mile_2020 numeric NOT NULL
                );
            '''
        )

        truncate_table = PostgresOperator(
            task_id="truncate_table_city_look_up",
            postgres_conn_id="postgres_conn",
            sql='''TRUNCATE TABLE city_look_up;
            '''
        ) 

        upload_S3_to_postgres = PostgresOperator(
            task_id="upload_S3_to_postgres",
            postgres_conn_id="postgres_conn",
            sql=''' SELECT aws_s3.table_import_from_s3('city_look_up', '', '(format csv, DELIMITER '','', HEADER true)', 'mybucketfordeveloping', 'us_city.csv', 'eu-north-1'); '''
        )

        create_table_2 = PostgresOperator(
            task_id="task_create_table_2",
            postgres_conn_id="postgres_conn",
            sql='''
                CREATE TABLE IF NOT EXISTS weather_data (
                    city text,
                    description text,
                    temperature_farenheit numeric,
                    feels_like_farenheit numeric,
                    minimum_temp_farenheit numeric,
                    maximum_temp_farenheit numeric,
                    pressure numeric,
                    humidity numeric,
                    wind_speed numeric,
                    time_of_record timestamp,
                    sunrise_local_time timestamp,
                    sunset_local_time timestamp
                );
            '''
        )             

        is_kyiv_weather_api_ready = HttpSensor(
            task_id = 'is_weater_api_ready',
            http_conn_id = 'weathermap_api',
            endpoint = '/data/2.5/weather?q=Kyiv&appid=a2fc2ab52b832be75e0040a88f3e406a'
        )        

        extract_kyiv_weather_data = SimpleHttpOperator(
            task_id = 'extract_weather_data',
            http_conn_id = 'weathermap_api',
            endpoint = '/data/2.5/weather?q=Kyiv&appid=a2fc2ab52b832be75e0040a88f3e406a',
            method = 'GET',
            response_filter = lambda r: json.loads(r.text),
            log_response = True
        )      

        transform_load_weather_data = PythonOperator(
            task_id = 'transform_load_weather_data',
            python_callable = transform_load_data
        )          

        load_weather_data = PythonOperator(
            task_id = 'load_weather_data',
            python_callable = load_data
        )

        create_table_1 >> truncate_table >> upload_S3_to_postgres
        create_table_2 >> is_kyiv_weather_api_ready >> extract_kyiv_weather_data >> transform_load_weather_data >> load_weather_data

    start_pipeline >> group_a >> join_data >> load_joined_data >> end_pipeline