from confluent_kafka import Consumer

c = Consumer({
    "bootstrap.servers": "localhost:9096",
    "group.id": "test",
    "auto.offset.reset": "earliest"
})

print(c.list_topics().topics["demo-topic"].partitions[0].leader)


meta = c.list_topics()
broker = meta.brokers[1]
print(broker.host, broker.port)