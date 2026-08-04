"""
Sanity tests for CockroachDB distributed vector matching.

Tests that _try_vector_match uses SQL-side cosine distance (<=>) against
the VECTOR(1536) column and index, not the old Python-side loop.

Run:
    cd backend
    python -m pytest tests/test_vector_match.py -v

These tests mock the database and Bedrock calls to verify the SQL
query structure and threshold logic without requiring live services.
"""

import asyncio
import math
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    return session


@pytest.fixture
def fake_embedding():
    """A deterministic 1536-dim embedding for testing."""
    # Normalized vector so cosine math is clean
    dim = 1536
    val = 1.0 / math.sqrt(dim)
    return [val] * dim


class TestGenerateEmbedding:
    """Tests for the generate_embedding function in bedrock_client."""

    def test_import_does_not_crash(self):
        """generate_embedding is importable (no more broken ImportError)."""
        from app.services.bedrock_client import generate_embedding
        assert callable(generate_embedding)

    @patch("boto3.client")
    def test_returns_1536_floats(self, mock_boto3_client):
        """generate_embedding returns a list of 1536 floats."""
        # Mock the bedrock-runtime client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client

        fake_result = [0.1] * 1536
        mock_body = MagicMock()
        mock_body.read.return_value = (
            b'{"embedding": ' + str(fake_result).encode() + b'}'
        )
        mock_client.invoke_model.return_value = {"body": mock_body}

        from app.services.bedrock_client import generate_embedding

        result = generate_embedding("Air Freight")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert all(isinstance(x, float) for x in result)
        mock_client.invoke_model.assert_called_once()


class TestTryVectorMatch:
    """Tests for _try_vector_match SQL-side vector search."""

    @pytest.mark.asyncio
    async def test_returns_none_when_no_embeddings(self, mock_session):
        """Returns None when there are no embeddings for the tenant."""
        # Mock: count query returns 0
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        mock_session.execute.return_value = count_result

        from app.services.charge_mapping import _try_vector_match

        result = await _try_vector_match(mock_session, "Air Freight", 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_sql_cosine_operator(self, mock_session, fake_embedding):
        """Verify the SQL query uses <=> operator (not Python-side cosine)."""
        # Mock: count query returns > 0
        count_mock = MagicMock()
        count_mock.scalar.return_value = 5

        # Mock: vector search returns a match
        vector_result = MagicMock()
        vector_result.fetchone.return_value = ("Air Freight", 0.95)

        # Mock: charge lookup returns a charge
        charge_mock = MagicMock()
        charge_obj = MagicMock()
        charge_obj.id = 42
        charge_obj.name = "Air Freight"
        charge_mock.scalar_one_or_none.return_value = charge_obj

        mock_session.execute.side_effect = [
            count_mock,      # count query
            vector_result,   # vector search query
            charge_mock,     # charge lookup
        ]

        from app.services.charge_mapping import _try_vector_match

        with patch(
            "app.services.bedrock_client.generate_embedding",
            return_value=fake_embedding,
        ):
            result = await _try_vector_match(mock_session, "Air Freight", 1)

        assert result is not None
        charge_id, charge_name, similarity = result
        assert charge_id == 42
        assert charge_name == "Air Freight"
        assert similarity == 0.95

        # Verify the vector search SQL was called (second call)
        sql_call = mock_session.execute.call_args_list[1]
        sql_text = str(sql_call[0][0])
        assert "<=>" in sql_text, (
            "Expected SQL to use <=> cosine distance operator"
        )
        assert "embedding_v" in sql_text, (
            "Expected SQL to reference the new embedding_v VECTOR column"
        )

    @pytest.mark.asyncio
    async def test_threshold_filters_low_similarity(
        self, mock_session, fake_embedding
    ):
        """Returns None when best match is below threshold."""
        count_mock = MagicMock()
        count_mock.scalar.return_value = 5

        vector_result = MagicMock()
        # Similarity 0.50 is below default threshold 0.85
        vector_result.fetchone.return_value = ("Some Charge", 0.50)

        mock_session.execute.side_effect = [count_mock, vector_result]

        from app.services.charge_mapping import _try_vector_match

        with patch(
            "app.services.bedrock_client.generate_embedding",
            return_value=fake_embedding,
        ):
            result = await _try_vector_match(mock_session, "Unknown Charge", 1)

        assert result is None


class TestMCPClient:
    """Tests for the MCP client integration."""

    def test_is_mcp_configured_false_by_default(self):
        """MCP is not configured when env vars are not set."""
        with patch.dict(
            "os.environ",
            {"CDB_MCP_CLUSTER_ID": "", "CDB_MCP_TOKEN": ""},
            clear=False,
        ):
            from app.services.mcp_client import is_mcp_configured
            assert is_mcp_configured() is False

    def test_is_mcp_configured_true_with_env(self):
        """MCP is configured when both cluster_id and token are set."""
        with patch.dict(
            "os.environ",
            {
                "CDB_MCP_CLUSTER_ID": "test-cluster",
                "CDB_MCP_TOKEN": "test-token",
            },
            clear=False,
        ):
            from app.services.mcp_client import is_mcp_configured
            assert is_mcp_configured() is True

    def test_create_mcp_tool_returns_none_when_not_configured(self):
        """create_mcp_tool returns None when MCP is not configured."""
        with patch.dict(
            "os.environ",
            {"CDB_MCP_CLUSTER_ID": "", "CDB_MCP_TOKEN": ""},
            clear=False,
        ):
            from app.services.mcp_client import create_mcp_tool
            tool = create_mcp_tool()
            assert tool is None

    def test_create_mcp_tool_returns_tool_when_configured(self):
        """create_mcp_tool returns a LangChain Tool when MCP is configured."""
        with patch.dict(
            "os.environ",
            {
                "CDB_MCP_CLUSTER_ID": "test-cluster",
                "CDB_MCP_TOKEN": "test-token",
            },
            clear=False,
        ):
            from app.services.mcp_client import create_mcp_tool
            tool = create_mcp_tool()
            assert tool is not None
            assert tool.name == "cockroachdb_mcp_query"
            assert "read-only" in tool.description.lower()
