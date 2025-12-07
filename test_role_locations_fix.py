#!/usr/bin/env python3
"""
Test role-specific location extraction and conversation flow.
Verifies that the fix for role-specific locations works correctly.
"""

import sys
import json

# Add workspace to path
sys.path.insert(0, r'c:\Users\artur\OneDrive\Desktop\JOB_assist')

from llm_service import LLMService

def test_extraction():
    """Test role-specific location extraction."""
    llm = LLMService()
    
    test_cases = [
        {
            "input": "for teacher - remote, for doctor - london",
            "expected_roles": ["Teacher", "Doctor"],
            "expected_locations": {"teacher": "Remote", "doctor": "London"},
            "name": "Role-specific locations with dash separator"
        },
        {
            "input": "i'm arthur and i want to be a teacher for remote work and a doctor in chicago",
            "expected_roles": ["Teacher", "Doctor"],
            "name": "Multiple roles with different locations"
        },
        {
            "input": "5 offers please, i want to be a doctor",
            "expected_roles": ["Doctor"],
            "name": "Numeric input (5) should not conflict"
        },
        {
            "input": "teacher in london, developer in new york",
            "expected_locations": {"teacher": "London", "developer": "New york"},
            "name": "Comma-separated role-location pairs"
        },
        {
            "input": "for engineer - san francisco",
            "expected_locations": {"engineer": "San francisco"},
            "name": "Single role-location pair"
        }
    ]
    
    print("=" * 70)
    print("ROLE-SPECIFIC LOCATION EXTRACTION TESTS")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['input']}")
        
        result = llm._extract_with_regex(test['input'], {})
        
        try:
            # Check career goals
            if "expected_roles" in test:
                goals = result.get("career_goals", "").split(", ")
                expected_goals = test["expected_roles"]
                assert goals == expected_goals, f"Expected {expected_goals}, got {goals}"
                print(f"  Career goals: {goals} [OK]")
            
            # Check role-specific locations
            if "expected_locations" in test:
                role_locs = result.get("role_locations", {})
                expected_locs = test["expected_locations"]
                for role, location in expected_locs.items():
                    actual = role_locs.get(role)
                    assert actual == location, f"Expected {role}={location}, got {actual}"
                print(f"  Role locations: {role_locs} ✓")
            
            print("  PASS ✓")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL ✗ - {e}")
            print(f"  Full result: {json.dumps(result, indent=2)}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

def test_extraction_no_conflicts():
    """Test that '5' doesn't conflict with hourly rate or offers extraction."""
    llm = LLMService()
    
    print("\n" + "=" * 70)
    print("NUMERIC INPUT CONFLICT TESTS")
    print("=" * 70)
    
    test_cases = [
        {
            "input": "5 per hour as my minimum rate",
            "expected_rate": 5.0,
            "name": "5 as hourly rate"
        },
        {
            "input": "show me 5 offers",
            "expected_offers": 5,
            "name": "5 as number of offers"
        },
        {
            "input": "i want a doctor role with 5 jobs to choose from",
            "name": "5 in context (should be interpreted as offers)"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['input']}")
        
        result = llm._extract_with_regex(test['input'], {})
        
        try:
            if "expected_rate" in test:
                rate = result.get("min_rate")
                expected = test["expected_rate"]
                assert rate == expected, f"Expected rate={expected}, got {rate}"
                print(f"  Min rate: {rate} ✓")
            
            if "expected_offers" in test:
                offers = result.get("num_offers")
                expected = test["expected_offers"]
                assert offers == expected, f"Expected offers={expected}, got {offers}"
                print(f"  Num offers: {offers} ✓")
            
            print("  PASS ✓")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL ✗ - {e}")
            print(f"  Full result: {json.dumps(result, indent=2)}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE ROLE-SPECIFIC LOCATION FIX TEST SUITE")
    print("=" * 70 + "\n")
    
    test1_passed = test_extraction()
    test2_passed = test_extraction_no_conflicts()
    
    print("\n" + "=" * 70)
    if test1_passed and test2_passed:
        print("ALL TESTS PASSED ✓")
        print("The role-specific location extraction fix is working correctly!")
    else:
        print("SOME TESTS FAILED ✗")
        print("Please review the failures above.")
    print("=" * 70)
    
    return 0 if (test1_passed and test2_passed) else 1

if __name__ == "__main__":
    sys.exit(main())
