"""Pytest unit tests for burn_job.graph module."""

import tempfile
import os
import pytest
from burn_job.graph.store import KuzuGraphStore
from burn_job.graph.ingest import parse_profile, parse_collapsed_stack

def test_kuzu_graph_store_initialization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_kuzu_db")
        store = KuzuGraphStore(db_path=db_path)
        assert store is not None
        assert store.db_path == db_path

def test_parse_collapsed_profile_format():
    with tempfile.NamedTemporaryFile("w+", suffix=".collapsed", delete=False) as tmp_file:
        tmp_file.write("com.example.Service.methodA;com.example.Dao.query 15\n")
        tmp_file.write("com.example.Controller.get;com.example.Service.methodA 25\n")
        tmp_file_path = tmp_file.name

    try:
        edge_counts, method_counts, total_samples = KuzuGraphStore._parse_collapsed(tmp_file_path)
        assert total_samples == 40
        assert method_counts["com.example.Service.methodA"] == 40
        assert edge_counts[("com.example.Controller.get", "com.example.Service.methodA")] == 25
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

def test_parse_profile_helper():
    with tempfile.NamedTemporaryFile("w+", suffix=".collapsed", delete=False) as tmp_file:
        tmp_file.write("main;foo 5\n")
        tmp_file_path = tmp_file.name

    try:
        edge_counts, method_counts, total_samples, extra = parse_profile(tmp_file_path)
        assert total_samples == 5
        assert "main" in method_counts
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
