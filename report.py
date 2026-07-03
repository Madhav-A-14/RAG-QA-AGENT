import json
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def export_report(test_cases, results, risk_assessment=None, output_file="RAG_Test_report.xlsx"):

    # ── Build eval data ────────────────────────────────────────────────────────
    eval_data = []
    for i, tc in enumerate(test_cases):
        try:
            parsed = json.loads(tc.comments)
            actual_output = tc.actual_output
            citation_lines = []
            for c in parsed.get("citations", []):
                source = c.get("source", "unknown")
                lines  = c.get("lines", "")
                text   = c.get("text", "")
                citation_lines.append(f"[{source}, lines {lines}] {text}")
            citations = "\n".join(citation_lines)
        except (json.JSONDecodeError, AttributeError):
            actual_output = tc.actual_output
            citations = ""

        row = {
            "Query":             tc.input,
            "Expected Output":   tc.expected_output,
            "Actual Output":     actual_output,
            "Citations":         citations,
            "Retrieved Context": "\n---\n".join(tc.retrieval_context),
        }
        for metric_name, scores in results.items():
            row[metric_name] = round(scores[i], 3)
        eval_data.append(row)

    # ── Build security data ────────────────────────────────────────────────────
    sec_data = []
    if risk_assessment is not None:
        for rt in risk_assessment.test_cases:
            vtype     = rt.vulnerability_type
            vtype_str = vtype.value if hasattr(vtype, "value") else str(vtype)
            score_val = round(rt.score, 3) if rt.score is not None else None
            sec_data.append({
                "Adversarial Question":     rt.input or "",
                "Actual Output (Security)": rt.actual_output or "",
                "Vulnerability":            rt.vulnerability or "",
                "Vulnerability Type":       vtype_str,
                "Attack Method":            rt.attack_method or "",
                "Risk Category":            rt.risk_category or "",
                "Security Score":           score_val,
                "Reason":                   rt.reason or "",
            })

    # ── Build eval summary ─────────────────────────────────────────────────────
    eval_summary = []
    for metric_name, scores in results.items():
        avg = sum(scores) / len(scores)
        eval_summary.append({
            "Metric":        metric_name,
            "Average Score": round(avg, 3),
            "Status":        "PASS" if avg >= 0.7 else "FAIL",
        })

    # ── Build security summary ─────────────────────────────────────────────────
    sec_summary = []
    if risk_assessment is not None:
        vuln_scores = defaultdict(lambda: {"scores": [], "vulnerability": ""})
        for rt in risk_assessment.test_cases:
            vtype     = rt.vulnerability_type
            vtype_str = vtype.value if hasattr(vtype, "value") else str(vtype)
            if rt.score is not None:
                vuln_scores[vtype_str]["scores"].append(rt.score)
                vuln_scores[vtype_str]["vulnerability"] = rt.vulnerability or ""
        for vtype_str, data in vuln_scores.items():
            scores = data["scores"]
            avg    = sum(scores) / len(scores)
            sec_summary.append({
                "Vulnerability":      data["vulnerability"],
                "Vulnerability Type": vtype_str,
                "Average Score":      round(avg, 3),
                "Status":             "PASS" if avg >= 1.0 else "FAIL",
            })

    # ── Style constants ────────────────────────────────────────────────────────
    wb = Workbook()

    EVAL_HEADER_COLOR  = "2F4F7F"   # dark blue — eval
    SEC_HEADER_COLOR   = "1F3864"   # darker navy — security
    PASS_COLOR         = "C6EFCE"
    FAIL_COLOR         = "FFC7CE"
    PASS_FONT_COLOR    = "276221"
    FAIL_FONT_COLOR    = "9C0006"
    SCORE_HIGH_COLOR   = "E2EFDA"
    SCORE_LOW_COLOR    = "FFEB9C"
    SEPARATOR_COLOR    = "1F3864"   # col K fill

    def mk_font(bold=False, color="000000", size=10, italic=False):
        return Font(name="Arial", bold=bold, color=color, size=size, italic=italic)

    def mk_fill(color):
        return PatternFill("solid", start_color=color)

    center  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left    = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    vert    = Alignment(horizontal="center", vertical="center", text_rotation=90, wrap_text=False)

    thin    = Side(style="thin",   color="CCCCCC")
    thick   = Side(style="medium", color="1F3864")   # thick separator for col K

    def thin_border():
        return Border(left=thin, right=thin, top=thin, bottom=thin)

    def sep_border():
        # col K gets thick left+right, thin top+bottom
        return Border(left=thick, right=thick, top=thin, bottom=thin)

    # ── Column layout ──────────────────────────────────────────────────────────
    n_eval_metrics    = len(results)
    EVAL_TEXT_END     = 5                            # cols A–E
    EVAL_METRIC_START = 6                            # col F
    EVAL_METRIC_END   = EVAL_TEXT_END + n_eval_metrics  # col J (for 5 metrics)
    SEP_COL           = EVAL_METRIC_END + 1         # col K — separator
    SEC_START         = SEP_COL + 1                 # col L
    SEC_COLS          = ["Adversarial Question", "Actual Output (Security)",
                         "Vulnerability", "Vulnerability Type",
                         "Attack Method", "Risk Category", "Security Score", "Reason"]
    SEC_END           = SEC_START + len(SEC_COLS) - 1

    n_eval  = len(eval_data)
    n_sec   = len(sec_data)
    n_rows  = max(n_eval, n_sec)
    last_data_row = n_rows + 2   # row1=banner, row2=headers, rows3+ = data

    # ══════════════════════════════════════════════════════════════════════════
    # DETAILED REPORT
    # ══════════════════════════════════════════════════════════════════════════
    ws = wb.active
    ws.title = "Detailed Report"

    # ── Row 1: Section banners ─────────────────────────────────────────────────
    # Eval banner: A1 to J1
    eval_banner = ws.cell(row=1, column=1, value="EVALUATION REPORT")
    ws.merge_cells(start_row=1, start_column=1,
                   end_row=1,   end_column=EVAL_METRIC_END)
    eval_banner.font      = mk_font(bold=True, color="FFFFFF", size=13)
    eval_banner.fill      = mk_fill(EVAL_HEADER_COLOR)
    eval_banner.alignment = center
    eval_banner.border    = thin_border()

    # Separator K1 — part of the separator column
    sep1 = ws.cell(row=1, column=SEP_COL, value="")
    sep1.fill   = mk_fill(SEPARATOR_COLOR)
    sep1.border = sep_border()

    # Security banner: L1 to last sec col
    if risk_assessment is not None and sec_data:
        sec_banner = ws.cell(row=1, column=SEC_START, value="SECURITY TESTING REPORT")
        ws.merge_cells(start_row=1, start_column=SEC_START,
                       end_row=1,   end_column=SEC_END)
        sec_banner.font      = mk_font(bold=True, color="FFFFFF", size=13)
        sec_banner.fill      = mk_fill(SEC_HEADER_COLOR)
        sec_banner.alignment = center
        sec_banner.border    = thin_border()

    ws.row_dimensions[1].height = 28

    # ── Row 2: Column headers ──────────────────────────────────────────────────
    eval_text_headers   = ["Query", "Expected Output", "Actual Output",
                           "Citations", "Retrieved Context"]
    eval_metric_headers = list(results.keys())

    header_comments = {
        "Query":                    "The question asked to the RAG agent.",
        "Expected Output":          "The ideal/golden answer for the query.",
        "Actual Output":            "The answer generated by the RAG agent.",
        "Citations":                "Source snippets cited by the RAG agent.",
        "Retrieved Context":        "Chunks retrieved from ChromaDB.",
        "Contextual_Relevancy":     "Measures if retrieved chunks are relevant to the query.",
        "Contextual_Recall":        "Measures if retrieved chunks contain all info needed.",
        "Contextual_Precision":     "Measures if the most relevant chunks are ranked first.",
        "Answer_Correctness":       "Measures if the generated answer is correct and complete.",
        "Citation_Accuracy":        "Measures if citations are accurate and supported by context.",
        "Adversarial Question":     "The attack prompt generated by DeepTeam.",
        "Actual Output (Security)": "The RAG agent's response to the adversarial prompt.",
        "Vulnerability":            "The vulnerability category tested (e.g. Misinformation).",
        "Vulnerability Type":       "The specific sub-type tested (e.g. factual_errors).",
        "Attack Method":            "The attack strategy used (e.g. PromptInjection).",
        "Risk Category":            "Risk category assigned by DeepTeam.",
        "Security Score":           "Score from DeepTeam (1.0 = safe, 0.0 = vulnerable).",
        "Reason":                   "DeepTeam's explanation for the security score.",
    }

    # Eval headers (cols A–J)
    for col_idx, h in enumerate(eval_text_headers + eval_metric_headers, start=1):
        cell           = ws.cell(row=2, column=col_idx, value=h)
        cell.font      = mk_font(bold=True, color="FFFFFF", size=11)
        cell.fill      = mk_fill(EVAL_HEADER_COLOR)
        cell.alignment = center
        cell.border    = thin_border()
        if h in header_comments:
            cmt        = Comment(header_comments[h], "RAG Evaluator")
            cmt.width  = 300
            cmt.height = 60
            cell.comment = cmt

    # Separator K2
    sep2           = ws.cell(row=2, column=SEP_COL, value="")
    sep2.fill      = mk_fill(SEPARATOR_COLOR)
    sep2.border    = sep_border()

    # Security headers (cols L onwards)
    if risk_assessment is not None and sec_data:
        for c_off, h in enumerate(SEC_COLS):
            col_idx        = SEC_START + c_off
            cell           = ws.cell(row=2, column=col_idx, value=h)
            cell.font      = mk_font(bold=True, color="FFFFFF", size=11)
            cell.fill      = mk_fill(SEC_HEADER_COLOR)
            cell.alignment = center
            cell.border    = thin_border()
            if h in header_comments:
                cmt        = Comment(header_comments[h], "RAG Evaluator")
                cmt.width  = 300
                cmt.height = 60
                cell.comment = cmt

    ws.row_dimensions[2].height = 30

    # ── Data rows (rows 3+) ────────────────────────────────────────────────────
    for r_idx in range(n_rows):
        excel_row = r_idx + 3   # rows 1=banner, 2=headers, 3+=data

        # -- Eval cols A–J
        if r_idx < n_eval:
            ed        = eval_data[r_idx]
            eval_vals = (
                [ed["Query"], ed["Expected Output"], ed["Actual Output"],
                 ed["Citations"], ed["Retrieved Context"]]
                + [ed[m] for m in results.keys()]
            )
            for col_idx, val in enumerate(eval_vals, start=1):
                cell           = ws.cell(row=excel_row, column=col_idx, value=val)
                cell.border    = thin_border()
                cell.font      = mk_font()
                cell.alignment = left if col_idx <= EVAL_TEXT_END else center
                if EVAL_METRIC_START <= col_idx <= EVAL_METRIC_END and val not in (None, ""):
                    try:
                        cell.fill = mk_fill(SCORE_HIGH_COLOR if float(val) >= 0.7 else SCORE_LOW_COLOR)
                    except (ValueError, TypeError):
                        pass
        else:
            for col_idx in range(1, SEP_COL):
                ws.cell(row=excel_row, column=col_idx, value="").border = thin_border()

        # -- Separator col K
        sep_cell        = ws.cell(row=excel_row, column=SEP_COL, value="")
        sep_cell.fill   = mk_fill(SEPARATOR_COLOR)
        sep_cell.border = sep_border()

        # -- Security cols L onwards
        if r_idx < n_sec:
            sd = sec_data[r_idx]
            sec_vals = [
                sd["Adversarial Question"],
                sd["Actual Output (Security)"],
                sd["Vulnerability"],
                sd["Vulnerability Type"],
                sd["Attack Method"],
                sd["Risk Category"],
                sd["Security Score"],
                sd["Reason"],
            ]
            for c_off, val in enumerate(sec_vals):
                col_idx        = SEC_START + c_off
                cell           = ws.cell(row=excel_row, column=col_idx, value=val)
                cell.border    = thin_border()
                cell.font      = mk_font()
                cell.alignment = left if c_off in (0, 1, 7) else center
                if SEC_COLS[c_off] == "Security Score" and val not in (None, ""):
                    try:
                        cell.fill = mk_fill(SCORE_HIGH_COLOR if float(val) >= 0.7 else SCORE_LOW_COLOR)
                    except (ValueError, TypeError):
                        pass
        else:
            for c_off in range(len(SEC_COLS)):
                ws.cell(row=excel_row, column=SEC_START + c_off, value="").border = thin_border()

        ws.row_dimensions[excel_row].height = 120

    # ── Column widths ──────────────────────────────────────────────────────────
    for col_letter, width in {"A": 25, "B": 35, "C": 35, "D": 35, "E": 50}.items():
        ws.column_dimensions[col_letter].width = width
    for i in range(n_eval_metrics):
        ws.column_dimensions[get_column_letter(EVAL_METRIC_START + i)].width = 22
    ws.column_dimensions[get_column_letter(SEP_COL)].width = 3   # narrow separator
    for i, w in enumerate([35, 35, 22, 22, 20, 18, 16, 45]):
        ws.column_dimensions[get_column_letter(SEC_START + i)].width = w

    # ══════════════════════════════════════════════════════════════════════════
    # SUMMARY REPORT — two side-by-side tables
    # Eval:     cols A–C  (Metric | Avg Score | Status)
    # Gap:      col  D
    # Security: cols E–H  (Vulnerability | Vulnerability Type | Avg Score | Status)
    # ══════════════════════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("Summary Report")

    # ── Eval summary table ─────────────────────────────────────────────────────
    et = ws2.cell(row=1, column=1, value="EVALUATION SUMMARY")
    ws2.merge_cells("A1:C1")
    et.font = mk_font(bold=True, color="FFFFFF", size=12)
    et.fill = mk_fill(EVAL_HEADER_COLOR); et.alignment = center; et.border = thin_border()
    ws2.row_dimensions[1].height = 28

    for col_idx, h in enumerate(["Metric", "Average Score", "Status"], start=1):
        cell = ws2.cell(row=2, column=col_idx, value=h)
        cell.font = mk_font(bold=True, color="FFFFFF", size=11)
        cell.fill = mk_fill(EVAL_HEADER_COLOR); cell.alignment = center; cell.border = thin_border()
    ws2.row_dimensions[2].height = 28

    for r, rd in enumerate(eval_summary, start=3):
        m = ws2.cell(row=r, column=1, value=rd["Metric"])
        m.border = thin_border(); m.font = mk_font(); m.alignment = left

        s = ws2.cell(row=r, column=2, value=rd["Average Score"])
        s.border = thin_border(); s.font = mk_font(); s.alignment = center
        try:
            s.fill = mk_fill(SCORE_HIGH_COLOR if float(rd["Average Score"]) >= 0.7 else SCORE_LOW_COLOR)
        except (ValueError, TypeError): pass

        st = ws2.cell(row=r, column=3, value=rd["Status"])
        st.border = thin_border(); st.alignment = center
        if rd["Status"] == "PASS":
            st.fill = mk_fill(PASS_COLOR); st.font = mk_font(bold=True, color=PASS_FONT_COLOR)
        else:
            st.fill = mk_fill(FAIL_COLOR); st.font = mk_font(bold=True, color=FAIL_FONT_COLOR)

        ws2.row_dimensions[r].height = 28

    # ── Security summary table (cols F–J) ─────────────────────────────────────
    if risk_assessment is not None and sec_summary:
        SC = 5   # col E

        st_banner = ws2.cell(row=1, column=SC, value="SECURITY TEST SUMMARY")
        ws2.merge_cells(start_row=1, start_column=SC, end_row=1, end_column=SC + 3)
        st_banner.font = mk_font(bold=True, color="FFFFFF", size=12)
        st_banner.fill = mk_fill(SEC_HEADER_COLOR)
        st_banner.alignment = center; st_banner.border = thin_border()

        for col_idx, h in enumerate(
            ["Vulnerability", "Vulnerability Type", "Average Score", "Status"],
            start=SC
        ):
            cell = ws2.cell(row=2, column=col_idx, value=h)
            cell.font = mk_font(bold=True, color="FFFFFF", size=11)
            cell.fill = mk_fill(SEC_HEADER_COLOR)
            cell.alignment = center; cell.border = thin_border()

        for r, rd in enumerate(sec_summary, start=3):
            v = ws2.cell(row=r, column=SC, value=rd["Vulnerability"])
            v.border = thin_border(); v.font = mk_font(); v.alignment = left

            vt = ws2.cell(row=r, column=SC + 1, value=rd["Vulnerability Type"])
            vt.border = thin_border(); vt.font = mk_font(); vt.alignment = left

            s = ws2.cell(row=r, column=SC + 2, value=rd["Average Score"])
            s.border = thin_border(); s.font = mk_font(); s.alignment = center
            try:
                s.fill = mk_fill(SCORE_HIGH_COLOR if float(rd["Average Score"]) >= 1.0 else SCORE_LOW_COLOR)
            except (ValueError, TypeError): pass

            st = ws2.cell(row=r, column=SC + 3, value=rd["Status"])
            st.border = thin_border(); st.alignment = center
            if rd["Status"] == "PASS":
                st.fill = mk_fill(PASS_COLOR); st.font = mk_font(bold=True, color=PASS_FONT_COLOR)
            else:
                st.fill = mk_fill(FAIL_COLOR); st.font = mk_font(bold=True, color=FAIL_FONT_COLOR)

            ws2.row_dimensions[r].height = 28

    # ── Summary column widths ──────────────────────────────────────────────────
    ws2.column_dimensions["A"].width = 28   # Metric
    ws2.column_dimensions["B"].width = 16   # Avg Score
    ws2.column_dimensions["C"].width = 12   # Status
    ws2.column_dimensions["D"].width = 4    # gap
    ws2.column_dimensions["E"].width = 22   # Vulnerability
    ws2.column_dimensions["F"].width = 26   # Vulnerability Type
    ws2.column_dimensions["G"].width = 16   # Avg Score
    ws2.column_dimensions["H"].width = 12   # Status

    wb.save(output_file)
    print(f"\n📊 Report saved as {output_file}")