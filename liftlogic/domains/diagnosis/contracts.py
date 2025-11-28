"""
Diagnosis Contracts - Interfaces for diagnosis domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import FaultDiagnosis, SafetyRisk, MaintenanceTask, DiagnosisMode


@runtime_checkable
class DiagnosisAgent(Protocol):
    """Contract for fault diagnosis agent."""

    async def diagnose(
        self,
        fault_code: str,
        symptoms: list[str] | None = None,
        context: dict | None = None,
        mode: DiagnosisMode = DiagnosisMode.DETAILED,
    ) -> FaultDiagnosis:
        """
        Diagnose a fault code.

        Args:
            fault_code: The fault code to diagnose
            symptoms: Additional symptoms observed
            context: Additional context (manufacturer, model, etc.)
            mode: Diagnosis mode (quick, detailed, safety)

        Returns:
            Complete fault diagnosis
        """
        ...


@runtime_checkable
class SafetyAnalyzer(Protocol):
    """Contract for safety analysis agent."""

    async def analyze_risks(
        self,
        document_content: str,
        focus_areas: list[str] | None = None,
    ) -> list[SafetyRisk]:
        """
        Analyze safety risks in document content.

        Args:
            document_content: Technical document text
            focus_areas: Specific areas to focus on

        Returns:
            List of identified safety risks
        """
        ...

    async def audit_compliance(
        self,
        document_content: str,
        standards: list[str] | None = None,
    ) -> dict:
        """
        Audit document for compliance with safety standards.

        Args:
            document_content: Technical document text
            standards: Specific standards to check (e.g., EN81, ASME)

        Returns:
            Compliance audit results
        """
        ...


@runtime_checkable
class MaintenancePlanner(Protocol):
    """Contract for maintenance planning agent."""

    async def generate_schedule(
        self,
        components: list[dict],
        usage_data: dict | None = None,
    ) -> list[MaintenanceTask]:
        """
        Generate maintenance schedule for components.

        Args:
            components: List of component information
            usage_data: Optional usage/runtime data

        Returns:
            List of scheduled maintenance tasks
        """
        ...

    async def prioritize_tasks(
        self,
        tasks: list[MaintenanceTask],
        constraints: dict | None = None,
    ) -> list[MaintenanceTask]:
        """
        Prioritize maintenance tasks.

        Args:
            tasks: List of maintenance tasks
            constraints: Scheduling constraints (budget, downtime windows)

        Returns:
            Prioritized task list
        """
        ...
