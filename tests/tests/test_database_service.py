"""Tests for DatabaseService."""
import pytest
from unittest.mock import patch, MagicMock
from pypgsvg.database_service import DatabaseService


class TestFetchSchema:
    """Tests for fetch_schema method."""

    def test_fetch_schema_success(self):
        """Test successful schema fetch."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema dump')

            result = service.fetch_schema('localhost', '5432', 'testdb', 'testuser', 'password')

            assert result == '-- Schema dump'
            # Verify pg_dump was called correctly
            call_args = mock_run.call_args
            assert call_args[0][0][0] == 'pg_dump'
            assert '-h' in call_args[0][0]
            assert 'localhost' in call_args[0][0]

    def test_fetch_schema_with_cached_password(self):
        """Test schema fetch with cached password."""
        service = DatabaseService()
        service.cached_password = 'cached_pass'

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema')

            # Don't provide password, should use cached
            result = service.fetch_schema('localhost', '5432', 'testdb', 'testuser', None)

            assert result == '-- Schema'
            # Check that PGPASSWORD was set to cached password
            env = mock_run.call_args[1]['env']
            assert env['PGPASSWORD'] == 'cached_pass'

    def test_fetch_schema_empty_password(self):
        """Test schema fetch with empty password."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema')

            result = service.fetch_schema('localhost', '5432', 'testdb', 'testuser', '')

            assert result == '-- Schema'
            # Verify PGPASSWORD was not set (empty password)
            env = mock_run.call_args[1]['env']
            assert 'PGPASSWORD' not in env or env.get('PGPASSWORD') == ''

    def test_fetch_schema_none_password_becomes_empty(self):
        """Test that None password becomes empty string."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema')

            service.fetch_schema('localhost', '5432', 'testdb', 'testuser', None)

            # Check cached password was set to empty
            assert service.cached_password == ''

    def test_fetch_schema_caches_password(self):
        """Test that password gets cached."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema')

            service.fetch_schema('localhost', '5432', 'testdb', 'testuser', 'mypass')

            assert service.cached_password == 'mypass'

    def test_fetch_schema_subprocess_error(self):
        """Test schema fetch with subprocess error."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("subprocess.CalledProcessError")
            mock_run.side_effect.stderr = "Connection failed"

            # Manually raise CalledProcessError
            import subprocess
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd='pg_dump', stderr="Connection failed"
            )

            with pytest.raises(Exception) as exc_info:
                service.fetch_schema('localhost', '5432', 'testdb', 'testuser', 'password')

            assert "Database connection failed" in str(exc_info.value)

    def test_fetch_schema_pg_dump_not_found(self):
        """Test schema fetch when pg_dump command not found."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("pg_dump not found")

            with pytest.raises(Exception) as exc_info:
                service.fetch_schema('localhost', '5432', 'testdb', 'testuser', 'password')

            assert "pg_dump command not found" in str(exc_info.value)


