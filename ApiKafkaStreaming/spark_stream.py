import logging
from datetime import datetime
import time

from cassandra.cluster import Cluster
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StructField, StringType


def create_keyspace(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS spark_streams
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
    """)

    print("Keyspace created successfully!")


def create_table(session):
    session.execute("""                    
        CREATE TABLE IF NOT EXISTS spark_streams.created_users (
                    id UUID PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    gender TEXT,
                    address TEXT,
                    post_code TEXT,
                    email TEXT,
                    username TEXT,                    
                    registered_date TEXT,
                    phone TEXT,
                    picture TEXT

        );
    """)

    print("Table created successfully!")    


def insert_data(session, **kwargs):
    print("Insertin data ...")

    user_id = kwargs.get('id')
    first_name = kwargs.get('first_name')
    last_name = kwargs.get('last_name')
    gender = kwargs.get('gender')
    address = kwargs.get('address')
    postcode = kwargs.get('post_code')
    email = kwargs.get('email')
    username= kwargs.get('username')
    registered_date = kwargs.get('registered_date')
    phone = kwargs.get('phone')
    picture = kwargs.get('picture')

    try:
        session.execute("""
            INSERT INTO spark_streams.created_users
            (id, first_name, last_name, gender, address, postcode, email, username, registered_date, phone, picture)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, first_name, last_name, gender, address, postcode, email, username, registered_date, phone, picture))
        logging.info(f"Data inserted for {first_name} {last_name}")
    
    except Exception as e:
        logging.error(f"Couldn't insert data due tu {e}")


def create_spark_connection():
    s_conn = None
    JAR_PACKAGES = [
        "com.datastax.spark:spark-cassandra-connector_2.12:3.4.1",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1",
        "org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.4.1"
    ]

    try:
        s_conn = SparkSession.builder \
                            .appName("SparkStreaming") \
                            .config("spark.jars.packages", ",".join(JAR_PACKAGES)) \
                            .config("spark.cassandra.connection.host", "localhost") \
                            .config("spark.cassandra.connection.port", "9042") \
                            .getOrCreate()                            
        
        s_conn.sparkContext.setLogLevel("ERROR")
        logging.info("Spark connection created successfully!")
    except Exception as e:
        logging.error(f"Couldn't create the spark session due the exception {e}")
        
    return s_conn


def connect_to_kafka(spark_conn):
    spark_df = None

    try:
        spark_df = spark_conn.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "localhost:9092") \
            .option("subscribe", "users_created") \
            .option("startingOffsets", "earliest") \
            .option("failOnDataLoss", "False") \
            .load()
        logging.info("Kafka dataframe created successfully!")
        print("Kafka Dataframe was created successfully") 

    except Exception as e:
        logging.error(f"Kafka dataframe could not be created because: {e}")

    return spark_df    


def create_cassandra_connection():
    try:
        # Connection to the cassandra cluster
        cluster = Cluster(['localhost'])

        cas_session = cluster.connect()
        
        return cas_session
    except Exception as e:
        logging.error(f"Couldn't create cassandra connection due to {e}")
        return None
    

def create_selection_df_from_kafka(spark_df):
    sel_expanded = None

    try:
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("first_name", StringType(), False),
            StructField("last_name", StringType(), False),
            StructField("gender", StringType(), False),
            StructField("address", StringType(), False),
            StructField("post_code", StringType(), False),
            StructField("email", StringType(), False),
            StructField("username", StringType(), False),
            StructField("registered_date", StringType(), False),
            StructField("phone", StringType(), False),
            StructField("picture", StringType(), False)
        ])

        sel = spark_df.selectExpr("cast(value as string) as value")
        sel_expanded = sel.select(from_json(col('value'), schema).alias('data')).select("data.*")
        print(sel_expanded)

    except Exception as e:
        print(f"Couldn't create selection dataframe due to {e}")

    return sel_expanded  


if __name__ == "__main__":
    # Create spark connection
    spark_conn = create_spark_connection()

    if spark_conn is not None:
        # Connect to kafka with spark connection
        df = connect_to_kafka(spark_conn)
    
        selection_df = create_selection_df_from_kafka(df)

        # Create cassandra session
        session = create_cassandra_connection()

        if session is not None:
            create_keyspace(session)
            create_table(session)
            
            logging.info("Streaming is being started...")

            streaming_query = (selection_df.writeStream
                                            .format("org.apache.spark.sql.cassandra")
                                            .option("checkpointLocation", "/tmp/checkpoint")
                                            .options(keyspace="spark_streams", table="created_users")
                                            .start())           
            streaming_query.awaitTermination()