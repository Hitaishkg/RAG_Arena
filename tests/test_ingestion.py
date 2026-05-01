import sys
import os
import tiktoken
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.ingestion.chunker import chunk_text, chunk_document, detect_section
from tests.fixtures.sample_pages import SAMPLE_PAGES

def test_chunk_text_basic():
    """chunk a text of ~200 words, assert result is a non-empty list of strings"""
    text = " ".join(["word" for _ in range(200)])
    chunks = chunk_text(text, chunk_size=100)
    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)

def test_chunk_text_no_sentence_break():
    """for each chunk, assert it does not end mid-sentence"""
    text = "Sentence one. Sentence two? Sentence three! Sentence four. Sentence five."
    chunks = chunk_text(text, chunk_size=10)
    sentence_endings = ('.', '?', '!', '"', ')', '}')
    for chunk in chunks:
        assert chunk.endswith(sentence_endings) or chunk == text.split()[-1]

def test_chunk_text_token_budget():
    """with chunk_size=50, assert each chunk has at most 60 tokens"""
    encoding = tiktoken.get_encoding("cl100k_base")
    text = "This is a long sentence that should be chunked properly based on token counts. " * 10
    chunks = chunk_text(text, chunk_size=50)
    for chunk in chunks:
        tokens = encoding.encode(chunk)
        assert len(tokens) <= 60

def test_chunk_text_single_long_sentence():
    """pass a single sentence of ~600 tokens, assert result has exactly 1 chunk (not discarded)"""
    long_sentence = "Word " * 600 + "."
    chunks = chunk_text(long_sentence, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == long_sentence

def test_chunk_document_returns_chunks():
    """call chunk_document(SAMPLE_PAGES), assert len > 0"""
    chunks = chunk_document(SAMPLE_PAGES)
    assert len(chunks) > 0

def test_chunk_document_chunk_ids():
    """assert all chunk ids match pattern test_doc_p{N}_c{NNN}"""
    chunks = chunk_document(SAMPLE_PAGES)
    pattern = r"test_doc_p\d+_c\d{3}"
    for chunk in chunks:
        assert re.match(pattern, chunk["id"])

def test_chunk_document_fields():
    """assert every chunk has keys: id, text, doc_id, page, section"""
    chunks = chunk_document(SAMPLE_PAGES)
    expected_keys = {"id", "text", "doc_id", "page", "section"}
    for chunk in chunks:
        assert set(chunk.keys()) == expected_keys

def test_detect_section_all_caps():
    """assert detect_section(\"DEFINITIONS\\nsome text\") returns \"DEFINITIONS\""""
    assert detect_section("DEFINITIONS\nsome text") == "DEFINITIONS"

def test_detect_section_numbered():
    """assert detect_section(\"1. Disclosure Requirements\\ntext\") returns \"1. Disclosure Requirements\""""
    assert detect_section("1. Disclosure Requirements\ntext") == "1. Disclosure Requirements"

def test_detect_section_empty():
    """assert detect_section(\"just a normal sentence here.\") returns \"\""""
    assert detect_section("just a normal sentence here.") == ""
