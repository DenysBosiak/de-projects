import pyspark
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
from pyspark.sql.functions import from_json, col


def start_streaming(spark: SparkSession):
    try:
        stream_df = (spark.readStream.format("socket")
                    .option("host", "localhost")
                    .option("port", 9999)
                    .load()
                    )
        schema = StructType([
            StructField("date", StringType()),
            StructField("description", StringType()),
            StructField("lang", StringType()),
            StructField("category1", StringType()),
            StructField("category2", StringType()),
            StructField("granularity", StringType())
        ])

        stream_df = stream_df.select(from_json(col('value'), schema).alias("data")).select(("data.*"))
        query = stream_df.writeStream.outputMode("append").format("console").options(truncate=False).start()
        query.awaitTermination()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    spark_conn = SparkSession.builder.appName("SocketStreamConsumer").getOrCreate()
    start_streaming(spark_conn)