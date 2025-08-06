# Python ERD Generator from Postgres Schema Dump File

`pypgsvg` is an open-source Python application that parses PostgreSQL schema SQL dump files and generates Directed Entity Relationship Diagrams (ERDs) using Graphviz. It includes features such as overview controls, edge highlighting, and introspection to display the SQL used to generate table nodes and edges, making it easier to debug PostgreSQL data structures.

---

In a past life I had been tasked with showing what the normalized postgresql database looks like for employers who do not want to pay for postgres tools that have the graphical tools. There are certainly usable free ones out there, and at the time required the installation of Java. So admittedly this started as an academic excersise. By no means is this even an alledgedly full throated tool, but takes most diagraph args.

Some versions of this saved me hours of time in explainations, now easier to share.



## Features
- Parse PostgreSQL dump files to extract table definitions and relationships.
- Generate interactive SVG ERDs with automatic color coding.
- Support for complex SQL structures, including foreign keys, constraints, and various data types.
- Table filtering to exclude temporary or utility tables.
- Accessible color palette with proper contrast for readability.
- Comprehensive test suite with >80% code coverage.

---

## Installation

1. Install `pypgsvg`:
   ```bash
   pip install pypgsvg
   ```

2. Ensure Graphviz is installed:
   - **macOS**: `brew install graphviz`
   - **Ubuntu/Debian**: `sudo apt-get install graphviz`
   - **Windows**: Download from [Graphviz.org](https://graphviz.org/download/).

---

## Usage
### Obtain or generate a PostgreSQL schema dump file
If you do not already schema dump file, you can generate one with pg_dump, or you can use the the [Sample](https://github.com/blackburnd/pypgsvg/blob/main/Samples/schema.dump).
pg_dump comes along with the postgresql install if you do not yet have a SQL schema dump file to process.
[PostgreSQL](https://www.postgresql.org/)

```bash
pg_dump -h 192.168.1.xxx --format=plain -d database -U postgres -s -O -F plain --disable-triggers --encoding=UTF8 -f schema.dump
```

### Command-Line Usage
Generate an ERD from your SQL dump file:

```bash
python -m src.pypgsvg Samples/schema.dump --output your_database_erd --rankdir TB --node-sep 4 --packmode graph --view
```

View the diagram immediately after generation:

```bash

python -m src.pypgsvg Samples/schema.dump --view

```

The following screenshots were generated from the dump file in the samples directory,
You can view the example_output_erd.svg via github, but for security reasons github restricts scripts runnning remotely.
If you want to have the intented interactive svg the file must be downloaded and opened in a browser from your local machine.

[[example_output_erd.svg](https://github.com/blackburnd/pypgsvg/blob/main/Samples/example_output_erd.svg)]



[![Demo Images](https://live.staticflickr.com/65535/54701842059_14340b4b77_b.jpg)](https://flic.kr/ps/46D1Th)


### Python API Usage

For programmatic use:
```
python
from src.pypgsvg import parse_sql_dump, generate_erd_with_graphviz

# Load SQL dump
with open("your_database_dump.sql", "r", encoding='utf-8') as file:
    sql_content = file.read()

# Parse tables and relationships
tables, foreign_keys, errors = parse_sql_dump(sql_content)

# Generate ERD
if not errors:
    generate_erd_with_graphviz(tables, foreign_keys, "database_diagram")
    print("ERD generated successfully!")
else:
    print("Parsing errors found:", errors)
```

---

## Components

### Metadata
Displays information about the generated SVG and the options used.
[![Metadata](https://live.staticflickr.com/65535/54701918384_2debb75e13_z.jpg)](https://flic.kr/ps/46D1Th)

### Overview
A minimap to quickly navigate larger SVG files.
[![Overview](https://live.staticflickr.com/65535/54702015980_bca2aedb3e_c.jpg)](https://flic.kr/ps/46D1Th)

### Selection SQL
Highlights SQL generation text for selected elements. Single-click inside the content area converts it to a text area for copy/paste.
[![SQL](https://live.staticflickr.com/65535/54701891288_096038eca2_b.jpg)](https://flic.kr/ps/46D1Th)

---

## Testing

Run the complete test suite:
```bash
PYTHONPATH=src python -m pytest tests/tests
```

Run specific test categories:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

Generate an HTML coverage report:
```bash
pytest --cov-report=html
open htmlcov/index.html
```

---

## Project Structure

```text
├── src/
│   └── create_graph.py          # Main application code
├── tests/
│   ├── conftest.py              # Test fixtures and configuration
│   ├── test_utils.py            # Tests for utility functions
│   ├── test_parser.py           # Tests for SQL parsing
│   ├── test_erd_generation.py   # Tests for ERD generation
│   └── test_integration.py      # Integration tests
├── requirements.txt             # Python dependencies
├── pyproject.toml               # pytest configuration
└── README.md                    # Documentation
```

---

## Configuration

### Table Exclusion
The application automatically excludes tables matching certain patterns:
- Views (`vw_`)
- Backup tables (`bk`)
- Temporary fix tables (`fix`)
- Duplicate tables (`dups`, `duplicates`)
- Match tables (`matches`)
- Version logs (`versionlog`)
- Old tables (`old`)
- Member data (`memberdata`)

### Color Palette
The ERD uses an accessible color palette with automatic contrast calculation for text readability following WCAG guidelines.

---

## Supported SQL Features

- `CREATE TABLE` statements with various column types.
- `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY`.
- Quoted identifiers and complex data types (e.g., `numeric`, `timestamp`, `jsonb`).
- Multiple constraint variations.

---

## Error Handling

The application includes comprehensive error handling for:
- Malformed SQL syntax.
- Missing table references in foreign keys.
- Unicode encoding issues.
- File reading errors.

---

## Contributing

1. Follow PEP 8 style guidelines.
2. Write tests for new functionality.
3. Maintain >90% test coverage.
4. Use type hints where appropriate.
5. Update documentation as needed.

---

## Dependencies

- `graphviz>=0.20.1` - For generating diagrams.
- `pytest>=7.4.0` - Testing framework.
- `pytest-cov>=4.1.0` - Coverage reporting.
- `pytest-mock>=3.11.0` - Mocking utilities.
