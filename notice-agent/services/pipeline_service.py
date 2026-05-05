from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from models import (
    NoticeAttachment,
    NoticeItem,
    NoticePipelineStage,
    NoticeStageRecord,
    PipelineStageStatus,
)
from services.mongo_service import MongoService
from services.slack_service import SlackService


PIPELINE_STAGE_ORDER = [
    NoticePipelineStage.DISCOVERED,
    NoticePipelineStage.DETAIL_FETCHED,
    NoticePipelineStage.ATTACHMENTS_DOWNLOADED,
    NoticePipelineStage.PARSED,
    NoticePipelineStage.ENRICHED,
    NoticePipelineStage.PUBLISHED,
    NoticePipelineStage.NOTIFIED,
]


@dataclass
class NoticePipelineStore:
    notice: NoticeItem
    run_id: str
    should_notify: bool = False
    current_stage: NoticePipelineStage | None = None
    current_status: PipelineStageStatus | None = None
    last_error: str | None = None
    retry_count: int = 0
    attachments: list[NoticeAttachment] = field(default_factory=list)
    stage_results: list[dict[str, Any]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    notified: bool = False


@dataclass
class NoticePipelineResult:
    run_id: str
    notice_key: str
    current_stage: NoticePipelineStage | None
    current_status: PipelineStageStatus | None
    stage_results: list[dict[str, Any]]
    notified: bool


class NoticePipelineJob(ABC):
    stage: NoticePipelineStage

    @abstractmethod
    async def process(self, store: NoticePipelineStore) -> None:
        raise NotImplementedError


class DiscoverNoticeJob(NoticePipelineJob):
    stage = NoticePipelineStage.DISCOVERED

    async def process(self, store: NoticePipelineStore) -> None:
        store.context["discovered_notice"] = {
            "title": store.notice.title,
            "url": store.notice.url,
            "source": store.notice.source,
        }


class NotifySlackJob(NoticePipelineJob):
    stage = NoticePipelineStage.NOTIFIED

    def __init__(self, slack_service: SlackService):
        self.slack_service = slack_service

    async def process(self, store: NoticePipelineStore) -> None:
        if not store.should_notify:
            store.context["notification"] = {"reason": "bootstrap_or_notification_disabled"}
            return

        store.notified = await self.slack_service.send_new_notice(store.notice)
        store.context["notification"] = {"channel_delivery": "slack", "sent": store.notified}


class NoticePipelineRunner:
    def __init__(self, mongo_service: MongoService, jobs: list[NoticePipelineJob]):
        self.mongo_service = mongo_service
        self.jobs = jobs
        self.stage_order = [job.stage for job in jobs]
        self.allowed_transitions = {
            stage: self.stage_order[index + 1] if index + 1 < len(self.stage_order) else None
            for index, stage in enumerate(self.stage_order)
        }

    async def execute(self, store: NoticePipelineStore) -> NoticePipelineResult:
        active_stage: NoticePipelineStage | None = None

        try:
            for job in self.jobs:
                self._validate_transition(store.current_stage, job.stage)
                active_stage = job.stage
                await self._record_stage(store, job.stage, PipelineStageStatus.RUNNING)
                await job.process(store)
                await self._record_stage(
                    store,
                    job.stage,
                    self._resolve_success_status(store, job.stage),
                    metadata=self._build_stage_metadata(store, job.stage),
                )

            await self.mongo_service.finish_pipeline_run(
                run_id=store.run_id,
                status=PipelineStageStatus.SUCCEEDED,
            )
            return self._build_result(store)
        except Exception as exc:
            store.last_error = str(exc)
            store.retry_count += 1
            if active_stage is not None:
                await self._record_stage(
                    store,
                    active_stage,
                    PipelineStageStatus.FAILED,
                    error=store.last_error,
                )
            await self.mongo_service.finish_pipeline_run(
                run_id=store.run_id,
                status=PipelineStageStatus.FAILED,
                error=store.last_error,
            )
            raise

    def _validate_transition(
        self,
        previous_stage: NoticePipelineStage | None,
        next_stage: NoticePipelineStage,
    ) -> None:
        if previous_stage is None:
            return

        expected_next_stage = self.allowed_transitions.get(previous_stage)
        if expected_next_stage != next_stage:
            raise ValueError(
                f"Invalid pipeline transition: {previous_stage.value} -> {next_stage.value}"
            )

    def _resolve_success_status(
        self,
        store: NoticePipelineStore,
        stage: NoticePipelineStage,
    ) -> PipelineStageStatus:
        if stage == NoticePipelineStage.NOTIFIED and not store.should_notify:
            return PipelineStageStatus.SKIPPED
        if stage == NoticePipelineStage.NOTIFIED and not store.notified:
            return PipelineStageStatus.SKIPPED
        return PipelineStageStatus.SUCCEEDED

    def _build_stage_metadata(
        self,
        store: NoticePipelineStore,
        stage: NoticePipelineStage,
    ) -> dict[str, Any]:
        if stage == NoticePipelineStage.DISCOVERED:
            return dict(store.context.get("discovered_notice", {}))
        if stage == NoticePipelineStage.NOTIFIED:
            return dict(store.context.get("notification", {}))
        return {}

    async def _record_stage(
        self,
        store: NoticePipelineStore,
        stage: NoticePipelineStage,
        status: PipelineStageStatus,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        record = NoticeStageRecord(
            stage=stage,
            status=status,
            updated_at=self.mongo_service._now_iso(),
            error=error,
            metadata=metadata or {},
        )
        await self.mongo_service.record_notice_stage(
            notice=store.notice,
            run_id=store.run_id,
            record=record,
            retry_count=store.retry_count,
            attachments=store.attachments,
            last_error=error,
        )
        store.current_stage = stage
        store.current_status = status
        store.stage_results.append(record.model_dump(mode="json"))

    @staticmethod
    def _build_result(store: NoticePipelineStore) -> NoticePipelineResult:
        return NoticePipelineResult(
            run_id=store.run_id,
            notice_key=f"{store.notice.source}:{store.notice.external_id}",
            current_stage=store.current_stage,
            current_status=store.current_status,
            stage_results=store.stage_results,
            notified=store.notified,
        )


class NoticePipelineService:
    def __init__(self, mongo_service: MongoService, slack_service: SlackService):
        self.mongo_service = mongo_service
        self.slack_service = slack_service
        self.runner = NoticePipelineRunner(
            mongo_service=mongo_service,
            jobs=[
                DiscoverNoticeJob(),
                NotifySlackJob(slack_service),
            ],
        )

    async def process_discovered_notice(
        self,
        *,
        notice: NoticeItem,
        should_notify: bool,
    ) -> NoticePipelineResult:
        run_id = await self.mongo_service.start_pipeline_run(notice=notice, stages=PIPELINE_STAGE_ORDER)
        store = NoticePipelineStore(
            notice=notice,
            run_id=run_id,
            should_notify=should_notify,
        )
        return await self.runner.execute(store)
