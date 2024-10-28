import io
from datetime import timedelta

from minio import Minio
from minio.error import S3Error
from minio_config import config

import pandas as pd

def main():
    client = Minio(
        endpoint="localhost:9000",
        access_key=config['access_key'],
        secret_key=config['secret_key'],
        secure=False
    )

    bucket_name = 'bucket'
    objects = client.list_objects(bucket_name=bucket_name, recursive=True)

    for obj in objects:
        if 'nyc_taxi' in obj.object_name:
            url = client.get_presigned_url(
                method='GET',
                bucket_name=bucket_name,
                object_name=obj.object_name,
                expires=timedelta(hours=1)
            )

            data = pd.read_parquet(url)

            for index, row in data.iterrows():
                vendor_id = str(row['VendorID'])
                pickup_datetime = str(row['tpep_pickup_datetime'])
                pickup_datetime_formatted = pickup_datetime.replace(":", "-").replace(" ", "-")
                file_name = f"trip_{vendor_id}_{pickup_datetime_formatted}.json"

                record = row.to_json()
                record_bytes = record.encode('utf-8')
                record_stream = io.BytesIO(record_bytes)
                record_stream_len = len(record_bytes)

                client.put_object(
                    bucket_name = 'nyt-records',
                    object_name = f"nyc_taxi_records/{file_name}",
                    data = record_stream,
                    length = record_stream_len,
                    content_type = 'application/json'
                )

                print(f"Uploaded {file_name} to Minio")

                break

        break


if __name__ == "__main__":
    try:
        main()
    except S3Error as e:
        print(f"ERROR OCCURRED: {e}")