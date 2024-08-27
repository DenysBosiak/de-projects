import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from pyspark.sql.functions import from_json, col
from config.config import config
from time import sleep


def start_streaming(spark: SparkSession):
    topic = 'customers_tip_review'

    while True:
        try:
            stream_df = (spark.readStream.format("socket")
                        .option("host", "0.0.0.0")
                        .option("port", 9999)
                        .load()
                        )
            
            schema = StructType([
                StructField("text", StringType()), \
                StructField("date", StringType()), \
                StructField("compliment_count", IntegerType()), \
                StructField("business_id", StringType()), \
                StructField("user_id", StringType())
            ])

            stream_df = stream_df.select(from_json(col('value'), schema).alias("data")).select(("data.*"))

            # query = stream_df.writeStream.outputMode("append").format("console").options(truncate=False).start()
            # query.awaitTermination()

            kafka_df = stream_df.selectExpr("CAST(user_id AS STRING) AS key", "to_json(struct(*)) AS value")
            query = (kafka_df.writeStream
                        .format("kafka")
                        .option("kafka.bootstrap.servers", config['kafka']['bootstrap.servers'])
                        .option("kafka.sasl.protocol", config['kafka']['security.protocol'])
                        .option("kafka.sasl.mechanism", config['kafka']['sasl.mechanisms'])
                        .option('checkpointLocation', '/tmp/checkpoint')
                        .option('topic', topic)
                        .start()
                        .awaitTermination()
                    )
        except Exception as e:
            print(f"Exception encountered: {e}. Retrying in 10 seconds")
            sleep(10)

if __name__ == "__main__":
    spark_conn = SparkSession.builder.appName("SocketStreamConsumer").getOrCreate()
    start_streaming(spark_conn)