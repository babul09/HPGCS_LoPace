# Technology Stack

## Core Technologies
- **Language**: Python (>=3.8) for backend, JavaScript/React for frontend
- **Backend Framework**: Core libraries, FastAPI (`serve_api.py`)
- **Frontend Framework**: React 19 (`frontend/package.json`), Vite 8

## Compression & Processing
- **Zstandard (`zstandard>=0.22.0`)**: Used for dictionary, per-prompt, and component compression.
- **LZ4 (`lz4>=4.3.3`)**: Fast compression backend.
- **Brotli (`brotli>=1.1.0`)**: Quality-focused text compression backend.
- **Snappy (`python-snappy>=0.7.1`)**: Fast dictionary compression backend.
- **TikToken (`tiktoken>=0.5.0`)**: OpenAI tokenization scheme (BPE mapping for text).
- **Gzip/Deflate**: Built-in Python library use.

## Analytics & Visualisation
- **NetworkX (`networkx>=3.0`)**: Graph processing for prompt references.
- **NumPy (`numpy>=1.24.0`)**: Array manipulations and centroid calculations.
- **Streamlit (`streamlit>=1.28.0`)**: Alternative legacy UI.
- **Plotly & Pandas**: Experimental dataframe analysis and chart plotting.

## Frontend Infrastructure
- **Routing**: `react-router-dom`
- **Icons**: `lucide-react`
- **Build System**: Vite 
- **Linting**: ESLint with React hooks plugins
