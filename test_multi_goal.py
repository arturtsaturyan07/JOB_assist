#!/usr/bin/env python3
"""Test multi-goal extraction"""

from llm_service import LLMService

llm = LLMService()

# Test 1: Multiple roles with "and"
test_cases = [
    "english teacher and surgeon",
    "python developer and data scientist",
    "english teacher, surgeon and lawyer",
    "i want english teacher & surgeon",
    "surgeon or english teacher",
]

for test_input in test_cases:
    print(f"\n📝 Testing: '{test_input}'")
    extracted = llm._extract_with_regex(test_input, {})
    print(f"   Career Goals: {extracted.get('career_goals', 'None')}")
    print(f"   Skills: {extracted.get('skills', 'None')}")
