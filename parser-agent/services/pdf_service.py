import pdfplumber
import io

class PDFService:
    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        text_content = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n".join(text_content)
