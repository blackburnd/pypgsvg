# pypgsvg - Lightweight PostgreSQL ERD Generator

`pypgsvg` is a **lightweight** Python tool that generates a JS/CSS/SVG interactive Entity Relationship Diagrams (ERDs) from PostgreSQL schema dump files. With **only Graphviz as a dependency**, manually run or place in CI/CD pipelines, fast rapid deployment verification scenarios.



## 📦 Installation

**Lightweight setup - only 2 steps:**

1. Install `pypgsvg`:
   ```bash
   pip install pypgsvg
   ```

2. Install Graphviz (external dependency):
   - **macOS**: `brew install graphviz`
   - **Ubuntu/Debian**: `sudo apt-get install graphviz`
   - **CentOS/RHEL**: `sudo yum install graphviz`
   - **Windows**: Download from [Graphviz.org](https://graphviz.org/download/)

**That's it!** Ready for  deployment.

---


### 🎬 Quick Demo

[[🎯 View Interactive Example](https://www.blackburnsystems.com/demo-erd-complex)] 

![](https://live.staticflickr.com/65535/54725569515_1a265e1695.jpg)

**Try it yourself:**
```bash
# Download sample and generate interactive ERD
wget https://github.com/blackburnd/pypgsvg/raw/main/Samples/complex_schema.dump
pypgsvg schema.dump --output demo_erd --view
```


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

**Usage:**
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

[![Metadata Panel](https://live.staticflickr.com/65535/54725445018_efd3631f59.jpg)](https://flic.kr/s/aHBqjCpNX1)

### 🗺️ Miniature Overview
Navigate large schemas effortlessly:
- **Interactive minimap** with viewport indicator
- **Click to jump** to specific schema areas
- **Drag viewport** for precise navigation
- **Resizable panel** - make it larger for detailed navigation

[![Overview Panel](https://live.staticflickr.com/65535/54725569515_1a265e1695.jpg)](https://flic.kr/s/aHBqjCpNX1)

### 🔍 Selection Details
View and export detailed SQL information:
- **Table definitions** with column details and constraints
- **Foreign key relationships** with full SQL syntax
- **Trigger information** including execution details
- **Copy button** for instant clipboard access
- **Download button** for formatted text export
- **Enterprise-friendly** emoji-free output option

[![Selection Panel](https://live.staticflickr.com/65535/54725469434_1300a2e147.jpg)](https://flic.kr/s/aHBqjCpNX1)
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


For detailed testing instructions, see the [Testing Guide](docs/testing-guide.md).

**Quality metrics:**
- ✅ **95%+ code coverage** 
- ✅ **70+ comprehensive tests**
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


---

## 🚨 Error Handling & Reliability

**Error management:**
- **Graceful degradation** - Continues processing despite individual parsing errors
- **Detailed error reporting** - Specific line numbers and context
- **Encoding resilience** - Handles various character encodings
- **Malformed SQL recovery** - Attempts to extract partial information
- **Validation checks** - Ensures output integrity

**Logging:**
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
Welcome users and contributors:

1. **Code quality** - Follow PEP 8 and maintain >95% test coverage
2. **Enterprise focus** - Consider automation and deployment scenarios  
3. **Performance** - Optimize for large schemas and CI/CD usage
4. **Documentation** - Update examples for enterprise use cases
5. **Testing** - Add tests for new SQL patterns and edge cases

---

### Required
- **Python 3.8+** (standard in most enterprise environments)
- **Graphviz** (system package, widely available)

### Development/Testing Only
- **Node.js/npm** - Required for running browser tests only
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `playwright>=1.37.0` - Browser testing framework  

## Development Setup

### Quick Install (From Source)

If you're cloning the repository for development, use the automated installer:

```bash
# Clone the repository
git clone https://github.com/blackburnd/pypgsvg.git
cd pypgsvg

# Run the automated installer
./install.sh
```

The installer will:
- Detect your operating system (macOS, Ubuntu/Debian, CentOS/RHEL)
- Install Graphviz system package
- Install Node.js and npm
- Create Python virtual environment
- Install Python dependencies
- Install Playwright browser binaries

**Supported platforms:** macOS (with Homebrew), Ubuntu/Debian, CentOS/RHEL

### Manual Setup

If the automated installer doesn't support your system:

```bash
# 1. Install system dependencies
brew install graphviz node  # macOS
# or
sudo apt-get install graphviz nodejs npm  # Ubuntu/Debian

# 2. Create virtual environment and install Python dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e ".[test]"

# 3. Install Playwright browsers
npx playwright install
```

## Testing

The project includes both unit tests (Python) and functional tests (browser-based).

### Quick Start
Use the provided test runner script which handles environment setup:

```bash
# Run unit tests
./run-tests.sh

# Run browser tests
./run-tests.sh --browser
```
