"""Regression tests for run/step response schemas accepting non-dict JSON values.

Background: GET /api/v1/runs/{id} previously 500'd whenever a step's output (or
run output, or trigger_data) was a JSON value other than an object — typically
a list. The runner persists whatever the user returns into JSONB columns, but
the response models were typed as `dict[str, Any] | None`, so Pydantic
rejected lists/scalars at serialize-time and crashed the entire endpoint.

These tests pin the contract: StepResponse and RunResponse must accept any
valid JSON value for their JSON-blob fields.
"""

import os
import tempfile

# `flowforge_server.api.__init__` imports `app.py`, which calls `create_app()`
# at module load and tries to mkdir settings.media_dir (default `/app/media`).
# Point it at a writable temp dir so importing schemas doesn't fail in CI.
os.environ.setdefault("FLOWFORGE_MEDIA_DIR", tempfile.mkdtemp(prefix="ff-test-media-"))

from datetime import datetime  # noqa: E402

import pytest  # noqa: E402
from flowforge_server.api.schemas.runs import RunResponse, StepResponse  # noqa: E402


def _step_kwargs(**overrides):
    base = dict(
        id="step-uuid",
        step_id="step-1",
        step_type="run",
        status="completed",
        attempt=1,
        max_attempts=3,
        created_at=datetime.utcnow(),
    )
    base.update(overrides)
    return base


def _run_kwargs(**overrides):
    base = dict(
        id="run-uuid",
        function_id="fn-uuid",
        status="completed",
        trigger_type="event",
        trigger_data={"event": {"name": "x"}},
        attempt=1,
        max_attempts=3,
        created_at=datetime.utcnow(),
    )
    base.update(overrides)
    return base


class TestStepResponseAcceptsAnyJson:
    @pytest.mark.parametrize(
        "value",
        [
            [{"is_new": False, "entity_id": "abc"}, {"is_new": True}],
            ["a", "b", "c"],
            "bare-string",
            42,
            3.14,
            True,
            None,
            {"nested": {"deep": [1, 2, 3]}},
        ],
        ids=["list-of-dicts", "list-of-strs", "string", "int", "float", "bool", "none", "nested-dict"],
    )
    def test_output_accepts_any_json(self, value):
        step = StepResponse(**_step_kwargs(output=value))
        assert step.output == value

    def test_input_accepts_list(self):
        step = StepResponse(**_step_kwargs(input=[1, 2, 3]))
        assert step.input == [1, 2, 3]

    def test_error_accepts_string(self):
        step = StepResponse(**_step_kwargs(error="something broke"))
        assert step.error == "something broke"

    def test_tool_input_output_accept_lists(self):
        step = StepResponse(
            **_step_kwargs(
                tool_input=[{"q": "a"}],
                tool_output=["result1", "result2"],
            )
        )
        assert step.tool_input == [{"q": "a"}]
        assert step.tool_output == ["result1", "result2"]


class TestRunResponseAcceptsAnyJson:
    def test_output_accepts_list(self):
        run = RunResponse(**_run_kwargs(output=[{"a": 1}, {"b": 2}]))
        assert run.output == [{"a": 1}, {"b": 2}]

    def test_output_accepts_scalar(self):
        run = RunResponse(**_run_kwargs(output="ok"))
        assert run.output == "ok"

    def test_error_accepts_list(self):
        run = RunResponse(**_run_kwargs(error=["e1", "e2"]))
        assert run.error == ["e1", "e2"]


class TestRunResponseRoundTripsListSteps:
    """The bug surfaced when serialising a Run with list-output steps. Verify
    the full nested model_dump() round-trips cleanly."""

    def test_run_with_list_output_step_round_trips(self):
        step = StepResponse(
            **_step_kwargs(output=[{"is_new": False, "entity_id": "x"}])
        )
        run = RunResponse(**_run_kwargs(steps=[step]))

        dumped = run.model_dump()
        assert dumped["steps"][0]["output"] == [{"is_new": False, "entity_id": "x"}]

        # Re-validate from dump — would fail under the old dict-only typing
        round_tripped = RunResponse.model_validate(dumped)
        assert round_tripped.steps[0].output == [{"is_new": False, "entity_id": "x"}]
