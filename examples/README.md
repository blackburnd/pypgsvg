# pypgsvg Jupyter Examples

This directory contains Jupyter notebooks demonstrating how to use pypgsvg in an interactive environment.

## Setup

1. **Activate your virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Install pypgsvg with Jupyter dependencies:**
   ```bash
   pip install -e ".[test]"
   ```

   Or, to install only Jupyter dependencies:
   ```bash
   pip install -e ".[jupyter]"
   ```

3. **Set up the Jupyter kernel:**
   ```bash
   ./scripts/setup_jupyter_kernel.sh
   ```

   Or manually:
   ```bash
   python -m ipykernel install --user --name=pypgsvg --display-name="pypgsvg - PostgreSQL ERD Generator"
   ```

## Running the Examples

### Using JupyterLab (Recommended)

```bash
jupyter lab
```

This will open JupyterLab in your browser with the pypgsvg workspace configured.

### Using Jupyter Notebook

```bash
jupyter notebook
```

Navigate to the `examples` directory and open `pypgsvg_demo.ipynb`.

## Available Notebooks

- **pypgsvg_demo.ipynb**: Comprehensive demo showing how to:
  - Generate ERDs from PostgreSQL dump files
  - Display SVG diagrams inline in notebooks
  - Analyze parsed schema information
  - Customize ERD generation

## Creating Your Own Notebooks

When creating new notebooks in this project:

1. Select the "pypgsvg - PostgreSQL ERD Generator" kernel
2. Import the necessary modules:
   ```python
   from pypgsvg.erd_generator import ERDGenerator
   from IPython.display import SVG, display
   ```
3. Use the `display(SVG(filename='path/to/file.svg'))` to show generated diagrams

## Workspace Configuration

The project includes a default JupyterLab workspace configuration at `.jupyter/lab/workspaces/default.jupyterlab-workspace`. This provides a consistent development environment with:

- File browser on the left
- Main work area for notebooks
- Table of contents support

## Troubleshooting

### Kernel not showing up

If the pypgsvg kernel doesn't appear in Jupyter:
```bash
jupyter kernelspec list
```

If it's not listed, run the setup script again:
```bash
./scripts/setup_jupyter_kernel.sh
```

### Module import errors

Make sure you've installed the package in editable mode:
```bash
pip install -e ".[test]"
```

### SVG not displaying

Ensure:
1. The SVG file was generated successfully
2. The file path is correct
3. You're using `display(SVG(filename='path'))` not just `SVG('path')`

## Tips

- Use `Shift+Enter` to run cells
- Use `Tab` for code completion
- Use `Shift+Tab` to view function signatures
- The generated SVGs are interactive when opened in a browser, but static when displayed inline in notebooks
