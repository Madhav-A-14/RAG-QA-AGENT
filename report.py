import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def export_report(test_cases, results,output_file = "RAGEvaluation_report.xlsx"):
    
    
    # ── Detailed Sheet ─────────────────────────────────────────────────
    detailed_rows = []
    for i, tc in enumerate(test_cases):
        row = {
            "Query" : tc.input,
            "Expected Output" : tc.expected_output,
            "Actual Output" : tc.actual_output,
            "Retrieved Context" :"\n---\n".join(tc.retrieval_context),
        }   
        for metric_name , scores in results.items():
            row[metric_name] = round(scores[i],3)
        detailed_rows.append(row)
    
    detailed_df = pd.DataFrame(detailed_rows)
    
    # ── Summary Sheet ────────────────────────────────────────────────
     
    summary_rows = []
    for metric_name , scores in results.items():
        avg = sum(scores)/len(scores)
        summary_rows.append({
            "Metric": metric_name,
            "Average Score" : round(avg,3),
            "Status" : "PASS" if avg >= 0.7 else "FAIL",
        })
    summary_df = pd.DataFrame(summary_rows)
    
    # ── Write to Excel ─────────────────────────────────────────────────
     
    with pd.ExcelWriter(output_file,engine="openpyxl") as writer:
            detailed_df.to_excel(writer,sheet_name="Detailed Report", index = False)
            summary_df.to_excel(writer,sheet_name="Summary Report", index = False)
    
    
    
    # ── Formatting ─────────────────────────────────────────────────────
    wb = load_workbook(output_file)

    header_font     = Font(name="Arial", bold=True, color="FFFFFF", size=11)
    header_fill     = PatternFill("solid", start_color="2F4F7F")
    center_align    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align      = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    pass_fill       = PatternFill("solid", start_color="C6EFCE")
    fail_fill       = PatternFill("solid", start_color="FFC7CE")
    pass_font       = Font(name="Arial", color="276221", bold=True, size=10)
    fail_font       = Font(name="Arial", color="9C0006", bold=True, size=10)
    score_high_fill = PatternFill("solid", start_color="E2EFDA")
    score_low_fill  = PatternFill("solid", start_color="FFEB9C")
    thin_side       = Side(style="thin", color="CCCCCC")
    thin_border     = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    ws = wb["Detailed Report"]
    metric_col_start = 5

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    for row in ws.iter_rows(min_row=2):
        for col_idx, cell in enumerate(row, start=1):
            cell.border = thin_border
            cell.font = Font(name="Arial", size=10)
            cell.alignment = left_align if col_idx <= 4 else center_align
            if col_idx >= metric_col_start and cell.value is not None:
                cell.fill = score_high_fill if float(cell.value) >= 0.7 else score_low_fill

    for col, width in {"A": 35, "B": 38, "C": 38, "D": 50}.items():
        ws.column_dimensions[col].width = width
    for i in range(len(results)):
        ws.column_dimensions[get_column_letter(metric_col_start + i)].width = 22
    ws.row_dimensions[1].height = 30
    for row_idx in range(2, ws.max_row + 1):
        ws.row_dimensions[row_idx].height = 80  

    ws2 = wb["Summary Report"]

    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    for row in ws2.iter_rows(min_row=2):
        for col_idx, cell in enumerate(row, start=1):
            cell.border = thin_border
            cell.font = Font(name="Arial", size=10)
            cell.alignment = center_align
            if col_idx == 2 and cell.value is not None:
                cell.fill = score_high_fill if float(cell.value) >= 0.7 else score_low_fill
            if col_idx == 3 and cell.value:
                if "PASS" in str(cell.value):
                    cell.fill = pass_fill
                    cell.font = pass_font
                else:
                    cell.fill = fail_fill
                    cell.font = fail_font

    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 18
    ws2.column_dimensions["C"].width = 14
    ws2.row_dimensions[1].height = 30
    for row_idx in range(2, ws2.max_row + 1):
        ws2.row_dimensions[row_idx].height = 30
    

    wb.save(output_file)
    print(f"\n📊 Report saved as {output_file}")