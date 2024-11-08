import pytesseract
from pdf2image import convert_from_path
from docx import Document
import pandas as pd
from typing import Dict, Any
import tempfile
import os

class DocumentProcessor:
    def process_document(self, file_content: bytes, filename: str) -> str:
        file_extension = filename.split('.')[-1].lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            if file_extension == 'pdf':
                text = self._process_pdf(temp_file_path)
            elif file_extension in ['png', 'jpg', 'jpeg']:
                text = self._process_image(temp_file_path)
            elif file_extension == 'csv':
                text = self._process_csv(temp_file_path)
            elif file_extension == 'docx':
                text = self._process_docx(temp_file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
        finally:
            os.unlink(temp_file_path)
            
        return text
    
    def _process_pdf(self, file_path: str) -> str:
        pages = convert_from_path(file_path)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page)
        return text
    
    def _process_image(self, file_path: str) -> str:
        return pytesseract.image_to_string(file_path)
    
    def _process_csv(self, file_path: str) -> str:
        df = pd.read_csv(file_path)
        return df.to_string()
    
    def _process_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        return " ".join([paragraph.text for paragraph in doc.paragraphs])