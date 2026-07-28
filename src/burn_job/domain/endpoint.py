"""Endpoint Domain Models."""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EndpointInfo:
    """Represents a scanned Spring REST Controller endpoint."""
    path: str
    http_method: str = "GET"
    controller_class: str = ""
    method_name: str = ""
    file_path: str = ""
    line_number: int = 0
    query_params: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "http_method": self.http_method,
            "controller_class": self.controller_class,
            "method_name": self.method_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "query_params": self.query_params,
        }

# Alias Endpoint to EndpointInfo for contract consistency
Endpoint = EndpointInfo
