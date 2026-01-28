"""Tests for tool definition and schema inference."""

import pytest
from typing import Literal, Optional

# Direct import to avoid dependency issues in tests
import sys
import importlib.util

spec = importlib.util.spec_from_file_location(
    "tools",
    "packages/flowforge-sdk/src/flowforge/tools.py"
)
tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools_module)

tool = tools_module.tool
Tool = tools_module.Tool


class TestToolDecorator:
    """Test the @tool decorator."""

    def test_basic_tool_creation(self):
        """Test creating a basic tool with decorator."""

        @tool(name="test_func", description="Test function")
        def test_func(x: str) -> dict:
            """Test docstring."""
            return {}

        assert isinstance(test_func, Tool)
        assert test_func.name == "test_func"
        assert test_func.description == "Test function"
        assert callable(test_func.fn)

    def test_async_tool(self):
        """Test creating async tool."""

        @tool(name="async_func", description="Async function")
        async def async_func(x: str) -> dict:
            """Async test."""
            return {}

        assert isinstance(async_func, Tool)
        assert async_func.name == "async_func"

    def test_tool_with_approval(self):
        """Test tool with approval settings."""

        @tool(
            name="sensitive",
            description="Sensitive operation",
            requires_approval=True,
            approval_timeout="30m",
        )
        def sensitive(x: str) -> dict:
            return {}

        assert sensitive.requires_approval is True
        assert sensitive.approval_timeout == "30m"

    def test_default_name_from_function(self):
        """Test that name defaults to function name."""

        @tool(description="Test")
        def my_function(x: str) -> dict:
            return {}

        assert my_function.name == "my_function"

    def test_default_description_from_docstring(self):
        """Test that description defaults to docstring."""

        @tool(name="test")
        def my_function(x: str) -> dict:
            """This is the description."""
            return {}

        assert my_function.description == "This is the description."


class TestParameterInference:
    """Test parameter schema inference."""

    def test_string_parameter(self):
        """Test string type inference."""

        @tool(name="test", description="Test")
        def test_func(name: str) -> dict:
            return {}

        assert test_func.parameters["properties"]["name"]["type"] == "string"
        assert "name" in test_func.parameters["required"]

    def test_integer_parameter(self):
        """Test integer type inference."""

        @tool(name="test", description="Test")
        def test_func(count: int) -> dict:
            return {}

        assert test_func.parameters["properties"]["count"]["type"] == "integer"

    def test_float_parameter(self):
        """Test float type inference."""

        @tool(name="test", description="Test")
        def test_func(value: float) -> dict:
            return {}

        assert test_func.parameters["properties"]["value"]["type"] == "number"

    def test_boolean_parameter(self):
        """Test boolean type inference."""

        @tool(name="test", description="Test")
        def test_func(flag: bool) -> dict:
            return {}

        assert test_func.parameters["properties"]["flag"]["type"] == "boolean"

    def test_list_parameter(self):
        """Test list type inference."""

        @tool(name="test", description="Test")
        def test_func(items: list) -> dict:
            return {}

        assert test_func.parameters["properties"]["items"]["type"] == "array"

    def test_dict_parameter(self):
        """Test dict type inference."""

        @tool(name="test", description="Test")
        def test_func(data: dict) -> dict:
            return {}

        assert test_func.parameters["properties"]["data"]["type"] == "object"

    def test_optional_parameter(self):
        """Test optional parameter (with default value)."""

        @tool(name="test", description="Test")
        def test_func(required: str, optional: str = "default") -> dict:
            return {}

        params = test_func.parameters
        assert "required" in params["required"]
        assert "optional" not in params["required"]
        assert params["properties"]["optional"]["type"] == "string"

    def test_literal_parameter(self):
        """Test Literal type for enums."""

        @tool(name="test", description="Test")
        def test_func(priority: Literal["low", "medium", "high"]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["priority"]
        assert param_schema["type"] == "string"
        assert param_schema["enum"] == ["low", "medium", "high"]

    def test_parameter_description_from_docstring(self):
        """Test parameter descriptions extracted from docstring."""

        @tool(name="test", description="Test")
        def test_func(name: str, age: int) -> dict:
            """
            Test function.

            Args:
                name: The person's name
                age: The person's age

            Returns:
                Result dict
            """
            return {}

        assert test_func.parameters["properties"]["name"]["description"] == "The person's name"
        assert test_func.parameters["properties"]["age"]["description"] == "The person's age"


class TestSchemaConversion:
    """Test schema conversion to provider formats."""

    def test_openai_schema_format(self):
        """Test conversion to OpenAI format."""

        @tool(name="search", description="Search database")
        def search(query: str, limit: int = 10) -> dict:
            """
            Search function.

            Args:
                query: Search query
                limit: Result limit
            """
            return {}

        schema = search.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"
        assert schema["function"]["description"] == "Search database"
        assert "parameters" in schema["function"]
        assert schema["function"]["parameters"]["type"] == "object"
        assert "query" in schema["function"]["parameters"]["properties"]
        assert "limit" in schema["function"]["parameters"]["properties"]

    def test_anthropic_schema_format(self):
        """Test conversion to Anthropic format."""

        @tool(name="search", description="Search database")
        def search(query: str) -> dict:
            return {}

        schema = search.to_anthropic_schema()

        assert schema["name"] == "search"
        assert schema["description"] == "Search database"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "query" in schema["input_schema"]["properties"]


class TestComplexTypes:
    """Test handling of complex type hints."""

    def test_list_with_type(self):
        """Test List[str] type."""
        from typing import List

        @tool(name="test", description="Test")
        def test_func(items: List[str]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["items"]
        assert param_schema["type"] == "array"
        assert param_schema["items"]["type"] == "string"

    def test_dict_with_types(self):
        """Test Dict[str, int] type."""
        from typing import Dict

        @tool(name="test", description="Test")
        def test_func(data: Dict[str, int]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["data"]
        assert param_schema["type"] == "object"
        assert param_schema["additionalProperties"]["type"] == "integer"

    def test_optional_type(self):
        """Test Optional[str] type."""

        @tool(name="test", description="Test")
        def test_func(value: Optional[str]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["value"]
        assert param_schema["type"] == "string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
