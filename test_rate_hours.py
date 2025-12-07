#!/usr/bin/env python3
"""Test rate and hours extraction"""

from llm_service import LLMService

llm = LLMService()

# Test cases for rate and hours
test_cases = [
    "50 per hour",
    "$50/hr",
    "minimum 50 an hour",
    "40 hours per week",
    "40 hours a week",
    "40 hours/week",
    "i want 50 per hour and 40 hours per week",
    "50$/hr and 30/week",
]

for test_input in test_cases:
    print(f"\n📝 Testing: '{test_input}'")
    extracted = llm._extract_with_regex(test_input, {})
    print(f"   Min Rate: {extracted.get('min_rate', 'None')}")
    print(f"   Max Hours: {extracted.get('max_hours', 'None')}")
