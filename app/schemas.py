from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GoldenTestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    category: str
    difficulty: str = "medium"
    question: str
    context: str
    expected_answer: str
    must_include: list[str] = Field(default_factory=list)
    must_not_include: list[str] = Field(default_factory=list)
    expected_behavior: Literal["answer", "unanswerable", "clarify", "refuse"]
    metadata: dict[str, Any] = Field(default_factory=dict)

class GenerationResult(BaseModel):
    provider: str = ""
    model: str = ""
    answer: str
    latency_seconds: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    generation_error: str | None = None

    def model_post_init(self, __context: Any) -> None:
        if self.generation_error and not self.error_message:
            self.error_message = self.generation_error
        if self.error_message and not self.generation_error:
            self.generation_error = self.error_message

class JudgeResult(BaseModel):
    relevancy: float | None = None
    faithfulness: float | None = None
    correctness: float | None = None
    safety_passed: bool | None = None
    hallucination_detected: bool | None = None
    reason: str = ""
    judge_error: str | None = None
    error_type: str | None = None

class EvaluationResult(BaseModel):
    version: str
    id: str
    category: str
    difficulty: str
    question: str
    context: str
    expected_answer: str
    expected_behavior: str
    must_include: list[str]
    must_not_include: list[str]
    actual_answer: str
    keyword_passed: bool
    forbidden_terms_passed: bool
    behavior_passed: bool
    semantic_similarity: float | None = None
    relevancy: float | None
    faithfulness: float | None
    correctness: float | None
    safety_passed: bool | None
    hallucination_detected: bool | None
    judge_reason: str
    failed_checks: list[str]
    latency_seconds: float | None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None
    generation_error: str | None
    judge_error: str | None
    final_result: Literal["PASS", "FAIL", "ERROR"]
    experiment_id: str | None = None
    run_id: str | None = None
    configuration_id: str | None = None
    prompt_name: str | None = None
    prompt_hash: str | None = None
    provider: str | None = None
    model: str | None = None
    judge_provider: str | None = None
    judge_model: str | None = None
    dataset_name: str | None = None
    dataset_hash: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

class VersionSummary(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    pass_rate: float
    generation_error_count: int
    judge_error_count: int
    valid_generation_count: int
    valid_judge_count: int
    valid_quality_evaluation_count: int
    valid_evaluation_ratio: float
    average_semantic_similarity: float | None
    average_relevancy: float | None
    average_faithfulness: float | None
    average_correctness: float | None
    safety_pass_rate: float | None
    hallucination_rate: float | None
    average_latency: float | None
    median_latency: float | None
    p95_latency: float | None
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_estimated_cost: float | None = None
    average_estimated_cost: float | None = None

class QualityGateResult(BaseModel):
    name: str
    actual: Any
    threshold: Any
    status: Literal["PASS", "FAIL", "UNAVAILABLE"]
    reason: str

class ExperimentConfiguration(BaseModel):
    experiment_id: str
    run_id: str
    configuration_id: str
    prompt_name: str
    prompt_text: str
    prompt_hash: str
    provider: str
    model: str
    judge_provider: str
    judge_model: str
    dataset_name: str
    dataset_hash: str
    temperature: float = 0.0
    max_output_tokens: int = 1024
    started_at: str | None = None
    completed_at: str | None = None
    status: Literal["PENDING", "RUNNING", "PASS", "FAIL", "ERROR"] = "PENDING"

class ExperimentSummary(BaseModel):
    experiment_id: str
    run_id: str
    mode: Literal["prompt_comparison", "model_comparison", "matrix"]
    dataset_name: str
    dataset_hash: str
    started_at: str
    completed_at: str | None = None
    status: Literal["PASS", "FAIL", "ERROR", "RUNNING"] = "RUNNING"
    configurations: list[ExperimentConfiguration] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PipelineReport(BaseModel):
    generation_provider: str
    generation_model: str
    judge_provider: str
    judge_model: str
    timestamp: str
    thresholds: dict[str, Any]
    validity_checks: list[QualityGateResult]
    quality_gates: list[QualityGateResult]
    baseline_metrics: VersionSummary
    candidate_metrics: VersionSummary
    pipeline_status: Literal["PASS", "FAIL", "ERROR"]
    failed_candidate_ids: list[str] = Field(default_factory=list)
    fixed_test_ids: list[str] = Field(default_factory=list)
    regressed_test_ids: list[str] = Field(default_factory=list)
