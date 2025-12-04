import sys
import os
import io
import types
import pytest
from unittest.mock import patch, mock_open, MagicMock
import contextlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pypgsvg.__init__ as mainmod

@pytest.fixture
def fake_sql():
    return "CREATE TABLE users (id SERIAL PRIMARY KEY);"

@contextlib.contextmanager
def run_main_with_args(args, mock_file_content=None, raise_file_error=None, parse_errors=None, gen_exception=None):
    """Helper to run main() with various mocks."""
    argv = ["prog"] + args
    with patch.object(sys, "argv", argv):
        # Mock open
        if raise_file_error:
            open_mock = patch("builtins.open", side_effect=raise_file_error)
        else:
            open_mock = patch("builtins.open", mock_open(read_data=mock_file_content or ""))
        with open_mock as mfile, \
             patch("pypgsvg.__init__.parse_sql_dump") as mparse, \
             patch("pypgsvg.__init__.generate_erd_with_graphviz") as mgen, \
             patch("webbrowser.open") as mweb:
            # parse_sql_dump returns (tables, fks, triggers, errors, views)
            mparse.return_value = ({"users": {"columns": []}}, [], {}, parse_errors or [], {})
            if gen_exception:
                mgen.side_effect = gen_exception
            yield mfile, mparse, mgen, mweb

def test_main_success(tmp_path, fake_sql):
    # Normal run, all options, --view, --show-standalone
    out = io.StringIO()
    with patch("sys.stdout", out):
        for extra in ([], ["--view"], ["--show-standalone", "true"], ["--view", "--show-standalone", "true"]):
            args = [str(tmp_path/"schema.sql"), "-o", str(tmp_path/"out")] + extra
            with run_main_with_args(args, mock_file_content=fake_sql) as (mfile, mparse, mgen, mweb):
                mainmod.main()
                assert mgen.called
                if "--view" in args:
                    assert mweb.called
                else:
                    assert not mweb.called
                assert "Successfully generated ERD" in out.getvalue()
                out.truncate(0)
                out.seek(0)


def test_main_file_not_found():
    out = io.StringIO()
    with patch("sys.stdout", out), \
         pytest.raises(SystemExit) as e:
        args = ["missing.sql"]
        with run_main_with_args(args, raise_file_error=FileNotFoundError()):
            mainmod.main()
    assert "Error: Input file not found" in out.getvalue()
    assert e.value.code == 1

def test_main_file_read_error():
    out = io.StringIO()
    with patch("sys.stdout", out), \
         pytest.raises(SystemExit) as e:
        args = ["bad.sql"]
        with run_main_with_args(args, raise_file_error=OSError("fail")):
            mainmod.main()
    assert "An error occurred while reading the file" in out.getvalue()
    assert e.value.code == 1

def test_main_parse_errors(tmp_path, fake_sql):
    out = io.StringIO()
    with patch("sys.stdout", out):
        args = [str(tmp_path/"schema.sql")]
        with run_main_with_args(args, mock_file_content=fake_sql, parse_errors=["bad stuff"]):
            mainmod.main()
    assert "--- PARSING ERRORS ---" in out.getvalue()
    assert "bad stuff" in out.getvalue()

def test_main_erd_generation_exception(tmp_path, fake_sql):
    out = io.StringIO()
    with patch("sys.stdout", out), \
         patch.object(mainmod.log, "exception") as mlogexc, \
         pytest.raises(SystemExit) as e:
        args = [str(tmp_path/"schema.sql")]
        with run_main_with_args(args, mock_file_content=fake_sql, gen_exception=RuntimeError("fail")):
            mainmod.main()
    assert "--- ERROR during ERD generation ---" in out.getvalue()
    assert "An unexpected error occurred" in out.getvalue()
    assert mlogexc.called
    assert e.value.code == 1

def test_main_mock_with_real_schema_dump(tmp_path):
    # Path to the real schema.dump file
    schema_dump_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "../../Samples/complex_schema.dump"))
    
    # Ensure the file exists
    assert os.path.exists(schema_dump_path), \
        f"Schema dump file not found at {schema_dump_path}"
    
    # Read the content of the schema.dump file
    with open(schema_dump_path, "r") as schema_file:
        schema_content = schema_file.read()
    
    # Prepare output and arguments
    out = io.StringIO()
    args = [schema_dump_path, "-o", str(tmp_path / "out")]
    
    # Run the test
    with patch("sys.stdout", out):
        with run_main_with_args(args, mock_file_content=schema_content) as \
                (mfile, mparse, mgen, mweb):
            mainmod.main()
            assert mgen.called
            assert "Successfully generated ERD" in out.getvalue()


def test_main_full_functionality_with_real_schema_dump(tmp_path):
    # Path to the real schema.dump file
    schema_dump_path = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "../../Samples/complex_schema.dump"))
    
    # Ensure the file exists
    assert os.path.exists(schema_dump_path), \
        f"Schema dump file not found at {schema_dump_path}"
    
    # Prepare output and arguments
    out = io.StringIO()
    args = [schema_dump_path, "-o", str(tmp_path / "out")]

    # Run the test as if it were executed from the terminal
    with patch("sys.stdout", out):
        with patch.object(sys, "argv", ["prog"] + args):
            mainmod.main()  # Run the actual main function
