import os
import requests
import tempfile
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from markitdown import MarkItDown

mcp = FastMCP(name="DocumentReader", 
              instructions="This server provides tools to read PDF and DOCX documents into markdown",
                dependencies=["markitdown[all]","requests","os","tempfile"],
                description="This server provides tools to read PDF and DOCX documents into markdown",)

md = MarkItDown()

@mcp.tool(name="Read PDF Document", description="Read a PDF file and return the text content in LLM friendly MarkDown format.")
def read_pdf(file_path: str) -> str:
    """Read a PDF file and return the text content in LLM friendly MarkDown format.
    
    Args:
        file_path: Path or public URI to the PDF file to read
    """
    try:
        local_path = get_local_file(file_path)
        doc = md.convert(local_path)
        content: str = ""
        if doc.text_content is not None:
            content = doc.text_content
        return content
    except Exception as e:
        return f"Error reading PDF: {str(e)}"
    
@mcp.tool(name="Read DOCX Document", description="Read a DOCX file and return the text content in LLM friendly MarkDown format.")   
def read_docx(file_path: str) -> str:
    """Read a DOCX file and return the text content in LLM friendly MarkDown format.
    
    Args:
        file_path: Path or public URI to the Word document to read
    """
    try:
        local_path = get_local_file(file_path)
        doc = md.convert(local_path)
        content: str = ""
        if doc.text_content is not None:
            content = doc.text_content
        return content
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"
    
##Prompts
@mcp.prompt(name="Debug PDF", description="Helps to debug errors for PDF issues.")
def debug_pdf_path(error: str) -> list[base.Message]:
    """Debug prompt for PDF issues.
    
    This prompt helps diagnose issues when a PDF file cannot be read.
    
    Args:
        error: The error message encountered
    """
    content=f"I'm trying to read a PDF file but encountered this error: {error}. " \
            "How can I resolve this issue? Please provide step-by-step troubleshooting advice."
    return base.UserMessage(content=content)
    


##Helpers
def get_local_file(file_path: str) -> str:
    """
    If file_path is a public URI, download the file to a temporary location
    and return the local file path. Otherwise, expand the user's path.
    """
    if file_path.startswith("http://") or file_path.startswith("https://"):
        print(f"Downloading file from {file_path}...")
        response = requests.get(file_path)
        response.raise_for_status()
        # Try to preserve file extension, default to .tmp if none
        file_without_query_param = file_path.split("?")[0]
        _, ext = os.path.splitext(file_without_query_param)
        ext = ext if ext else ".tmp"
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        temp.write(response.content)
        temp.close()
        print(f"Saved temporary file at {temp.name}...")
        return temp.name
    return os.path.expanduser(file_path)


# server.py
def main():
    mcp.run(transport="streamable-http")

if __name__ == "__main__":
    main()
