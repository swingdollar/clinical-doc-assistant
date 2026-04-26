"""
JSON Schema Validator for EHR Output
Validates LLM output conforms to SOAP note JSON schema for EHR integration.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Optional


SOAP_NOTE_SCHEMA = {
    "type": "object",
    "required": ["subjective", "objective", "assessment", "plan"],
    "properties": {
        "subjective": {
            "type": "object",
            "required": ["chief_complaint"],
            "properties": {
                "chief_complaint": {"type": "string"},
                "history_of_present_illness": {"type": "string"},
                "relevant_history": {"type": "string"},
                "medications": {"type": "array", "items": {"type": "string"}},
                "allergies": {"type": "array", "items": {"type": "string"}},
                "patient_reported_symptoms": {"type": "array", "items": {"type": "string"}}
            }
        },
        "objective": {
            "type": "object",
            "properties": {
                "vitals": {
                    "type": "object",
                    "properties": {
                        "blood_pressure": {"type": "string"},
                        "heart_rate": {"type": "string"},
                        "temperature": {"type": "string"},
                        "respiratory_rate": {"type": "string"},
                        "oxygen_saturation": {"type": "string"}
                    }
                },
                "physical_examination": {"type": "array", "items": {"type": "string"}},
                "observed_symptoms": {"type": "array", "items": {"type": "string"}},
                "lab_results": {"type": "array", "items": {"type": "string"}}
            }
        },
        "assessment": {
            "type": "object",
            "required": ["clinical_impression"],
            "properties": {
                "primary_diagnosis": {"type": "string"},
                "differential_diagnoses": {"type": "array", "items": {"type": "string"}},
                "clinical_impression": {"type": "string"}
            }
        },
        "plan": {
            "type": "object",
            "properties": {
                "treatment": {"type": "array", "items": {"type": "string"}},
                "medications": {"type": "string"},
                "follow_up": {"type": "string"},
                "referrals": {"type": "array", "items": {"type": "string"}},
                "patient_education": {"type": "array", "items": {"type": "string"}},
                "additional_tests": {"type": "string"}
            }
        }
    }
}


@dataclass
class ValidationResult:
    valid: bool
    errors: list
    warnings: list
    validated_data: Optional[dict] = None


class SOAPNoteValidator:
    PHI_PATTERNS = [
        r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    ]

    def __init__(self):
        self.schema = SOAP_NOTE_SCHEMA

    def validate(self, data: Any) -> ValidationResult:
        """Validate SOAP note data against schema."""
        errors = []
        warnings = []

        if not data:
            return ValidationResult(
                valid=False,
                errors=["Empty response received"],
                warnings=[]
            )

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                return ValidationResult(
                    valid=False,
                    errors=[f"Invalid JSON: {str(e)}"],
                    warnings=[]
                )

        if not isinstance(data, dict):
            return ValidationResult(
                valid=False,
                errors=["Response must be a JSON object"],
                warnings=[]
            )

        errors.extend(self._validate_structure(data))
        errors.extend(self._validate_required_fields(data))
        warnings.extend(self._check_phi_leaks(data))

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_data=data if len(errors) == 0 else None
        )

    def _validate_structure(self, data: dict) -> list:
        """Validate top-level structure."""
        errors = []
        required_sections = ["subjective", "objective", "assessment", "plan"]

        for section in required_sections:
            if section not in data:
                errors.append(f"Missing required section: {section}")
            elif not isinstance(data[section], dict):
                errors.append(f"Section '{section}' must be an object")

        return errors

    def _validate_required_fields(self, data: dict) -> list:
        """Validate required fields within sections."""
        errors = []

        if "subjective" in data:
            if "chief_complaint" not in data["subjective"]:
                errors.append("Missing required field: subjective.chief_complaint")

        if "assessment" in data:
            if "clinical_impression" not in data["assessment"]:
                errors.append("Missing required field: assessment.clinical_impression")

        return errors

    def _check_phi_leaks(self, data: dict) -> list:
        """Check for potential PHI leaks in the output."""
        warnings = []
        text = json.dumps(data)

        for pattern in self.PHI_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    if len(match) > 4 and "@" not in match:
                        warnings.append(f"Potential PHI detected: {match[:20]}...")

        return warnings

    def sanitize_output(self, data: dict) -> dict:
        """Attempt to sanitize and fix common issues."""
        sanitized = {}

        for section in ["subjective", "objective", "assessment", "plan"]:
            if section in data:
                sanitized[section] = data[section]
            else:
                sanitized[section] = {}

        return sanitized


def create_validator() -> SOAPNoteValidator:
    return SOAPNoteValidator()