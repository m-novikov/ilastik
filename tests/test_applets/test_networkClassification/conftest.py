import pytest

from lazyflow.graph import Graph

@pytest.fixture
def graph():
    return Graph()
