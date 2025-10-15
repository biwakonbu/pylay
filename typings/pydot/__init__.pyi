"""pydot型スタブファイル"""

from typing import Any

class Dot:
    def __init__(
        self,
        graph_type: str = ...,
        rankdir: str = ...,
        **kwargs: Any,
    ) -> None: ...
    def add_node(self, node: Node) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def write_png(self, path: str) -> None: ...
    def write_pdf(self, path: str) -> None: ...
    def write_dot(self, path: str) -> None: ...

class Node:
    def __init__(
        self,
        name: str,
        label: str = ...,
        shape: str = ...,
        color: str = ...,
        **kwargs: Any,
    ) -> None: ...

class Edge:
    def __init__(
        self,
        source: str,
        target: str,
        label: str = ...,
        color: str = ...,
        fontcolor: str = ...,
        **kwargs: Any,
    ) -> None: ...
