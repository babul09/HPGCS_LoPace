# LoPace Example Notebooks

This directory contains comprehensive example notebooks demonstrating how to use LoPace.

## Notebooks

### `LoPace_Complete_Guide.ipynb`

A complete guide covering all aspects of LoPace usage:

- **Introduction**: Overview of LoPace features and capabilities
- **Installation**: How to install and import LoPace
- **Quick Start**: Basic usage examples
- **Compression Methods**: Detailed examples of all three methods:
  - Zstd Compression
  - Token-based Compression (BPE)
  - Hybrid Compression (Recommended)
- **Configuration Options**: 
  - Tokenizer model selection
  - Zstd compression level tuning
- **Advanced Usage**:
  - Cross-instance compression/decompression
  - Batch processing
  - Compression statistics
- **Real-World Examples**:
  - Database storage scenarios
  - Conversation history compression
  - LLM API response caching
- **Best Practices**: Tips for optimal usage
- **Performance Benchmarks**: Comparison across methods and sizes

## Running the Notebook

1. Install Jupyter Notebook or JupyterLab:
   ```bash
   pip install jupyter
   ```

2. Install LoPace and dependencies:
   ```bash
   pip install lopace
   ```

3. Navigate to the notebooks directory and start Jupyter:
   ```bash
   cd notebooks
   jupyter notebook
   ```

4. Open `LoPace_Complete_Guide.ipynb` and run the cells!

## Requirements

- Python 3.8+
- LoPace (`pip install lopace`)
- Jupyter Notebook or JupyterLab

The notebook will automatically import all necessary dependencies when run.

## Notes

- All examples are designed to be runnable and demonstrate real-world use cases
- Performance benchmarks may vary based on your system
- Examples include lossless verification to demonstrate LoPace's guarantees
