"""
Tests for Gemini Client adapter.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .client import GeminiAPIError, GeminiClient, RateLimitError
from .models import GeminiConfig, GeminiResponse, ThinkingLevel


@pytest.fixture
def mock_genai() -> Generator[MagicMock, None, None]:
    """Mock the google.generativeai module."""
    with patch("liftlogic.adapters.gemini.client.genai") as mock:
        # Mock GenerativeModel
        mock_model = MagicMock()
        mock_model.generate_content.return_value = MagicMock(
            text="Test response",
            usage_metadata=MagicMock(
                prompt_token_count=10,
                candidates_token_count=20,
            ),
        )
        mock.GenerativeModel.return_value = mock_model
        yield mock


@pytest.fixture
def client(mock_genai: MagicMock) -> GeminiClient:
    """Create a GeminiClient with mocked dependencies."""
    return GeminiClient()


@pytest.fixture
def custom_config() -> GeminiConfig:
    """Create a custom configuration for testing."""
    return GeminiConfig(
        model="gemini-2.0-flash",
        temperature=0.5,
        thinking_level=ThinkingLevel.MEDIUM,
        max_output_tokens=4096,
        timeout_seconds=120,
        rate_limit_rpm=30,
    )


# --- Model Tests ---


def test_gemini_config_defaults() -> None:
    """Test GeminiConfig default values."""
    config = GeminiConfig()
    assert config.model == "gemini-2.0-flash"
    assert config.temperature == 1.0
    assert config.thinking_level == ThinkingLevel.HIGH
    assert config.max_output_tokens == 8192
    assert config.timeout_seconds == 300
    assert config.rate_limit_rpm == 60


def test_gemini_config_custom() -> None:
    """Test GeminiConfig with custom values."""
    config = GeminiConfig(
        model="gemini-3-pro",
        temperature=0.7,
        thinking_level=ThinkingLevel.LOW,
    )
    assert config.model == "gemini-3-pro"
    assert config.temperature == 0.7
    assert config.thinking_level == ThinkingLevel.LOW


def test_gemini_config_temperature_validation() -> None:
    """Test GeminiConfig temperature must be between 0 and 2."""
    # Valid temperatures
    config = GeminiConfig(temperature=0.0)
    assert config.temperature == 0.0
    config = GeminiConfig(temperature=2.0)
    assert config.temperature == 2.0

    # Invalid temperatures
    with pytest.raises(ValueError):
        GeminiConfig(temperature=-0.1)
    with pytest.raises(ValueError):
        GeminiConfig(temperature=2.1)


def test_gemini_response_model() -> None:
    """Test GeminiResponse model."""
    response = GeminiResponse(
        text="Hello, world!",
        model="gemini-2.0-flash",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    assert response.text == "Hello, world!"
    assert response.model == "gemini-2.0-flash"
    assert response.prompt_tokens == 10
    assert response.completion_tokens == 5
    assert response.total_tokens == 15
    assert response.total_cost == 0.0  # Placeholder


def test_thinking_level_values() -> None:
    """Test ThinkingLevel enum values."""
    assert ThinkingLevel.NONE.value == "none"
    assert ThinkingLevel.LOW.value == "low"
    assert ThinkingLevel.MEDIUM.value == "medium"
    assert ThinkingLevel.HIGH.value == "high"


# --- Client Initialization Tests ---


def test_client_initialization_default_config(mock_genai: MagicMock) -> None:
    """Test GeminiClient initializes with default config."""
    client = GeminiClient()
    assert client.config.model == "gemini-2.0-flash"
    assert client.config.thinking_level == ThinkingLevel.HIGH


def test_client_initialization_custom_config(
    mock_genai: MagicMock, custom_config: GeminiConfig
) -> None:
    """Test GeminiClient initializes with custom config."""
    client = GeminiClient(config=custom_config)
    assert client.config.model == "gemini-2.0-flash"
    assert client.config.temperature == 0.5
    assert client.config.thinking_level == ThinkingLevel.MEDIUM


# --- Generate Tests ---


async def test_generate_basic(client: GeminiClient) -> None:
    """Test basic text generation."""
    response = await client.generate("Hello")
    assert isinstance(response, GeminiResponse)
    assert response.text == "Test response"


async def test_generate_with_system_instruction(client: GeminiClient) -> None:
    """Test generation with system instruction."""
    response = await client.generate(
        prompt="Hello",
        system_instruction="You are a helpful assistant.",
    )
    assert isinstance(response, GeminiResponse)


async def test_generate_json_valid(client: GeminiClient, mock_genai: MagicMock) -> None:
    """Test JSON generation with valid response."""
    # Mock JSON response
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(
        text='{"key": "value", "number": 42}'
    )

    # Force model recreation
    client._model = None

    result = await client.generate_json("Return JSON")
    assert result == {"key": "value", "number": 42}


async def test_generate_json_extracts_from_text(
    client: GeminiClient, mock_genai: MagicMock
) -> None:
    """Test JSON extraction from text with surrounding content."""
    # Mock response with JSON embedded in text
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(
        text='Here is the JSON: {"extracted": true} More text.'
    )

    client._model = None

    result = await client.generate_json("Extract JSON")
    assert result == {"extracted": True}


async def test_generate_json_invalid_raises(
    client: GeminiClient, mock_genai: MagicMock
) -> None:
    """Test JSON generation with invalid response raises error."""
    # Mock invalid JSON response
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(text="Not JSON at all")

    client._model = None

    with pytest.raises(Exception):  # JSONDecodeError
        await client.generate_json("Return JSON")


# --- Rate Limiting Tests ---


async def test_rate_limiting_allows_requests_within_limit(
    mock_genai: MagicMock,
) -> None:
    """Test that requests within rate limit are allowed."""
    config = GeminiConfig(rate_limit_rpm=5)
    client = GeminiClient(config=config)

    # Make 5 requests (at limit)
    for _ in range(5):
        await client.generate("Hello")

    # All should succeed without waiting


async def test_thinking_budget_values(client: GeminiClient) -> None:
    """Test thinking budget returns correct values for each level."""
    # Test each thinking level
    client.config = GeminiConfig(thinking_level=ThinkingLevel.NONE)
    assert client._thinking_budget() == 0

    client.config = GeminiConfig(thinking_level=ThinkingLevel.LOW)
    assert client._thinking_budget() == 1024

    client.config = GeminiConfig(thinking_level=ThinkingLevel.MEDIUM)
    assert client._thinking_budget() == 4096

    client.config = GeminiConfig(thinking_level=ThinkingLevel.HIGH)
    assert client._thinking_budget() == 16384


# --- Error Handling Tests ---


async def test_generate_handles_rate_limit_error(
    client: GeminiClient, mock_genai: MagicMock
) -> None:
    """Test that rate limit errors from API are handled."""
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.side_effect = Exception("429 Rate limit exceeded")

    client._model = None

    with pytest.raises(RateLimitError):
        await client.generate("Hello")


async def test_generate_handles_api_error(
    client: GeminiClient, mock_genai: MagicMock
) -> None:
    """Test that API errors are wrapped in GeminiAPIError after retries."""
    import tenacity

    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.side_effect = Exception("Connection failed")

    client._model = None

    # After retries are exhausted, tenacity wraps the error
    with pytest.raises(tenacity.RetryError):
        await client.generate("Hello")


def test_rate_limit_error() -> None:
    """Test RateLimitError exception."""
    error = RateLimitError("Too many requests")
    assert str(error) == "Too many requests"
    assert isinstance(error, Exception)


def test_gemini_api_error() -> None:
    """Test GeminiAPIError exception."""
    error = GeminiAPIError("API failure")
    assert str(error) == "API failure"
    assert isinstance(error, Exception)


# --- File Upload Tests ---


async def test_upload_file_not_found(client: GeminiClient) -> None:
    """Test upload_file raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        await client.upload_file("/nonexistent/file.pdf")


# --- Integration-style Tests (still mocked) ---


async def test_full_generate_workflow(
    mock_genai: MagicMock, custom_config: GeminiConfig
) -> None:
    """Test a complete generation workflow."""
    # Setup mock
    mock_model = mock_genai.GenerativeModel.return_value
    mock_model.generate_content.return_value = MagicMock(
        text="The answer is 42",
        usage_metadata=MagicMock(
            prompt_token_count=15,
            candidates_token_count=10,
        ),
    )

    # Create client and generate
    client = GeminiClient(config=custom_config)
    response = await client.generate(
        prompt="What is the meaning of life?",
        system_instruction="You are a philosopher.",
    )

    # Verify response
    assert response.text == "The answer is 42"
    assert response.model == "gemini-2.0-flash"
    assert response.prompt_tokens == 15
    assert response.completion_tokens == 10
