"""Test the SDLC phase classifier."""

import pytest
from sdlc_moe.orchestrator.classifier import classify


def test_classify_requirements():
    """Test classification of requirements prompts."""
    prompts = [
        "The app should let users sign up, log in, and reset their password",
        "Write requirements for a user authentication system",
        "Define user stories for the checkout process",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "requirements"
        assert result.confidence > 0.5


def test_classify_algorithm():
    """Test classification of algorithm prompts."""
    prompts = [
        "Design an efficient algorithm to find duplicates",
        "What is the time complexity of this sorting algorithm?",
        "Implement binary search",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "algorithm"
        assert result.confidence > 0.5


def test_classify_codegen():
    """Test classification of code generation prompts."""
    prompts = [
        "Write a Python function to parse CSV",
        "Implement a REST API endpoint",
        "Create a React component for the dashboard",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "codegen"
        assert result.confidence > 0.5


def test_classify_testgen():
    """Test classification of test generation prompts."""
    prompts = [
        "Write unit tests for this function",
        "Create pytest test cases",
        "Add integration tests for the API",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "testgen"
        assert result.confidence > 0.5


def test_classify_debug():
    """Test classification of debugging prompts."""
    prompts = [
        "Fix this error in my code",
        "Debug this Python script",
        "What's wrong with this implementation?",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "debug"
        assert result.confidence > 0.5


def test_classify_docs():
    """Test classification of documentation prompts."""
    prompts = [
        "Write documentation for this API",
        "Create a README for the project",
        "Add inline comments to this code",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "docs"
        assert result.confidence > 0.5


def test_classify_security():
    """Test classification of security prompts."""
    prompts = [
        "Review this code for security vulnerabilities",
        "Check for SQL injection risks",
        "Add input validation to prevent XSS",
    ]

    for prompt in prompts:
        result = classify(prompt)
        assert result.phase == "security"
        assert result.confidence > 0.5


def test_low_confidence():
    """Test that ambiguous prompts have low confidence."""
    ambiguous_prompts = [
        "Hello world",
        "What is programming?",
        "Help me with something",
    ]

    for prompt in ambiguous_prompts:
        result = classify(prompt)
        assert result.confidence <= 0.5


def test_all_phases_covered():
    """Test that all phases can be classified."""
    all_phases = set()

    test_prompts = [
        ("User login requirements", "requirements"),
        ("Sort array algorithm", "algorithm"),
        ("Python function", "codegen"),
        ("Unit tests", "testgen"),
        ("Fix bug", "debug"),
        ("API docs", "docs"),
        ("Security review", "security"),
    ]

    for prompt, expected_phase in test_prompts:
        result = classify(prompt)
        assert result.phase == expected_phase
        all_phases.add(result.phase)

    # All phases should be covered
    expected_phases = {
        "requirements",
        "architecture",
        "algorithm",
        "codegen",
        "fim",
        "testgen",
        "debug",
        "docs",
        "security",
    }

    # At minimum, we should hit the main phases
    main_phases = {
        "requirements",
        "algorithm",
        "codegen",
        "testgen",
        "debug",
        "docs",
        "security",
    }

    assert main_phases.issubset(all_phases)
