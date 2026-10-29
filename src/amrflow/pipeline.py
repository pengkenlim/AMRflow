"""Core AMR detection pipeline."""

from __future__ import annotations


class AMRFlowPipeline:
    """Simple placeholder pipeline implementation."""

    def __init__(self, *, input_dir: str | None = None) -> None:
        self.input_dir = input_dir

    def run(self) -> str:
        """Execute the pipeline."""
        if self.input_dir:
            return f"Pipeline initialized for {self.input_dir}"
        return "Pipeline initialized"
