#!/usr/bin/env python3
"""
Database service for pypgsvg - handles PostgreSQL database operations.

Extracted from server.py for better testability and separation of concerns.
"""
import os
import subprocess
from typing import Dict, Any, List, Tuple, Optional


class DatabaseService:
    """Service class for PostgreSQL database operations."""

    def __init__(self):
        """Initialize database service."""
        self.cached_password: Optional[str] = None

    def fetch_schema(self, host: str, port: str, database: str,
                    user: str, password: Optional[str] = None) -> str:
        """
        Fetch schema from PostgreSQL database using pg_dump.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password (optional for passwordless connections)

        Returns:
            SQL schema dump as string

        Raises:
            Exception: If database connection fails or pg_dump not found
        """
        # Use cached password if none provided
        if password is None and self.cached_password is not None:
            password = self.cached_password

        if password is None:
            password = ''  # Allow empty password for passwordless connections

        # Cache password for future use
        self.cached_password = password

        env = os.environ.copy()
        if password:  # Only set PGPASSWORD if password is not empty
            env['PGPASSWORD'] = password

        cmd = [
            'pg_dump',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-s',  # Schema only
            '--no-owner',
            '--no-privileges'
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"Database connection failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("pg_dump command not found. Please install PostgreSQL client tools.")

    def fetch_view_columns(self, host: str, port: str, database: str,
                          user: str, password: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch column information for all views in the database.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password

        Returns:
            Dict mapping view names to their column lists
        """
        env = os.environ.copy()
        if password:  # Only set PGPASSWORD if password is not empty
            env['PGPASSWORD'] = password

        # Query to get view columns
        query = """
        SELECT
            c.table_name as view_name,
            c.column_name,
            c.data_type,
            c.ordinal_position
        FROM information_schema.columns c
        JOIN information_schema.views v ON c.table_name = v.table_name
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position;
        """

        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-t',  # Tuples only
            '-A',  # Unaligned output
            '-F', '|',  # Field separator
            '-c', query
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            # Parse the output
            view_columns: Dict[str, List[Dict[str, Any]]] = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('|')
                    if len(parts) >= 4:
                        view_name = parts[0].strip()
                        column_name = parts[1].strip()
                        data_type = parts[2].strip()

                        if view_name not in view_columns:
                            view_columns[view_name] = []

                        view_columns[view_name].append({
                            'name': column_name,
                            'type': data_type,
                            'is_primary_key': False,
                            'is_foreign_key': False
                        })

            return view_columns
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not fetch view columns: {e.stderr}")
            return {}
        except Exception as e:
            print(f"Warning: Error parsing view columns: {e}")
            return {}

    def test_connection(self, host: str, port: str, database: str,
                       user: str, password: str) -> Dict[str, Any]:
        """
        Test database connection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password

        Returns:
            Dict with 'success' boolean and 'message' string
        """
        try:
            # Try to fetch schema (will fail if connection is bad)
            self.fetch_schema(host, port, database, user, password)
            return {
                "success": True,
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def list_databases(self, host: str, port: str, user: str,
                      password: str = '') -> List[Dict[str, Any]]:
        """
        List all databases on PostgreSQL server with table counts.

        Args:
            host: Database host
            port: Database port
            user: Database user
            password: Database password (optional)

        Returns:
            List of dicts with 'name' and 'table_count' keys

        Raises:
            Exception: If psql command fails or is not found
        """
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password

        # First get list of databases
        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', 'postgres',  # Connect to default postgres database
            '-t',  # Tuples only
            '-A',  # Unaligned output
            '-c', "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to query databases: {e.stderr}")
        except FileNotFoundError:
            raise Exception("psql command not found. Please install PostgreSQL client tools.")

        # Parse database list
        database_names = [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]

        # Get table count for each database
        databases = []
        for db_name in database_names:
            try:
                # Query table count for this database
                count_cmd = [
                    'psql',
                    '-h', host,
                    '-p', str(port),
                    '-U', user,
                    '-d', db_name,
                    '-t',
                    '-A',
                    '-c', "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema');"
                ]

                count_result = subprocess.run(
                    count_cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5  # Timeout after 5 seconds per database
                )

                table_count = int(count_result.stdout.strip() or 0)
                databases.append({
                    "name": db_name,
                    "table_count": table_count
                })
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
                # If we can't get table count, include database with unknown count
                databases.append({
                    "name": db_name,
                    "table_count": -1  # -1 indicates unknown
                })

        return databases
