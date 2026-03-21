import pdfplumber
import io

class PDFService:
    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        text_content = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                print(f"PDF opened with pdfplumber. Total pages: {len(pdf.pages)}")
                for i, page in enumerate(pdf.pages):
                    page_text = []
                    
                    # 1. Try to extract tables first
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            # Filter out empty rows/cols
                            clean_table = [[str(cell or "").strip() for cell in row] for row in table if any(row)]
                            if not clean_table: continue
                            
                            # Convert to Markdown-like table
                            md_table = "\n"
                            for r_idx, row in enumerate(clean_table):
                                md_table += "| " + " | ".join(row) + " |\n"
                                if r_idx == 0: # Add separator after header
                                    md_table += "| " + " | ".join(["---"] * len(row)) + " |\n"
                            page_text.append(md_table)
                    
                    # 2. Extract remaining text with layout=True to preserve columns
                    # We append it after tables. While there might be duplication, 
                    # LLMs handle duplication better than missing structural context.
                    raw_text = page.extract_text(layout=True)
                    if raw_text:
                        page_text.append("\n[RAW TEXT LAYOUT]\n" + raw_text)
                    
                    text_content.append(f"--- PAGE {i+1} ---\n" + "\n".join(page_text))
            
            combined_text = "\n\n".join(text_content)
            print(f"PDF Extraction Complete. Total characters: {len(combined_text)}")
            return combined_text
            
        except Exception as e:
            print(f"Error extracting PDF with pdfplumber: {e}")
            # Fallback to a very basic extraction if pdfplumber fails
            return str(pdf_bytes[:1000]) # Not ideal but prevents total crash
