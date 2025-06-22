#!/usr/bin/env python3
"""
Pytest configuration and fixtures for reconcile tests.
"""
import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_openai_api_key():
    """Automatically mock OpenAI API key for all tests."""
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-api-key'}):
        yield


@pytest.fixture
def sample_conflict_content():
    """Provide sample conflict content for tests."""
    return """line 1
<<<<<<< HEAD
def function():
    return "main branch"
=======
def function():
    return "feature branch"
>>>>>>> feature
line 2"""


@pytest.fixture
def sample_resolved_content():
    """Provide sample resolved content for tests."""
    return """line 1
def function():
    return "merged version"
line 2""" 