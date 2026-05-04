from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, Iterable, TypeVar

StoreT = TypeVar("StoreT")
OutputT = TypeVar("OutputT")


class AsyncJob(ABC, Generic[StoreT]):
    @abstractmethod
    async def process(self, store: StoreT) -> None:
        raise NotImplementedError


class AsyncFinishJob(ABC, Generic[StoreT, OutputT]):
    @abstractmethod
    async def process(self, store: StoreT) -> OutputT:
        raise NotImplementedError


class AsyncPipeline(Generic[StoreT, OutputT]):
    def __init__(
        self,
        store: StoreT,
        init_job: AsyncJob[StoreT],
        jobs: Iterable[AsyncJob[StoreT]],
        finish_job: AsyncFinishJob[StoreT, OutputT],
    ):
        self.store = store
        self.init_job = init_job
        self.jobs = list(jobs)
        self.finish_job = finish_job

    async def execute(self) -> OutputT:
        await self.init_job.process(self.store)

        for job in self.jobs:
            await job.process(self.store)

        return await self.finish_job.process(self.store)
