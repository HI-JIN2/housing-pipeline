import json
from aiokafka import AIOKafkaProducer

class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        import asyncio
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        for i in range(15):
            try:
                await self.producer.start()
                print(f"Kafka Producer started successfully on {self.bootstrap_servers}")
                return
            except Exception as e:
                print(f"Waiting for Kafka to be ready... ({i+1}/15) - {e}")
                await asyncio.sleep(3)
        raise RuntimeError(f"Could not connect to Kafka at {self.bootstrap_servers} after 15 retries")

    async def stop(self):
        if self.producer:
            await self.producer.stop()

    async def send_message(self, topic: str, message: dict):
        if not self.producer:
            raise RuntimeError("Producer has not been started")
        await self.producer.send_and_wait(topic, message)
