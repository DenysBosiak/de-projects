config = {
    "openai": {
        "api_key": "OPENAI_KEY"
    },
    "kafka": {
        "sasl.username": "KAFKA_CLUSTER_API_KEY",
        "sasl.password": "KAFKA_CLUSTER_API_SECRET",
        "bootstrap.servers": "192.168.0.104:9092",
        "security.protocol": "PLAINTEXT",
        "sasl.mechanisms": "PLAIN",
        "session.timeout.ms": 50000
    },
    "schema_registry": {
        "url": "SCHEMA_REGISTRY_URL",
        "basic.auth.user.info": "SR_API_KEY:SR_API_SECRET"
    }
}