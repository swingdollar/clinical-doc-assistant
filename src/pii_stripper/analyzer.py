"""
PII/PHI Stripper Module for HIPAA-Compliant Medical Documentation
Uses regex-based patterns to detect and redact personally identifiable information
while preserving medical terminology.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PIIDetectionResult:
    original_text: str
    stripped_text: str
    detected_phi: list


class PHIAnalyzer:
    PHI_PATTERNS = {
        "name": r"\b[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "dob": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "address": r"\b\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b",
        "mrn": r"\b(?:MRN|Medical Record)[:#]?\s*\d+\b",
        "dob_words": r"\b(?:born| Dob| DOB)\s+(?:on\s+)?\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    }

    REPLACEMENT_MAP = {
        "name": "[PATIENT_NAME]",
        "ssn": "[SSN_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "email": "[EMAIL_REDACTED]",
        "dob": "[DOB_REDACTED]",
        "address": "[ADDRESS_REDACTED]",
        "mrn": "[MRN_REDACTED]",
        "dob_words": "[DOB_REDACTED]",
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.compiled_patterns = {
            k: re.compile(v, re.IGNORECASE) for k, v in self.PHI_PATTERNS.items()
        }

    def detect_phi(self, text: str) -> list:
        detected = []
        for phi_type, pattern in self.compiled_patterns.items():
            matches = pattern.findall(text)
            for match in matches:
                detected.append({
                    "type": phi_type,
                    "value": match,
                    "position": pattern.search(text).span() if pattern.search(text) else None
                })
        return detected

    def strip_phi(self, text: str) -> str:
        result = text
        detected = self.detect_phi(text)
        
        for phi_info in detected:
            phi_type = phi_info["type"]
            value = phi_info["value"]
            replacement = self.REPLACEMENT_MAP.get(phi_type, "[REDACTED]")
            result = result.replace(value, replacement)
        
        return result

    def analyze(self, text: str) -> PIIDetectionResult:
        stripped = self.strip_phi(text)
        return PIIDetectionResult(
            original_text=text,
            stripped_text=stripped,
            detected_phi=self.detect_phi(text)
        )


def create_phi_analyzer(strict_mode: bool = True) -> PHIAnalyzer:
    return PHIAnalyzer(strict_mode=strict_mode)