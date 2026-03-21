import fitz  # PyMuPDF
import io

class PDFService:
    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        text_content = []
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    text = page.get_text("text") # "text" mode is standard, "blocks" or "words" could be more detailed
                    if text:
                        text_content.append(text)
            
            combined_text = "\n".join(text_content)
            print(f"PDF Extraction Complete. Total characters: {len(combined_text)}")
            return combined_text
        except Exception as e:
            print(f"Error extracting PDF text with PyMuPDF: {e}")
            return ""
