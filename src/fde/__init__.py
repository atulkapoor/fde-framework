"""A framework that takes an engagement from problem statement to a runnable project."""

try:
    from importlib.metadata import PackageNotFoundError, version
    __version__ = version("fde-framework")
except PackageNotFoundError:  # source tree without an install
    __version__ = "0.0.0.dev0"
