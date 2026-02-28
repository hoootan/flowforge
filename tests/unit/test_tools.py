"""Unit tests for tool definition and schema inference."""

from typing import Literal, Optional

import pytest
from flowforge.tools import Tool, _infer_parameters, _type_to_schema, tool


class TestToolDecorator:
    """Test the @tool decorator functionality."""

    def test_basic_tool_creation(self):
        """Test creating a basic tool with decorator."""

        @tool(name="test_func", description="Test function")
        def test_func(x: str) -> dict:
            """Test docstring."""
            return {"result": x}

        assert isinstance(test_func, Tool)
        assert test_func.name == "test_func"
        assert test_func.description == "Test function"
        assert callable(test_func.fn)
        assert test_func.requires_approval is False
        assert test_func.approval_timeout is None

    def test_async_tool(self):
        """Test creating async tool."""

        @tool(name="async_func", description="Async function")
        async def async_func(x: str) -> dict:
            """Async test."""
            return {"result": x}

        assert isinstance(async_func, Tool)
        assert async_func.name == "async_func"
        assert callable(async_func.fn)

    def test_tool_with_approval_required(self):
        """Test tool that requires human approval."""

        @tool(
            name="sensitive",
            description="Sensitive operation",
            requires_approval=True,
            approval_timeout="30m",
        )
        def sensitive(x: str) -> dict:
            return {"executed": x}

        assert sensitive.requires_approval is True
        assert sensitive.approval_timeout == "30m"

    def test_default_name_from_function(self):
        """Test that name defaults to function name."""

        @tool(description="Test function")
        def my_custom_function(x: str) -> dict:
            return {}

        assert my_custom_function.name == "my_custom_function"

    def test_default_description_from_docstring(self):
        """Test that description defaults to first line of docstring."""

        @tool(name="test")
        def my_function(x: str) -> dict:
            """This is the description line.

            More details here.
            """
            return {}

        assert my_function.description == "This is the description line."

    def test_empty_docstring_defaults(self):
        """Test tool with no docstring."""

        @tool(name="no_doc")
        def no_docstring(x: str) -> dict:
            return {}

        assert no_docstring.description == ""

    def test_tool_preserves_function(self):
        """Test that the original function is preserved."""

        def original_func(x: str, y: int) -> dict:
            return {"x": x, "y": y}

        tool_obj = tool(name="test", description="Test")(original_func)

        # The function should be stored
        assert tool_obj.fn is original_func


class TestParameterInference:
    """Test automatic parameter schema inference from function signatures."""

    def test_string_parameter(self):
        """Test string type inference."""

        @tool(name="test", description="Test")
        def test_func(name: str) -> dict:
            return {}

        assert test_func.parameters["type"] == "object"
        assert test_func.parameters["properties"]["name"]["type"] == "string"
        assert "name" in test_func.parameters["required"]

    def test_integer_parameter(self):
        """Test integer type inference."""

        @tool(name="test", description="Test")
        def test_func(count: int) -> dict:
            return {}

        assert test_func.parameters["properties"]["count"]["type"] == "integer"
        assert "count" in test_func.parameters["required"]

    def test_float_parameter(self):
        """Test float/number type inference."""

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
        """Test dict/object type inference."""

        @tool(name="test", description="Test")
        def test_func(data: dict) -> dict:
            return {}

        assert test_func.parameters["properties"]["data"]["type"] == "object"

    def test_optional_parameter_not_required(self):
        """Test that parameters with default values are not required."""

        @tool(name="test", description="Test")
        def test_func(required: str, optional: str = "default") -> dict:
            return {}

        params = test_func.parameters
        assert "required" in params["required"]
        assert "optional" not in params["required"]
        assert params["properties"]["optional"]["type"] == "string"

    def test_multiple_parameters(self):
        """Test function with multiple parameters of different types."""

        @tool(name="test", description="Test")
        def test_func(name: str, age: int, active: bool = True) -> dict:
            return {}

        props = test_func.parameters["properties"]
        required = test_func.parameters["required"]

        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"

        assert "name" in required
        assert "age" in required
        assert "active" not in required

    def test_no_parameters(self):
        """Test function with no parameters."""

        @tool(name="test", description="Test")
        def test_func() -> dict:
            return {}

        assert test_func.parameters["type"] == "object"
        assert test_func.parameters["properties"] == {}
        assert test_func.parameters.get("required", []) == []


