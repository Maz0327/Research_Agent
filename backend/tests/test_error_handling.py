"""
Tests for backend/utils/error_handling.py

Tests error message sanitization to prevent API key leakage.
"""
import pytest
from backend.utils.error_handling import sanitize_error_message, sanitize_dict_for_logging


class TestSanitizeErrorMessage:
    """Tests for error message sanitization."""

    def test_sanitizes_openai_api_key(self):
        """OpenAI API keys should be redacted."""
        error = Exception("Error with key sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234")
        result = sanitize_error_message(error)

        assert "sk-" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_perplexity_api_key(self):
        """Perplexity API keys should be redacted."""
        error = Exception("Error with key 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")
        result = sanitize_error_message(error)

        assert "pplx-" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_google_api_key(self):
        """Google API keys should be redacted."""
        error = Exception("Error with key AIzaAbcDefGhi123JklMno456PqrStu789VwxYz")
        result = sanitize_error_message(error)

        assert "AIza" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_bearer_tokens(self):
        """Bearer tokens should be redacted."""
        error = Exception("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
        result = sanitize_error_message(error)

        assert "Bearer" not in result or "eyJ" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_urls(self):
        """URLs should be redacted to prevent token leakage in query params."""
        error = Exception("Error accessing https://api.example.com/v1?key=secret123")
        result = sanitize_error_message(error)

        assert "https://" not in result
        assert "[URL_REDACTED]" in result

    def test_preserves_safe_messages(self):
        """Safe error messages should be preserved."""
        error = ValueError("Invalid input format")
        result = sanitize_error_message(error)

        assert "Invalid input format" in result

    def test_includes_exception_type(self):
        """Exception type should be included when requested."""
        error = ValueError("Test error")
        result = sanitize_error_message(error, include_type=True)

        assert "ValueError" in result
        assert "Test error" in result

    def test_excludes_exception_type_when_disabled(self):
        """Exception type should be excluded when requested."""
        error = ValueError("Test error")
        result = sanitize_error_message(error, include_type=False)

        assert "ValueError" not in result
        assert "Test error" in result


class TestSanitizeDictForLogging:
    """Tests for dictionary sanitization."""

    def test_sanitizes_api_key_field(self):
        """Fields named 'api_key' should be redacted."""
        data = {"api_key": "sk-secret123", "name": "test"}
        result = sanitize_dict_for_logging(data)

        assert result["api_key"] == "[REDACTED]"
        assert result["name"] == "test"

    def test_sanitizes_token_field(self):
        """Fields named 'token' should be redacted."""
        data = {"token": "secret_token", "value": 123}
        result = sanitize_dict_for_logging(data)

        assert result["token"] == "[REDACTED]"
        assert result["value"] == 123

    def test_sanitizes_password_field(self):
        """Fields named 'password' should be redacted."""
        data = {"password": "secret_password", "username": "user"}
        result = sanitize_dict_for_logging(data)

        assert result["password"] == "[REDACTED]"
        assert result["username"] == "user"

    def test_sanitizes_nested_dicts(self):
        """Nested dictionaries should also be sanitized."""
        data = {
            "config": {
                "api_key": "secret",
                "endpoint": "https://api.example.com"
            }
        }
        result = sanitize_dict_for_logging(data)

        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["endpoint"] == "https://api.example.com"

    def test_case_insensitive_matching(self):
        """Key matching should be case-insensitive."""
        data = {"API_KEY": "secret", "Token": "token", "PASSWORD": "pass"}
        result = sanitize_dict_for_logging(data)

        assert result["API_KEY"] == "[REDACTED]"
        assert result["Token"] == "[REDACTED]"
        assert result["PASSWORD"] == "[REDACTED]"

    def test_custom_sensitive_keys(self):
        """Custom sensitive keys should be supported."""
        data = {"custom_secret": "value", "other": "data"}
        result = sanitize_dict_for_logging(data, sensitive_keys=["custom_secret"])

        assert result["custom_secret"] == "[REDACTED]"
        assert result["other"] == "data"
