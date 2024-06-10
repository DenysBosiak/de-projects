from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.base_aws import AwsGenericHook
from datetime import timedelta, datetime
import time



def glue_job_s3_to_redshift_transfer(job_name, **kwargs):
    session = AwsGenericHook(aws_conn_id='aws_s3_conn')

    boto3_session = session.get_session(region_name='eu-north-1')

    client = boto3_session.client('glue')
    client.start_job_run(
        JobName=job_name
    )


def get_run_id():
    time.sleep(8)
    session = AwsGenericHooks.(aes_conn_id='aws_s3_conn')
    boto3_session = session.get_session(region_name='eu-north-1')
    glue_client = boto3_session.client('glue')
    response = glue_client.get_job_runs(JobName="s3_upload_to_redshift_gluejob")
    job_run_id = response["JobRuns"][0]["Id"]
    return job_run_id


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 10),
    'email': ['test@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(seconds=15)
}

with DAG('my_dag',
         default_args=default_args,
         schedule_interval='@weakly',
         catchup=False) as dag:
    

    glue_job_trigger = PythonOperator(
        task_id='glue_job_trigger',
        python_callable=glue_job_s3_to_redshift_transfer,
        op_kwargs={
            'job_name': 's3_upload_to_redshift_gluejob'
        }
    )


    grab_glue_job_run_id = PythonOperator(
        task_id='grab_glue_job_run_id',
        python_callable=get_run_id
    )