class TestComplexTypes:
    """Test handling of complex type hints."""

    def test_list_with_type(self):
        """Test List[str] type annotation."""

        @tool(name="test", description="Test")
        def test_func(items: list[str]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["items"]
        assert param_schema["type"] == "array"
        assert param_schema["items"]["type"] == "string"

    def test_dict_with_types(self):
        """Test Dict[str, int] type annotation."""

        @tool(name="test", description="Test")
        def test_func(data: dict[str, int]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["data"]
        assert param_schema["type"] == "object"
        assert param_schema["additionalProperties"]["type"] == "integer"

    def test_optional_string(self):
        """Test Optional[str] type."""

        @tool(name="test", description="Test")
        def test_func(value: str | None) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["value"]
        # Optional should resolve to the underlying type (string)
        assert param_schema["type"] == "string"

    def test_literal_type(self):
        """Test Literal type for enum values."""

        @tool(name="test", description="Test")
        def test_func(priority: Literal["low", "medium", "high"]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["priority"]
        assert param_schema["type"] == "string"
        assert param_schema["enum"] == ["low", "medium", "high"]

    def test_literal_integer_enum(self):
        """Test Literal with integer values."""

        @tool(name="test", description="Test")
        def test_func(level: Literal[1, 2, 3]) -> dict:
            return {}

        param_schema = test_func.parameters["properties"]["level"]
        assert param_schema["type"] == "integer"
        assert param_schema["enum"] == [1, 2, 3]


class TestDocstringParsing:
    """Test extraction of parameter descriptions from docstrings."""

    def test_parameter_description_from_docstring(self):
        """Test that parameter descriptions are extracted from Args section."""

        @tool(name="test", description="Test")
        def test_func(name: str, age: int) -> dict:
            """
            Test function.

            Args:
                name: The person's name
                age: The person's age in years

            Returns:
                Result dictionary
            """
            return {}

        props = test_func.parameters["properties"]
        assert props["name"]["description"] == "The person's name"
        assert props["age"]["description"] == "The person's age in years"

    def test_multiline_parameter_description(self):
        """Test parameter descriptions that span multiple lines."""

        @tool(name="test", description="Test")
        def test_func(query: str) -> dict:
            """
            Search function.

            Args:
                query: The search query string to use for finding relevant results

            Returns:
                Search results
            """
            return {}

        desc = test_func.parameters["properties"]["query"]["description"]
        assert "search query" in desc.lower()

    def test_no_docstring_no_descriptions(self):
        """Test that missing docstring doesn't cause errors."""

        @tool(name="test", description="Test")
        def test_func(x: str, y: int) -> dict:
            return {}

        props = test_func.parameters["properties"]
        assert "description" not in props["x"]
        assert "description" not in props["y"]

    def test_docstring_without_args_section(self):
        """Test docstring that doesn't have Args section."""

        @tool(name="test", description="Test")
        def test_func(x: str) -> dict:
            """This is just a description without Args section."""
            return {}

        props = test_func.parameters["properties"]
        assert "description" not in props["x"]


class TestSchemaConversion:
    """Test conversion to provider-specific schemas."""

    def test_openai_schema_format(self):
        """Test conversion to OpenAI function calling format."""

        @tool(name="search", description="Search database")
        def search(query: str, limit: int = 10) -> dict:
            """
            Search function.

            Args:
                query: Search query string
                limit: Maximum results to return
            """
            return {}

        schema = search.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "search"
        assert schema["function"]["description"] == "Search database"
        assert "parameters" in schema["function"]

        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "query" in params["properties"]
        assert "limit" in params["properties"]
        assert params["properties"]["query"]["type"] == "string"
        assert params["properties"]["limit"]["type"] == "integer"
        assert "query" in params["required"]
        assert "limit" not in params["required"]

    def test_anthropic_schema_format(self):
        """Test conversion to Anthropic tool format."""

        @tool(name="search", description="Search database")
        def search(query: str, filters: dict = None) -> dict:
            """
            Search with filters.

            Args:
                query: Search query
                filters: Optional filters
            """
            return {}

        schema = search.to_anthropic_schema()

        assert schema["name"] == "search"
        assert schema["description"] == "Search database"
        assert "input_schema" in schema

        input_schema = schema["input_schema"]
        assert input_schema["type"] == "object"
        assert "query" in input_schema["properties"]
        assert "filters" in input_schema["properties"]
        assert input_schema["properties"]["query"]["type"] == "string"
        assert input_schema["properties"]["filters"]["type"] == "object"

    def test_schema_with_nested_types(self):
        """Test schema generation with nested complex types."""

        @tool(name="process", description="Process data")
        def process(items: list[dict[str, str]]) -> dict:
            return {}

        schema = process.to_openai_schema()

        items_schema = schema["function"]["parameters"]["properties"]["items"]
        assert items_schema["type"] == "array"
        assert items_schema["items"]["type"] == "object"
        assert items_schema["items"]["additionalProperties"]["type"] == "string"


class TestTypeToSchema:
    """Test the _type_to_schema helper function."""

    def test_basic_types(self):
        """Test basic Python type conversions."""
        assert _type_to_schema(str) == {"type": "string"}
        assert _type_to_schema(int) == {"type": "integer"}
        assert _type_to_schema(float) == {"type": "number"}
        assert _type_to_schema(bool) == {"type": "boolean"}
        assert _type_to_schema(list) == {"type": "array"}
        assert _type_to_schema(dict) == {"type": "object"}

    def test_none_type(self):
        """Test None type conversion."""
        assert _type_to_schema(type(None)) == {"type": "null"}

    def test_list_with_items(self):
        """Test List[int] conversion."""
        result = _type_to_schema(list[int])
        assert result["type"] == "array"
        assert result["items"]["type"] == "integer"

    def test_dict_with_value_type(self):
        """Test Dict[str, bool] conversion."""
        result = _type_to_schema(dict[str, bool])
        assert result["type"] == "object"
        assert result["additionalProperties"]["type"] == "boolean"

    def test_optional_type(self):
        """Test Optional[int] resolves to integer."""
        result = _type_to_schema(Optional[int])
        assert result["type"] == "integer"

    def test_literal_string_enum(self):
        """Test Literal['a', 'b', 'c'] conversion."""
        from typing import Literal
        result = _type_to_schema(Literal["a", "b", "c"])
        assert result["type"] == "string"
        assert result["enum"] == ["a", "b", "c"]


class TestInferParameters:
    """Test the _infer_parameters helper function."""

    def test_function_with_mixed_params(self):
        """Test parameter inference with required and optional params."""

        def test_func(a: str, b: int, c: bool = False):
            pass

        params = _infer_parameters(test_func)

        assert params["type"] == "object"
        assert len(params["properties"]) == 3
        assert len(params["required"]) == 2
        assert "a" in params["required"]
        assert "b" in params["required"]
        assert "c" not in params["required"]

    def test_function_with_no_annotations(self):
        """Test function without type hints defaults to string."""

        def test_func(x, y=10):
            pass

        params = _infer_parameters(test_func)

        # Without type hints, should still create properties
        assert "x" in params["properties"]
        assert "y" in params["properties"]

    def test_skip_self_and_cls(self):
        """Test that self and cls parameters are skipped."""

        def method(self, x: str, cls: str):
            pass

        params = _infer_parameters(method)

        # self should be skipped, cls in this case is a regular param
        assert "self" not in params["properties"]
        assert "x" in params["properties"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
