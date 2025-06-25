"""
Test fixtures and sample data for create_graph tests.
"""
import pytest


@pytest.fixture
def sample_sql_dump():
    """Sample SQL dump for testing."""
    return """
    CREATE TABLE users (
        id integer NOT NULL,
        username character varying(50) NOT NULL,
        email character varying(100),
        created_at timestamp without time zone DEFAULT now()
    );
    
    CREATE TABLE posts (
        id integer NOT NULL,
        title character varying(200) NOT NULL,
        content text,
        user_id integer,
        created_at timestamp without time zone DEFAULT now()
    );
    
    CREATE TABLE comments (
        id integer NOT NULL,
        post_id integer,
        user_id integer,
        content text NOT NULL,
        created_at timestamp without time zone DEFAULT now()
    );
    
    ALTER TABLE ONLY posts
        ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
    
    ALTER TABLE ONLY comments
        ADD CONSTRAINT comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id);
    
    ALTER TABLE ONLY comments
        ADD CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);
    """


@pytest.fixture
def sample_tables():
    """Sample parsed tables for testing."""
    return {
        'users': {
            'lines': 'users\nid integer NOT NULL\nusername character varying(50) NOT NULL\nemail character varying(100)\ncreated_at timestamp without time zone DEFAULT now()',
            'columns': [
                {'name': 'id', 'type': 'integer', 'line': 'id integer NOT NULL'},
                {'name': 'username', 'type': 'character', 'line': 'username character varying(50) NOT NULL'},
                {'name': 'email', 'type': 'character', 'line': 'email character varying(100)'},
                {'name': 'created_at', 'type': 'timestamp', 'line': 'created_at timestamp without time zone DEFAULT now()'}
            ]
        },
        'posts': {
            'lines': 'posts\nid integer NOT NULL\ntitle character varying(200) NOT NULL\ncontent text\nuser_id integer\ncreated_at timestamp without time zone DEFAULT now()',
            'columns': [
                {'name': 'id', 'type': 'integer', 'line': 'id integer NOT NULL'},
                {'name': 'title', 'type': 'character', 'line': 'title character varying(200) NOT NULL'},
                {'name': 'content', 'type': 'text', 'line': 'content text'},
                {'name': 'user_id', 'type': 'integer', 'line': 'user_id integer'},
                {'name': 'created_at', 'type': 'timestamp', 'line': 'created_at timestamp without time zone DEFAULT now()'}
            ]
        }
    }


@pytest.fixture
def sample_foreign_keys():
    """Sample foreign keys for testing."""
    return [
        ('posts', 'user_id', 'users', 'id', 'ALTER TABLE ONLY posts ADD CONSTRAINT posts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);'),
        ('comments', 'post_id', 'posts', 'id', 'ALTER TABLE ONLY comments ADD CONSTRAINT comments_post_id_fkey FOREIGN KEY (post_id) REFERENCES posts(id);'),
        ('comments', 'user_id', 'users', 'id', 'ALTER TABLE ONLY comments ADD CONSTRAINT comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);')
    ]


@pytest.fixture
def color_test_cases():
    """Test cases for color contrast testing."""
    return [
        ("#000000", "white"),  # Black background -> white text
        ("#FFFFFF", "black"),  # White background -> black text
        ("#F94144", "white"),  # Red background -> white text
        ("#90BE6D", "black"),  # Light green background -> black text
        ("#264653", "white"),  # Dark green background -> white text
        ("#F9C74F", "black"),  # Yellow background -> black text
    ]


@pytest.fixture
def exclude_table_test_cases():
    """Test cases for table exclusion."""
    return [
        ("users", False),
        ("vw_users", True),
        ("posts_bk", True),
        ("fix_data", True),
        ("dups_table", True),
        ("duplicates_old", True),
        ("matches_temp", True),
        ("versionlog_2023", True),
        ("old_posts", True),
        ("ifma_data", True),
        ("memberdata_archive", True),
        ("normal_table", False),
    ]


@pytest.fixture
def malformed_sql_dumps():
    """Malformed SQL dumps for error testing."""
    return [
        # Missing semicolon
        """
        CREATE TABLE test (
            id integer NOT NULL
        )
        """,
        # Invalid foreign key reference
        """
        CREATE TABLE test (
            id integer NOT NULL
        );
        ALTER TABLE test ADD CONSTRAINT fk_test FOREIGN KEY (nonexistent_id) REFERENCES nonexistent_table(id);
        """,
        # Empty content
        "",
        # Only comments
        "-- This is just a comment\n/* Another comment */",
    ]