class TestFetchViewColumns:
    """Tests for fetch_view_columns method."""

    def test_fetch_view_columns_success(self):
        """Test successful view columns fetch."""
        service = DatabaseService()

        psql_output = "view1|col1|integer|1\nview1|col2|text|2\nview2|col1|text|1\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=psql_output)

            result = service.fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            assert 'view1' in result
            assert 'view2' in result
            assert len(result['view1']) == 2
            assert result['view1'][0]['name'] == 'col1'
            assert result['view1'][0]['type'] == 'integer'
            assert result['view1'][1]['name'] == 'col2'

    def test_fetch_view_columns_empty_password(self):
        """Test fetch view columns with empty password."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='')

            result = service.fetch_view_columns('localhost', '5432', 'testdb', 'testuser', '')

            assert result == {}
            # Verify PGPASSWORD was not set
            env = mock_run.call_args[1]['env']
            assert 'PGPASSWORD' not in env or env.get('PGPASSWORD') == ''

    def test_fetch_view_columns_subprocess_error(self):
        """Test fetch view columns with subprocess error."""
        service = DatabaseService()

        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd='psql', stderr="Auth failed"
            )

            result = service.fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on error
            assert result == {}

    def test_fetch_view_columns_parse_error(self):
        """Test fetch view columns with parse error."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            # Return invalid data that will cause parsing exception
            mock_run.return_value = MagicMock(stdout="invalid|data\n")

            result = service.fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on parse error
            assert result == {}

    def test_fetch_view_columns_general_exception(self):
        """Test fetch view columns with general exception."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            # Raise a general exception (not CalledProcessError)
            mock_run.side_effect = RuntimeError("Unexpected error")

            result = service.fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on error
            assert result == {}


class TestTestConnection:
    """Tests for test_connection method."""

    def test_connection_success(self):
        """Test successful connection test."""
        service = DatabaseService()

        with patch.object(service, 'fetch_schema') as mock_fetch:
            mock_fetch.return_value = '-- Schema'

            result = service.test_connection('localhost', '5432', 'testdb', 'testuser', 'password')

            assert result['success'] is True
            assert result['message'] == 'Connection successful'

    def test_connection_failure(self):
        """Test failed connection test."""
        service = DatabaseService()

        with patch.object(service, 'fetch_schema') as mock_fetch:
            mock_fetch.side_effect = Exception("Connection error")

            result = service.test_connection('localhost', '5432', 'testdb', 'testuser', 'password')

            assert result['success'] is False
            assert 'Connection error' in result['message']


class TestListDatabases:
    """Tests for list_databases method."""

    def test_list_databases_success(self):
        """Test successful database listing."""
        service = DatabaseService()

        # Mock the two subprocess calls: one for list, one for each database table count
        with patch('subprocess.run') as mock_run:
            # First call returns database names
            # Second call returns table count for first database
            # Third call returns table count for second database
            mock_run.side_effect = [
                MagicMock(stdout='testdb1\ntestdb2\n'),
                MagicMock(stdout='5\n'),  # table count for testdb1
                MagicMock(stdout='10\n'),  # table count for testdb2
            ]

            result = service.list_databases('localhost', '5432', 'testuser', 'password')

            assert len(result) == 2
            assert result[0]['name'] == 'testdb1'
            assert result[0]['table_count'] == 5
            assert result[1]['name'] == 'testdb2'
            assert result[1]['table_count'] == 10

    def test_list_databases_empty_password(self):
        """Test database listing with empty password."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout='testdb\n'),
                MagicMock(stdout='3\n'),
            ]

            result = service.list_databases('localhost', '5432', 'testuser', '')

            assert len(result) == 1
            # Verify PGPASSWORD was not set
            env = mock_run.call_args_list[0][1]['env']
            assert 'PGPASSWORD' not in env or env.get('PGPASSWORD') == ''

    def test_list_databases_table_count_error(self):
        """Test database listing when table count query fails."""
        service = DatabaseService()

        import subprocess
        with patch('subprocess.run') as mock_run:
            # First call succeeds, second fails
            mock_run.side_effect = [
                MagicMock(stdout='testdb1\n'),
                subprocess.CalledProcessError(returncode=1, cmd='psql', stderr="Query failed"),
            ]

            result = service.list_databases('localhost', '5432', 'testuser', 'password')

            assert len(result) == 1
            assert result[0]['name'] == 'testdb1'
            assert result[0]['table_count'] == -1  # Unknown count

    def test_list_databases_table_count_timeout(self):
        """Test database listing when table count query times out."""
        service = DatabaseService()

        import subprocess
        with patch('subprocess.run') as mock_run:
            # First call succeeds, second times out
            mock_run.side_effect = [
                MagicMock(stdout='testdb1\n'),
                subprocess.TimeoutExpired(cmd='psql', timeout=5),
            ]

            result = service.list_databases('localhost', '5432', 'testuser', 'password')

            assert len(result) == 1
            assert result[0]['name'] == 'testdb1'
            assert result[0]['table_count'] == -1  # Unknown count

    def test_list_databases_table_count_value_error(self):
        """Test database listing when table count is not a valid integer."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            # First call succeeds, second returns non-integer
            mock_run.side_effect = [
                MagicMock(stdout='testdb1\n'),
                MagicMock(stdout='not_a_number\n'),
            ]

            result = service.list_databases('localhost', '5432', 'testuser', 'password')

            assert len(result) == 1
            assert result[0]['name'] == 'testdb1'
            assert result[0]['table_count'] == -1  # Unknown count

    def test_list_databases_query_failed(self):
        """Test database listing when initial query fails."""
        service = DatabaseService()

        import subprocess
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd='psql', stderr="Auth failed"
            )

            with pytest.raises(Exception) as exc_info:
                service.list_databases('localhost', '5432', 'testuser', 'password')

            assert "Failed to query databases" in str(exc_info.value)

    def test_list_databases_psql_not_found(self):
        """Test database listing when psql command not found."""
        service = DatabaseService()

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("psql not found")

            with pytest.raises(Exception) as exc_info:
                service.list_databases('localhost', '5432', 'testuser', 'password')

            assert "psql command not found" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
