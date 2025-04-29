"""Configuration file for the Sphinx documentation builder."""

# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import subprocess  # nosec B404
import sys
from pathlib import Path


def run_apidoc() -> None:
    """Run sphinx-apidoc to generate API documentation."""
    current_dir = Path(__file__).resolve().parent
    source_dir = current_dir.parent / "src" / "quantum_executor"
    output_dir = current_dir / "api"

    if output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "sphinx-apidoc",
        "-o",
        str(output_dir),
        str(source_dir),
        "--force",
        "--no-toc",
    ]

    subprocess.check_call(cmd)  # nosec B603  # noqa: S603


run_apidoc()

project = "Quantum Executor"  # pylint: disable=invalid-name
copyright = "2025, Giuseppe Bisicchia"  # pylint: disable=invalid-name redefined-builtin
author = "Giuseppe Bisicchia"  # pylint: disable=invalid-name
release = "0.1.0"  # pylint: disable=invalid-name

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",  # for Markdown support
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # for NumPy/Google docstring style
    "sphinx.ext.viewcode",  # optional: links to source code
    "sphinx.ext.mathjax",  # optional: for math formulas
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"  # pylint: disable=invalid-name
html_static_path = ["_static"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# sys.path.insert(0, os.path.abspath("../src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
