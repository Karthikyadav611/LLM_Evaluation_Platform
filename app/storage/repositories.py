from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.schemas import (
    EvaluationResult,
    ExperimentConfiguration,
    ExperimentSummary,
    QualityGateResult,
    VersionSummary,
)
from app.storage.models import (
    EvaluationResultRecord,
    ExperimentConfigurationRecord,
    ExperimentRecord,
    MetricSummaryRecord,
    QualityGateResultRecord,
    ReportFileRecord,
)


class ExperimentRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def save_experiment(self, summary: ExperimentSummary) -> None:
        with self.session_factory() as session:
            first_config = summary.configurations[0] if summary.configurations else None
            record = ExperimentRecord(
                experiment_id=summary.experiment_id,
                run_id=summary.run_id,
                mode=summary.mode,
                dataset_name=summary.dataset_name,
                dataset_hash=summary.dataset_hash,
                status=summary.status,
                generation_provider=first_config.provider if first_config else None,
                generation_model=first_config.model if first_config else None,
                judge_provider=first_config.judge_provider if first_config else None,
                judge_model=first_config.judge_model if first_config else None,
            )
            session.add(record)
            for configuration in summary.configurations:
                session.add(self._configuration_record(configuration))
            session.commit()

    def save_completed_run(
        self,
        *,
        summary: ExperimentSummary,
        results: list[EvaluationResult],
        metric_summaries: dict[str, VersionSummary],
        quality_gates: list[QualityGateResult],
        report_directory: str,
        report_files: list[str],
    ) -> None:
        with self.session_factory() as session:
            try:
                first_config = summary.configurations[0] if summary.configurations else None
                completed_at = datetime.now(UTC).replace(tzinfo=None)
                record = ExperimentRecord(
                    experiment_id=summary.experiment_id,
                    run_id=summary.run_id,
                    mode=summary.mode,
                    dataset_name=summary.dataset_name,
                    dataset_hash=summary.dataset_hash,
                    status=summary.status,
                    generation_provider=first_config.provider if first_config else None,
                    generation_model=first_config.model if first_config else None,
                    judge_provider=first_config.judge_provider if first_config else None,
                    judge_model=first_config.judge_model if first_config else None,
                    report_directory=report_directory,
                    started_at=completed_at,
                    completed_at=completed_at,
                )
                session.add(record)
                for configuration in summary.configurations:
                    session.add(self._configuration_record(configuration))
                for result in results:
                    session.add(self._result_record(result))
                for configuration_id, metric_summary in metric_summaries.items():
                    session.add(
                        MetricSummaryRecord(
                            experiment_id=summary.experiment_id,
                            run_id=summary.run_id,
                            configuration_id=configuration_id,
                            summary=metric_summary.model_dump(mode="json"),
                        )
                    )
                for gate in quality_gates:
                    session.add(
                        QualityGateResultRecord(
                            experiment_id=summary.experiment_id,
                            run_id=summary.run_id,
                            configuration_id=None,
                            name=gate.name,
                            actual=None if gate.actual is None else str(gate.actual),
                            threshold=None if gate.threshold is None else str(gate.threshold),
                            status=gate.status,
                            reason=gate.reason,
                        )
                    )
                for file_name in report_files:
                    session.add(
                        ReportFileRecord(
                            experiment_id=summary.experiment_id,
                            run_id=summary.run_id,
                            path=f"{report_directory}/{file_name}",
                            file_type=file_name.rsplit(".", 1)[-1],
                        )
                    )
                session.commit()
            except Exception:
                session.rollback()
                raise

    def save_results(self, results: list[EvaluationResult]) -> None:
        with self.session_factory() as session:
            for result in results:
                session.add(self._result_record(result))
            session.commit()

    def save_summary(self, experiment_id: str, run_id: str, configuration_id: str, summary: VersionSummary) -> None:
        with self.session_factory() as session:
            session.add(
                MetricSummaryRecord(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    configuration_id=configuration_id,
                    summary=summary.model_dump(mode="json"),
                )
            )
            session.commit()

    def save_quality_gates(
        self,
        experiment_id: str,
        run_id: str,
        gates: list[QualityGateResult],
        configuration_id: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            for gate in gates:
                session.add(
                    QualityGateResultRecord(
                        experiment_id=experiment_id,
                        run_id=run_id,
                        configuration_id=configuration_id,
                        name=gate.name,
                        actual=None if gate.actual is None else str(gate.actual),
                        threshold=None if gate.threshold is None else str(gate.threshold),
                        status=gate.status,
                        reason=gate.reason,
                    )
                )
            session.commit()

    def save_report_file(self, experiment_id: str, run_id: str, path: str, file_type: str) -> None:
        with self.session_factory() as session:
            session.add(
                ReportFileRecord(
                    experiment_id=experiment_id,
                    run_id=run_id,
                    path=path,
                    file_type=file_type,
                )
            )
            session.commit()

    def list_experiments(self, limit: int = 100) -> list[dict]:
        with self.session_factory() as session:
            rows = (
                session.query(ExperimentRecord)
                .order_by(ExperimentRecord.started_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "experiment_id": row.experiment_id,
                    "run_id": row.run_id,
                    "mode": row.mode,
                    "dataset_name": row.dataset_name,
                    "dataset_hash": row.dataset_hash,
                    "status": row.status,
                    "generation_provider": row.generation_provider,
                    "generation_model": row.generation_model,
                    "judge_provider": row.judge_provider,
                    "judge_model": row.judge_model,
                    "report_directory": row.report_directory,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                }
                for row in rows
            ]

    def get_experiment(self, experiment_id: str) -> dict | None:
        with self.session_factory() as session:
            row = (
                session.query(ExperimentRecord)
                .filter(ExperimentRecord.experiment_id == experiment_id)
                .one_or_none()
            )
            if row is None:
                return None
            return {
                "experiment_id": row.experiment_id,
                "run_id": row.run_id,
                "mode": row.mode,
                "dataset_name": row.dataset_name,
                "dataset_hash": row.dataset_hash,
                "status": row.status,
                "generation_provider": row.generation_provider,
                "generation_model": row.generation_model,
                "judge_provider": row.judge_provider,
                "judge_model": row.judge_model,
                "report_directory": row.report_directory,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }

    @staticmethod
    def _configuration_record(configuration: ExperimentConfiguration) -> ExperimentConfigurationRecord:
        return ExperimentConfigurationRecord(
            experiment_id=configuration.experiment_id,
            run_id=configuration.run_id,
            configuration_id=configuration.configuration_id,
            prompt_name=configuration.prompt_name,
            prompt_hash=configuration.prompt_hash,
            provider=configuration.provider,
            model=configuration.model,
            judge_provider=configuration.judge_provider,
            judge_model=configuration.judge_model,
            dataset_name=configuration.dataset_name,
            dataset_hash=configuration.dataset_hash,
            status=configuration.status,
        )

    @staticmethod
    def _result_record(result: EvaluationResult) -> EvaluationResultRecord:
        return EvaluationResultRecord(
            experiment_id=result.experiment_id or "",
            run_id=result.run_id or "",
            configuration_id=result.configuration_id or "",
            test_id=result.id,
            final_result=result.final_result,
            category=result.category,
            difficulty=result.difficulty,
            metrics={
                "semantic_similarity": result.semantic_similarity,
                "relevancy": result.relevancy,
                "faithfulness": result.faithfulness,
                "correctness": result.correctness,
                "safety_passed": result.safety_passed,
                "hallucination_detected": result.hallucination_detected,
                "latency_seconds": result.latency_seconds,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.total_tokens,
                "estimated_cost": result.estimated_cost,
            },
            actual_answer=result.actual_answer,
            failed_checks=result.failed_checks,
        )
