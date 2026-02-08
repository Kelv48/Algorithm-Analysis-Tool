from importlib import metadata as _metadata
try:
    __version__ = _metadata.version("algorithm_analysis_tool")
except _metadata.PackageNotFoundError:  # pragma: no cover - fallback for non-installed use
    __version__ = "0.1.3"