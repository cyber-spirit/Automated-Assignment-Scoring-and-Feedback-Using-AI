"""
iteration4_test.py

Unit tests for the main python file.

These tests verify:
1. csv mark schemes load correctly
2. pdf text extraction works
3. Ollama grading function processes streamed responses correctly
4. pdf report generation works

External services such as the Ollama API, PDF reader, and PDF writer
are mocked to ensure tests run quickly and deterministically.

The file needs to end in _test.py for pytest to discover it.
"""

from unittest.mock import Mock, patch
import pytest

# Import functions from automatedFYPMarker.py
from automatedFYPMarker import (
    load_mark_schemes_from_csv,
    extract_text_from_pdf,
    grade_with_ollama_streaming,
    create_pdf
)

# -----------------------------------------------------
# Tests for load_mark_schemes_from_csv
# -----------------------------------------------------
# Explanation of the tests:
# Test: test_load_mark_schemes_success:
# Tests that a valid CSV file is correctly converted into a dictionary.
# tmp_path creates a temporary directory so the real code isn't affected.
# Test: test_load_mark_schemes_file_not_found:
# This tests that the function throws an error when the mark scheme csv file isn't found.


def test_load_mark_schemes_success(tmp_path):

    csv_content = """project_type,criterion_name,weight,description
Engineering,Requirements,40,Good requirements
Study,Design,30,Good system design
Research,Methodology,50,Good research methodology
"""

    csv_file = tmp_path / "schemes.csv"
    csv_file.write_text(csv_content)

    result = load_mark_schemes_from_csv(csv_file)

    expected = {
        "Engineering": {
            "Requirements": {
                "weight": 40,
                "description": "Good requirements"
            }
        },
        "Study": {
            "Design": {
                "weight": 30,
                "description": "Good system design"
            }
        },
        "Research": {
            "Methodology": {
                "weight": 50,
                "description": "Good research methodology"
            }
        }
    }

    assert result == expected


def test_load_mark_schemes_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_mark_schemes_from_csv("missing_file.csv")


# -----------------------------------------------------
# Test for extract_text_from_pdf
# -----------------------------------------------------
# Explanation of the test:
# Test: test_extract_text_from_pdf:
# This tests that the extract text from pdf function correctly combines text from multiple pages of the pdf and extracts it.


@patch("automatedFYPMarker.PdfReader")
def test_extract_text_from_pdf(mock_pdf_reader):

    page1 = Mock()
    page1.extract_text.return_value = "Page 1 text"

    page2 = Mock()
    page2.extract_text.return_value = "Page 2 text"

    reader_instance = Mock()
    reader_instance.pages = [page1, page2]

    mock_pdf_reader.return_value = reader_instance

    result = extract_text_from_pdf("fake.pdf")

    assert result == "Page 1 text\nPage 2 text"


# -----------------------------------------------------
# Tests for grade_with_ollama_streaming
# -----------------------------------------------------
# Explanation of the test:
# Test: test_grade_with_ollama_streaming:
# This tests that the grade with ollama function correctly puts together the models streamed responses into a single string.
# The below fake ollama stream function is NOT a test function, it is just a funciton that simulates the streaming output of the model.
# Also note the use of @patch on the test function. (comes from unittest.mock)
# This exists so the external stuff used in iteration 4 (ollama, pdf reader and fpdf) are mocked and not actually used.

def fake_ollama_stream():
    responses = [
        {"message": {"content": "Hello "}},
        {"message": {"content": "world"}},
        {"message": {"content": "!"}}
    ]

    for r in responses:
        yield r


@patch("automatedFYPMarker.ollama.chat")
def test_grade_with_ollama_streaming(mock_chat):
    mock_chat.return_value = fake_ollama_stream()

    result = grade_with_ollama_streaming("student text", "system prompt")

    assert result == "Hello world!"


# -----------------------------------------------------
# Tests for create_pdf
# -----------------------------------------------------
# Explanation of the tests:
# Test: test_create_pdf:
# This tests that the the create pdf function calls the correct fpdf methods to create a pdf that looks correct.
# Again @patch is used here to mock the fpdf method so a pdf file isn't actually created.
# Test: test_create_pdf_handles_unicode:
# This is a test for the create pdf function to check it handles some unicode characters correctly so the pdf looks correct.

@patch("automatedFYPMarker.FPDF")
def test_create_pdf(mock_fpdf):
    pdf_instance = Mock()
    mock_fpdf.return_value = pdf_instance

    create_pdf("Example text", "output.pdf")

    pdf_instance.add_page.assert_called_once()
    pdf_instance.set_font.assert_called_once_with("Helvetica", size=10)

    pdf_instance.multi_cell.assert_called_once()

    pdf_instance.output.assert_called_once_with("output.pdf")


@patch("automatedFYPMarker.FPDF")
def test_create_pdf_handles_unicode(mock_fpdf):
    pdf_instance = Mock()
    mock_fpdf.return_value = pdf_instance

    text = "Unicode text: é ñ 汉字"

    create_pdf(text, "test.pdf")

    cleaned = text.encode("latin-1", "replace").decode("latin-1")

    pdf_instance.multi_cell.assert_called_once_with(0, 5, cleaned)