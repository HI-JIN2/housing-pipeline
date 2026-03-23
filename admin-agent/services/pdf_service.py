import pdfplumber
import io
import csv

class PDFService:
    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        text_content = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                print(f"PDF opened with pdfplumber. Total pages: {len(pdf.pages)}")
                for i, page in enumerate(pdf.pages):
                    page_parts = []
                    
                    # 1. Try to extract tables and convert to CSV
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            # Filter out empty rows/cols
                            clean_table = [[str(cell or "").strip() for cell in row] for row in table if any(row)]
                            if not clean_table: continue
                            
                            # Convert to CSV string
                            output = io.StringIO()
                            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
                            writer.writerows(clean_table)
                            csv_text = output.getvalue()
                            
                            page_parts.append("\n[TABLE START (CSV)]\n" + csv_text + "[TABLE END]\n")
                    
                    # 2. Extract remaining text with layout=True to preserve columns
                    raw_text = page.extract_text(layout=True)
                    if raw_text:
                        page_parts.append("\n[RAW TEXT LAYOUT]\n" + raw_text)
                    
                    text_content.append(f"--- PAGE {i+1} ---\n" + "\n".join(page_parts))
            
            combined_text = "\n\n".join(text_content)
            print(f"PDF Extraction Complete. Total characters: {len(combined_text)}")
            return combined_text
            
        except Exception as e:
            print(f"Error extracting PDF with pdfplumber (CSV mode): {e}")
            return ""
