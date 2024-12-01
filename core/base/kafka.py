import asyncio
import json

from aiokafka import AIOKafkaProducer

from core.settings import settings


class AIOWebProducer(object):
    def __init__(self):
        self.__producer = AIOKafkaProducer(
            bootstrap_servers=f"{settings.KAFKA_HOST}:{settings.KAFKA_PORT}",
            value_serializer=lambda x: json.dumps(x).encode("utf8"),
        )
        self.__produce_topic = settings.PRODUCE_TOPIC

    async def start(self) -> None:
        await self.__producer.start()

    async def stop(self) -> None:
        await self.__producer.stop()

    async def send(self, value: bytes) -> None:
        await self.start()
        try:
            await self.__producer.send(
                topic=self.__produce_topic,
                value=value,
            )
        finally:
            await self.stop()


async def get_producer() -> AIOWebProducer:
    return AIOWebProducer()
