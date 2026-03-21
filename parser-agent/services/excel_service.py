import openpyxl
import io

class ExcelService:
    @staticmethod
    def extract_text(excel_bytes: bytes) -> str:
        text_content = []
        try:
            wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
            for sheet in wb.worksheets:
                text_content.append(f"--- Sheet: {sheet.title} ---")
                for row in sheet.iter_rows(values_only=True):
                    # Filter out None values and convert to string
                    row_data = [str(cell) for cell in row if cell is not None]
                    if row_data:
                        text_content.append(" | ".join(row_data))
            
            return "\n".join(text_content)
        except Exception as e:
            print(f"Failed to read Excel file: {e}")
            return ""
