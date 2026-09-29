"""
Flask Application for Unified Supply Chain, Logistics, and Manufacturing Intelligence.
Provides:
- Web views with dark glassmorphic UI, rich Charts (Chart.js), Slicers, and KPI Cards.
- Endpoints for multi-file upload (TIM, ME2N, Freight Status, MB52, PLNORDR, PRDORDR).
- 1-Click Excel master report download.
- Pre-loaded workspace data demonstration.
"""

import os
import io
import json
import pandas as pd
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
from engine import process_unified_datasets, generate_master_excel_workbook, sanitize_for_json

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # 256 MB max

def safe_json_response(data):
    """Ensure all NaN, Inf, and non-standard float values are converted to null for standard JSON compliance."""
    clean_data = sanitize_for_json(data)
    json_str = json.dumps(clean_data, allow_nan=False)
    return Response(json_str, mimetype="application/json")

WORKSPACE_DIR = Path(__file__).resolve().parent

# Global in-memory cache for processed dashboard results
CACHE = {
    "data": None,
    "dfs": None
}


def load_default_workspace_data(exclude_new=False, category="ALL", country="ALL"):
    """Auto-load existing Excel files in workspace directory for instant demo, reusing parsed dataframes for fast slicer responses."""
    tim_p = WORKSPACE_DIR / "TIM 22092026.xlsx"
    me2n_p = WORKSPACE_DIR / "me2n.XLSX"
    fs_p = WORKSPACE_DIR / "Freight Status 22092026.XLSX"
    mb52_p = WORKSPACE_DIR / "mb52.XLSX"
    pln_p = WORKSPACE_DIR / "plnordr.XLSX"
    prd_p = WORKSPACE_DIR / "prdordr.XLSX"

    raw_cache = CACHE.get("raw_dfs")
    if raw_cache:
        f_tim = raw_cache.get("df_tim")
        f_me2n = raw_cache.get("df_me2n")
        f_fs = raw_cache.get("df_fs")
        f_mb52 = raw_cache.get("df_mb52")
        f_pln = raw_cache.get("file_pln")
        f_prd = raw_cache.get("file_prd")
    else:
        f_tim = tim_p if tim_p.exists() else None
        f_me2n = me2n_p if me2n_p.exists() else None
        f_fs = fs_p if fs_p.exists() else None
        f_mb52 = mb52_p if mb52_p.exists() else None
        f_pln = pln_p if pln_p.exists() else None
        f_prd = prd_p if prd_p.exists() else None

    res, d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies, *extra = process_unified_datasets(
        file_tim=f_tim,
        file_me2n=f_me2n,
        file_fs=f_fs,
        file_mb52=f_mb52,
        file_pln=f_pln,
        file_prd=f_prd,
        exclude_new_status=exclude_new,
        selected_category=category,
        selected_country=country
    )
    if extra and extra[0]:
        CACHE["raw_dfs"] = extra[0]
    if category == "ALL" and country == "ALL" and not exclude_new:
        CACHE["data"] = res
        CACHE["dfs"] = (d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies)
    return res


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/dashboard-data", methods=["GET"])
def get_dashboard_data():
    exclude_new = request.args.get("exclude_new", "false").lower() == "true"
    reload_data = request.args.get("reload", "false").lower() == "true"
    category = request.args.get("category", "ALL")
    country = request.args.get("country", "ALL")

    # If any slicer or reload is requested, compute dynamically
    if CACHE["data"] is None or reload_data or exclude_new or category != "ALL" or country != "ALL":
        data = load_default_workspace_data(exclude_new=exclude_new, category=category, country=country)
    else:
        data = CACHE["data"]

    return safe_json_response(data)


@app.route("/api/upload", methods=["POST"])
def upload_files():
    try:
        f_tim = request.files.get("file_tim")
        f_me2n = request.files.get("file_me2n")
        f_fs = request.files.get("file_fs")
        f_mb52 = request.files.get("file_mb52")
        f_pln = request.files.get("file_pln")
        f_prd = request.files.get("file_prd")
        exclude_new = request.form.get("exclude_new", "false").lower() == "true"

        res, d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies, *extra = process_unified_datasets(
            file_tim=f_tim if f_tim and f_tim.filename else None,
            file_me2n=f_me2n if f_me2n and f_me2n.filename else None,
            file_fs=f_fs if f_fs and f_fs.filename else None,
            file_mb52=f_mb52 if f_mb52 and f_mb52.filename else None,
            file_pln=f_pln if f_pln and f_pln.filename else None,
            file_prd=f_prd if f_prd and f_prd.filename else None,
            exclude_new_status=exclude_new
        )
        if extra and extra[0]:
            CACHE["raw_dfs"] = extra[0]

        CACHE["data"] = res
        CACHE["dfs"] = (d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies)
        return safe_json_response(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/export-master-excel", methods=["GET"])
def export_master_excel():
    if CACHE["dfs"] is None:
        load_default_workspace_data()

    d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies = CACHE["dfs"]
    excel_stream = generate_master_excel_workbook(d_tim, d_me, d_fs, d_mb, d_lines, d_so, d_anomalies)
    
    return send_file(
        excel_stream,
        as_attachment=True,
        download_name="Consolidated_Supply_Chain_Intelligence_Master.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Unified Supply Chain Platform on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
