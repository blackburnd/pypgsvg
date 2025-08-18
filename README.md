# pypgsvg - Lightweight PostgreSQL ERD Generator

`pypgsvg` is a **lightweight** Python tool that generates a JS/CSS/SVG interactive Entity Relationship Diagrams (ERDs) from PostgreSQL schema dump files. With **only Graphviz as a dependency**, manually run or place in CI/CD pipelines, fast rapid deployment verification scenarios.


## �️ Screenshots & Examples

### 📊 Complete ERD Example
![Complex Schema ERD](Samples/complex_schema.png)
*Example of a complex database schema with multiple relationships and interactive features*

### 🎬 Interactive Features Demo
![Interactive Animation](https://live.staticflickr.com/65535/54725569515_1a265e1695_o.gif)
*Live demonstration of drag, resize, and navigation features*

### 🗺️ Miniature Overview Navigation
![Miniature Overview](Samples/miniature.png)
*Interactive minimap for navigating large schemas with viewport indicator*

### 📋 Metadata Information Panel
![Metadata Panel](Samples/metadata.png)
*Comprehensive schema statistics and generation parameters*

### 🎯 Selection & Details Panel
![Selection Panel](Samples/selection.png)
*View detailed SQL for selected tables, foreign keys, and triggers*

### 📈 Basic Schema Example
![Basic Example](Samples/example.png)
*Simple schema showing core functionality and clean output*

## �🚀 Enterprise Features

- **Zero-dependency Python tool** (except Graphviz)
- **Interactive SVG output** with navigation and selection tools
- **Scriptable and automatable** for enterprise workflows
- **Quick deployment** - install and run in seconds
- **Self-contained** - no database connections required
- **Cross-platform** support (Windows, macOS, Linux)

---

## ✨ Interactive Features

### 🎯 Selection & Navigation Tools
- **Smart table/edge selection** - Click any element to view detailed SQL
- **Miniature overview** with viewport indicator for large schemas
- **Drag & drop containers** - Reposition windows anywhere
- **Resizable panels** - Customize your workspace layout

### 📋 Copy & Export Tools
- **One-click copy** - Copy table definitions, foreign keys, or trigger SQL
- **Download selection details** - Export selected elements as formatted text
- **Emoji-free output** - Enterprise-friendly plain text exports

### 🖱️ Interactive Controls
- **Minimize/maximize** any panel to focus on your work
- **Close buttons** for distraction-free viewing
- **Pan and zoom** with mouse or miniature navigator
- **Keyboard shortcuts** (ESC/R to reset view)

### 🎨 Visual Enhancements
- **Color-coded tables** with accessible contrast
- **Hover effects** for better element identification
- **Professional styling** suitable for documentation and presentations

---

## 📦 Installation

**Lightweight setup - only 2 steps:**

1. Install `pypgsvg`:
   ```bash
   pip install pypgsvg
   ```

2. Install Graphviz (the only external dependency):
   - **macOS**: `brew install graphviz`
   - **Ubuntu/Debian**: `sudo apt-get install graphviz`
   - **CentOS/RHEL**: `sudo yum install graphviz`
   - **Windows**: Download from [Graphviz.org](https://graphviz.org/download/)

**That's it!** Ready for enterprise deployment.

---

## 🛠️ Enterprise Usage

### Quick Start - Schema Analysis
```bash
# Generate interactive ERD from schema dump
pypgsvg schema.dump --output database_erd --view

# Enterprise automation (CI/CD ready)
pypgsvg Samples/complex_schema.dump --output Samples/complex_schema --rankdir LR --node-sep 4
```

### Advanced Enterprise Options
```bash
# Large schema optimization
pypgsvg Samples/complex_schema.dump --output Samples/complex_schema --rankdir LR --node-sep 4
source venv/bin/activate && python -m src.pypgsvg Samples/complex_schema.dump --node-shape=ellipse --show-standalone=false --output=./Samples/complex_schema --rankdir LR --node-sep 2 --packmode


# Custom layout for documentation
pypgsvg schema.dump --rankdir LR --fontsize 20 --node-fontsize 16 --output presentation_erd
```

## Usage
### Get Your PostgreSQL Schema
If you don't have a schema dump, generate one with `pg_dump`:

```bash
# Standard schema export (most common)
pg_dump -h your-host -d database -U username -s --no-owner --no-privileges > schema.dump

# Comprehensive export with triggers and functions
pg_dump -h your-host -d database -U username -s -O -F plain --disable-triggers --encoding=UTF8 > schema.dump
```

Or use our [sample schema](https://github.com/blackburnd/pypgsvg/blob/main/Samples/complex_schema.dump) for testing.

### Interactive ERD Generation

**Basic usage:**
```bash
pypgsvg schema.dump --output my_database_erd --view
```

**Enterprise production:**
```bash
pypgsvg schema.dump \
  --output docs/database_architecture \
  --rankdir TB \
  --node-sep 4 \
  --packmode graph \
  --rank-sep 3 \
  --hide-standalone
```

**The generated SVG includes:**
- 🖱️ **Interactive selection** - Click tables/edges to view SQL details
- 📱 **Miniature navigator** - Overview panel for large schemas  
- 📋 **Copy/download tools** - Export selected elements
- 🎨 **Resizable panels** - Customize your workspace
- ⌨️ **Keyboard shortcuts** - ESC/R to reset view

> **Note:** For full interactivity, open the SVG file locally in your browser. GitHub restricts JavaScript for security.

### 🎬 Quick Demo

[[🎯 View Interactive Example](https://github.com/blackburnd/pypgsvg/blob/main/Samples/complex_schema.svg)] 

[![https://live.staticflickr.com/65535/54725569515_1a265e1695.jpghttps://flic.kr/ps/46D1Th)

**Try it yourself:**
```bash
# Download sample and generate interactive ERD
wget https://github.com/blackburnd/pypgsvg/raw/main/Samples/complex_schema.dump
pypgsvg schema.dump --output demo_erd --view
```

### Scriptable API

Perfect for automation and enterprise workflows:

```python
from pypgsvg import parse_sql_dump, generate_erd_with_graphviz

# Parse schema dump
with open("schema.dump", "r", encoding='utf-8') as file:
    sql_content = file.read()

# Extract database structure  
tables, foreign_keys, triggers, errors = parse_sql_dump(sql_content)

# Generate interactive ERD
if not errors:
    generate_erd_with_graphviz(
        tables=tables,
        foreign_keys=foreign_keys, 
        output_file="enterprise_diagram",
        rankdir='TB',
        packmode='graph'
    )
    print("✅ Enterprise ERD generated successfully!")
else:
    print("⚠️ Parsing errors:", errors)
```

---

## ⚙️ Complete Command-Line Reference

### Core Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `input_file` | **Required** | - | Path to the PostgreSQL dump file |
| `-o, --output` | String | `schema_erd` | Output file name (without extension) |
| `--view` | Flag | `false` | Open the generated SVG in a browser |
| `--show-standalone` | String | `true` | Show/hide tables with no foreign key relationships |

### Layout & Positioning

| Argument | Type | Default | Options | Description |
|----------|------|---------|---------|-------------|
| `--packmode` | String | `array` | `array`, `cluster`, `graph` | **Graphviz packmode** - Controls how components are packed together |
| `--rankdir` | String | `TB` | `TB`, `LR`, `BT`, `RL` | **Graphviz rankdir** - Graph direction (Top-Bottom, Left-Right, etc.) |
| `--esep` | String | `8` | Any number | **Graphviz esep** - Edge separation distance in points |
| `--node-sep` | String | `0.5` | Any number | **Graphviz nodesep** - Minimum distance between nodes |
| `--rank-sep` | String | `1.2` | Any number | **Graphviz ranksep** - Distance between ranks/levels |

### Typography & Styling

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--fontname` | String | `Arial` | Font family for all text elements |
| `--fontsize` | Integer | `18` | Font size for graph title/labels |
| `--node-fontsize` | Integer | `14` | Font size for table names and column text |
| `--edge-fontsize` | Integer | `12` | Font size for relationship labels |
| `--node-style` | String | `rounded,filled` | **Graphviz node style** (e.g., `filled`, `rounded,filled`) |
| `--node-shape` | String | `rect` | **Graphviz node shape** (e.g., `rect`, `ellipse`, `box`) |

### Color & Visual Enhancement

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--saturate` | Float | `1.8` | Color saturation multiplier for table backgrounds |
| `--brightness` | Float | `1.0` | Brightness adjustment for table colors |

### Usage Examples by Scenario

#### 🚀 Quick Development Schema
```bash
# Fast development with browser preview
pypgsvg schema.dump --view
```

#### 📊 Large Enterprise Schema
```bash
# Optimized for large schemas with many tables
pypgsvg schema.dump \
  --output enterprise_erd \
  --packmode graph \
  --rankdir TB \
  --esep 12 \
  --rank-sep 2.5 \
  --hide-standalone false
```

#### 📋 Documentation & Presentations
```bash
# Clean layout for documentation
pypgsvg schema.dump \
  --output docs/database_diagram \
  --rankdir LR \
  --fontname "Arial" \
  --fontsize 20 \
  --node-fontsize 16 \
  --edge-fontsize 14 \
  --node-style "rounded,filled"
```

#### 🎨 Custom Styling
```bash
# Custom colors and typography
pypgsvg schema.dump \
  --output styled_erd \
  --fontname "Helvetica" \
  --saturate 2.2 \
  --brightness 1.1 \
  --node-style "filled" \
  --node-shape "box"
```

#### 🏗️ Wide Schema Layout
```bash
# Horizontal layout for wide displays
pypgsvg schema.dump \
  --rankdir LR \
  --node-sep 3 \
  --rank-sep 2 \
  --packmode cluster \
  --esep 10
```

### Understanding Graphviz Parameters

#### Packmode Options
- **`array`** (default): Tables arranged in a regular grid pattern
- **`cluster`**: Groups related tables together spatially  
- **`graph`**: Optimizes overall graph layout, best for complex schemas

#### Rankdir Options
- **`TB`** (Top-Bottom): Traditional vertical flow, tables flow downward
- **`LR`** (Left-Right): Horizontal flow, good for wide displays
- **`BT`** (Bottom-Top): Reverse vertical flow
- **`RL`** (Right-Left): Reverse horizontal flow

#### Distance Parameters
- **`esep`**: Controls spacing between edges (relationship lines)
- **`node-sep`**: Minimum distance between table nodes
- **`rank-sep`**: Distance between different levels/ranks of tables

### Advanced Filtering

Tables are automatically excluded based on common patterns:

- **Views**: `vw_*`, `*_view`
- **Temporary**: `*_temp`, `*_tmp`, `temp_*`
- **Backup**: `*_bk`, `*_backup`, `*_old`
- **Audit/Log**: `*_log`, `*_audit`, `audit_*`
- **Duplicates**: `*_dups`, `*_duplicates`
- **Archives**: `*_archive`, `archive_*`

Use `--show-standalone false` to hide tables with no foreign key relationships.

---

## 🎯 Interactive Components

The generated SVG includes several interactive panels that can be moved, resized, and minimized:
### 📊 Metadata Panel
Displays comprehensive information about your database schema:
- **Schema statistics** (table count, columns, relationships)
- **Generation parameters** used
- **File information** and timestamps
- **Interactive controls** (minimize, close, drag to reposition)

[![Metadata Panel](https://live.staticflickr.com/65535/54701918384_2debb75e13_z.jpg)](https://flic.kr/s/aHBqjCpNX1)

### 🗺️ Miniature Overview
Navigate large schemas effortlessly:
- **Interactive minimap** with viewport indicator
- **Click to jump** to specific schema areas
- **Drag viewport** for precise navigation
- **Resizable panel** - make it larger for detailed navigation

[![Overview Panel](https://live.staticflickr.com/65535/54702015980_bca2aedb3e_c.jpg)](https://flic.kr/s/aHBqjCpNX1)

### 🔍 Selection Details
View and export detailed SQL information:
- **Table definitions** with column details and constraints
- **Foreign key relationships** with full SQL syntax
- **Trigger information** including execution details
- **Copy button** for instant clipboard access
- **Download button** for formatted text export
- **Enterprise-friendly** emoji-free output option

[![Selection Panel](https://flic.kr/p/2rnUkss](https://flic.kr/s/aHBqjCpNX1)
**Example selection output:**
```
📊 Selected Tables
==================
public_franchises
public_association_map
public_ecommerce
...

🔗 Foreign Key Relationships  
============================
🔑 franchise_id → id
ALTER TABLE ONLY public.association_map
    ADD CONSTRAINT association_map_franchise_id_fkey 
    FOREIGN KEY (franchise_id) REFERENCES public.franchises(id) 
    ON DELETE CASCADE;
```

---

## 🏢 Enterprise Deployment

### CI/CD Integration
```yaml
# GitHub Actions example
- name: Generate Database Documentation
  run: |
    pip install pypgsvg
    sudo apt-get install graphviz
    pypgsvg schemas/production.dump --output docs/database_erd
    
# Docker deployment
FROM python:3.9-slim
RUN apt-get update && apt-get install -y graphviz && rm -rf /var/lib/apt/lists/*
RUN pip install pypgsvg
COPY schema.dump .
RUN pypgsvg schema.dump --output database_diagram
```

### Automation Scripts
```bash
#!/bin/bash
# Enterprise schema documentation automation
DATE=$(date +%Y%m%d)
pg_dump -h $DB_HOST -d $DB_NAME -U $DB_USER -s > schema_$DATE.dump
pypgsvg schema_$DATE.dump --output docs/database_erd_$DATE --hide-standalone
echo "✅ Database documentation updated: docs/database_erd_$DATE.svg"
```

---

## 🔧 Complete Feature Overview

### 📊 Database Schema Parsing

pypgsvg supports comprehensive PostgreSQL schema parsing including:

#### Table Structure Analysis
- **CREATE TABLE** statements with full column definitions
- **Data type detection** for all PostgreSQL types (SERIAL, JSONB, arrays, custom types)
- **Column constraints** (NOT NULL, DEFAULT values, CHECK constraints)
- **Primary key identification** (single and composite keys)
- **Quoted identifiers** and schema-qualified table names
- **Unicode support** with proper UTF-8 encoding handling

#### Relationship Mapping
- **Foreign key constraints** from ALTER TABLE statements
- **Inline REFERENCES** declarations within CREATE TABLE
- **Cascading options** (ON DELETE CASCADE, ON UPDATE RESTRICT, etc.)
- **Complex relationship patterns** (self-referencing, many-to-many)
- **Cross-schema references** with schema qualification

#### Advanced SQL Features
- **Database triggers** (BEFORE/AFTER/INSTEAD OF with INSERT/UPDATE/DELETE)
- **Trigger function calls** with parameter parsing
- **Constraint naming** and organization
- **Index definitions** (when present in dump)
- **Sequence relationships** for SERIAL columns

### 🎨 Visual Representation

#### Intelligent Layout Engine
- **Graphviz integration** with optimized parameter passing
- **Automatic table positioning** to minimize edge crossings
- **Hierarchical layouts** showing data flow and dependencies
- **Compact arrangements** for large schemas
- **Custom spacing** controls for readability

#### Color-Coded Organization
- **Deterministic color assignment** based on table names
- **WCAG-compliant contrast** for accessibility
- **Color-blind friendly** palette selection
- **Saturation controls** for visual emphasis
- **Automatic text color** calculation for optimal readability

#### Interactive Enhancement
- **Clickable elements** for detailed SQL view
- **Hover effects** for element identification
- **Drag-and-drop** interface elements
- **Resizable panels** for workspace customization
- **Keyboard navigation** (ESC, R keys for reset)

### 🖥️ User Interface Components

#### Selection & Detail Panel
- **Multi-select capability** for tables and relationships
- **SQL source display** with proper formatting
- **Clipboard integration** for easy copying
- **Download functionality** for formatted exports
- **Emoji-free output** option for enterprise use
- **Trigger information** display with execution details

#### Miniature Navigation
- **Schema overview** with proportional scaling
- **Viewport indicator** showing current view
- **Click-to-navigate** functionality
- **Drag viewport** for precise positioning
- **Zoom level awareness** and synchronization

#### Metadata Information
- **Schema statistics** (table count, column count, relationship count)
- **Generation parameters** display
- **File information** (size, modification date, encoding)
- **Processing timestamps** for audit trails
- **Parameter documentation** for reproducibility

### 🛠️ Enterprise Integration Features

#### Automation-Friendly Design
- **Command-line interface** with extensive options
- **Scriptable Python API** for programmatic use
- **Error handling** with detailed reporting
- **Return codes** for CI/CD integration
- **Logging support** for monitoring and debugging

#### Output Customization
- **SVG format** for web integration and scaling
- **Self-contained files** with embedded styles and scripts
- **No external dependencies** in generated output
- **Cross-browser compatibility** (Chrome, Firefox, Safari, Edge)
- **Print-friendly** layouts with proper scaling

#### Quality Assurance
- **Input validation** with comprehensive error reporting
- **Graceful degradation** for partial schema parsing
- **Memory efficiency** for large schema processing
- **Performance optimization** for quick generation
- **Deterministic output** for version control

### 📋 Table Filtering & Exclusion

#### Automatic Exclusions
pypgsvg intelligently excludes common utility tables:

| Pattern | Examples | Reason |
|---------|----------|---------|
| `vw_*`, `*_view` | `vw_users`, `summary_view` | Database views |
| `*_temp`, `*_tmp`, `temp_*` | `data_temp`, `tmp_import` | Temporary tables |
| `*_bk`, `*_backup`, `*_old` | `users_bk`, `data_backup` | Backup tables |
| `*_log`, `*_audit`, `audit_*` | `error_log`, `audit_users` | Logging tables |
| `*_dups`, `*_duplicates` | `data_dups`, `user_duplicates` | Cleanup tables |
| `*_archive`, `archive_*` | `old_archive`, `archive_2023` | Archive tables |

#### Standalone Table Handling
- **Configurable display** of tables without foreign key relationships
- **Useful for utility tables** and lookup tables
- **Reduces clutter** in complex schemas
- **Maintains referential integrity** in relationship mapping

---

## 🧪 Testing & Quality

**Enterprise-grade testing** with comprehensive coverage:

```bash
# Run full test suite (no dependencies required)
python -m pytest tests/tests/

# Generate detailed coverage report
python -m pytest tests/tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

**Quality metrics:**
- ✅ **95%+ code coverage** 
- ✅ **70+ comprehensive tests**
- ✅ **Enterprise PYTHONPATH support**
- ✅ **Cross-platform compatibility**

---

## 🏗️ Architecture & Performance

### Lightweight Design
```text
📦 pypgsvg/
├── 🐍 Pure Python core (~450 lines)
├── 🎨 CSS styling (~200 lines)  
├── ⚡ JavaScript interactivity (~2000 lines)
├── 🧪 Comprehensive tests (~1000+ lines)
└── 📚 Zero runtime dependencies (except Graphviz)
```

**Performance characteristics:**
- **Fast parsing** - Processes large schemas in seconds
- **Memory efficient** - Minimal footprint for enterprise deployment
- **Scalable output** - Handles schemas with hundreds of tables
- **Quick startup** - No database connections or heavy frameworks

### Enterprise-Ready Features
- **🔒 Security-focused** - No network requirements, processes local files only
- **📋 Audit-friendly** - Deterministic output for version control
- **🚀 Container-ready** - Minimal Docker image size
- **⚙️ Configurable** - Extensive customization options
- **📊 Monitoring** - Built-in error reporting and validation

---

## ⚙️ Configuration & Customization

### Advanced Layout Options
```bash
# Horizontal layout for wide displays
pypgsvg schema.dump --rankdir LR --node-sep 3 --rank-sep 2

# Compact layout for presentations  
pypgsvg schema.dump --packmode graph --fontsize 16 --node-fontsize 14

# Large schema optimization
pypgsvg schema.dump --hide-standalone --esep 8 --rank-sep 4
```

### Table Filtering (Automatic)
Enterprise-focused exclusions for cleaner diagrams:
- **Views** (`vw_*`) - Database views  
- **Backup tables** (`*_bk`, `*_backup`) - Temporary backup data
- **Utility tables** (`*_temp`, `*_tmp`) - Temporary processing tables
- **Log tables** (`*_log`, `*_audit`) - Audit and logging tables
- **Duplicate tables** (`*_dups`, `*_duplicates`) - Data cleanup tables
- **Version tables** (`*_old`, `*_archive`) - Historical data tables

### Color & Accessibility
- **WCAG-compliant** color palette with proper contrast ratios
- **Automatic text color** calculation for readability
- **Color-blind friendly** palette selection
- **High-contrast mode** for professional presentations

---

## 🔧 Supported Database Features

### SQL Parsing Capabilities
- ✅ **CREATE TABLE** statements with all PostgreSQL data types
- ✅ **ALTER TABLE** constraints and foreign keys
- ✅ **Triggers** with BEFORE/AFTER/INSTEAD OF events
- ✅ **Primary keys** and unique constraints
- ✅ **Complex data types** (JSON, arrays, custom types)
- ✅ **Quoted identifiers** and schema-qualified names
- ✅ **Unicode support** with proper encoding handling

### Advanced SQL Features
```sql
-- Fully supported constructs
CREATE TABLE "complex_table" (
    id SERIAL PRIMARY KEY,
    data JSONB NOT NULL,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger support
CREATE TRIGGER update_modified_time 
    BEFORE UPDATE ON complex_table 
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- Foreign key variations
ALTER TABLE orders 
    ADD CONSTRAINT fk_customer 
    FOREIGN KEY (customer_id) 
    REFERENCES customers(id) 
    ON DELETE CASCADE ON UPDATE RESTRICT;
```

---

## 🚨 Error Handling & Reliability

**Production-ready error management:**
- **Graceful degradation** - Continues processing despite individual parsing errors
- **Detailed error reporting** - Specific line numbers and context
- **Encoding resilience** - Handles various character encodings
- **Malformed SQL recovery** - Attempts to extract partial information
- **Validation checks** - Ensures output integrity

**Enterprise logging:**
```python
# Built-in error collection for monitoring
tables, foreign_keys, triggers, errors = parse_sql_dump(sql_content)

if errors:
    for error in errors:
        log.warning(f"Schema parsing issue: {error}")
    # Continue with partial results
```

---

## 🤝 Contributing

We welcome enterprise users and contributors:

1. **Code quality** - Follow PEP 8 and maintain >95% test coverage
2. **Enterprise focus** - Consider automation and deployment scenarios  
3. **Performance** - Optimize for large schemas and CI/CD usage
4. **Documentation** - Update examples for enterprise use cases
5. **Testing** - Add tests for new SQL patterns and edge cases

---

## 📋 Dependencies

**Minimal dependency footprint for enterprise deployment:**

### Required
- **Python 3.8+** (standard in most enterprise environments)
- **Graphviz** (system package, widely available)

### Development/Testing Only
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting  

**That's it!** No heavy frameworks, databases, or complex runtime dependencies.

---

## 📄 License & Enterprise Usage

This project is released under the MIT License, making it suitable for:
- ✅ **Commercial use** in enterprise environments
- ✅ **Modification** for internal requirements  
- ✅ **Distribution** within organizations
- ✅ **Private use** without attribution requirements

Perfect for enterprise adoption with minimal legal overhead.
