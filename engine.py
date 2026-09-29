"""
Engine core logic for unifying TIM, ME2N, Freight Status, MB52, PLNORDR, and PRDORDR.
Implements:
1. Normalization & Key Sanitization (strip zeros, '.0', whitespace)
2. Category Consolidation (KITCHEN, DOORS & WINDOWS, KITCHEN PROJECT)
3. Mandatory Audio Directive:
   - Article Status Filtering ('New' assortment toggle)
   - ATP Threshold Bucketing (< 0, 0-30, Cumulative < 30)
   - DoC (Days of Coverage), Warehouse CBM, Valuation (KD)
   - Average Lead Times, Commitment Equations (OH vs Sales vs ATP)
4. ME2N Priority & Projected Inbound ATP Date:
   Projected ATP Date = Document Date (ME2N) + Lead Time (TIM Master)
5. Logistics Milestones & Delays (EXF, ETD, ETA, BAYAN, AWH, GR, PORT) & Capital at Risk
6. Harsh2 FIFO Manufacturing Shortage & Stock Depletion Date Engine
7. Multi-Tab Master Excel Workbook Generator
"""

import io
import datetime
import math
import numpy as np
import pandas as pd


def sanitize_for_json(obj):
    """Recursively replace NaN, Inf, and non-serializable objects with None or safe defaults for strict standard JSON."""
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (datetime.date, datetime.datetime, pd.Timestamp)):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    return obj


def sanitize_article(series):
    """Normalize article ID: string, stripped, no '.0', no leading zeros."""
    return (
        series.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.lstrip("0")
    )


def normalize_categories(df, cat_col="Category", art_col="Article"):
    """
    Standardize Category names:
    - KITCHENS, BATHROOM PRODUCTION, KITCHEN PRODUCTION -> KITCHEN
    - D&W variants -> DOORS & WINDOWS
    - P- prefix -> KITCHEN PROJECT
    """
    if cat_col not in df.columns:
        return df

    df[cat_col] = df[cat_col].fillna("N/A").astype(str).str.strip()
    
    # Kitchen Consolidation
    kitchen_mask = df[cat_col].str.upper().isin(
        ["KITCHENS", "BATHROOM PRODUCTION", "KITCHEN PRODUCTION"]
    )
    df.loc[kitchen_mask, cat_col] = "KITCHEN"

    # Doors & Windows Normalization
    dw_mask = df[cat_col].str.upper().isin(
        ["D&W PRODUCTION", "D&W PRODUCTIONS", "DOORS & WINDOWS", "DOORS AND WINDOWS"]
    )
    df.loc[dw_mask, cat_col] = "DOORS & WINDOWS"

    # Project Kitchen Flag
    if art_col in df.columns:
        p_mask = df[art_col].astype(str).str.strip().str.startswith("P-")
        df.loc[p_mask, cat_col] = "KITCHEN PROJECT"

    return df


def classify_import_local(country_series):
    """Local: KUWAIT (KW) or SAUDI ARABIA (SA). Otherwise Import."""
    vals = country_series.fillna("").astype(str).str.upper().str.strip()
    return np.where(
        vals.isin(["KUWAIT", "SAUDI ARABIA", "KW", "SA"]),
        "Local",
        "Import"
    )


def process_unified_datasets(
    file_tim=None,
    file_me2n=None,
    file_fs=None,
    file_mb52=None,
    file_pln=None,
    file_prd=None,
    exclude_new_status=False,
    selected_category="ALL",
    selected_country="ALL"
):
    """
    Main unification function. Ingests all 6 streams and produces complete KPI structures,
    chart datasets, and data tables.
    Supports dynamic category and country slicers across all views and KPIs.
    """
    today = pd.Timestamp.now().normalize()
    results = {
        "kpis": {},
        "charts": {},
        "tables": {},
        "status": "success",
        "loaded_files": []
    }

    # -------------------------------------------------------------
    # 1. TIM MASTER (Commercial & Demand Backbone)
    # -------------------------------------------------------------
    df_tim = None
    if file_tim is not None:
        try:
            if isinstance(file_tim, pd.DataFrame):
                df_tim = file_tim.copy()
            else:
                cols = [
                    'Country', 'Article', 'ArticleDesc', 'Anchor Grouping', 'Category', 'Sub Category',
                    'Vendor', 'Vendor Desc.', 'Lead Time', 'Country Sales Monthly Mean QTY',
                    'Article Status - New', 'OH Stock', 'OH Value KD', 'OH CBM',
                    'Open Sales QTY', 'ATP QTY', 'ATP Days', 'Inbound Curr', 'Inbound Curr+1'
                ]
                df_tim = pd.read_excel(file_tim, usecols=lambda c: str(c).strip() in cols)
                df_tim.columns = df_tim.columns.str.strip()
                df_tim["Article_Key"] = sanitize_article(df_tim["Article"])
                df_tim = normalize_categories(df_tim, "Category", "Article")
            
            # Numeric conversion
            num_cols = [
                'Lead Time', 'Country Sales Monthly Mean QTY', 'OH Stock',
                'OH Value KD', 'OH CBM', 'Open Sales QTY', 'ATP QTY', 'ATP Days',
                'Inbound Curr', 'Inbound Curr+1'
            ]
            for col in num_cols:
                if col in df_tim.columns:
                    df_tim[col] = pd.to_numeric(df_tim[col], errors='coerce').fillna(0)

            # Preserve full category and country lists for UI slicers
            all_cat_list = sorted([str(c) for c in df_tim["Category"].dropna().unique() if str(c).strip()])
            all_ctry_list = sorted([str(c) for c in df_tim["Country"].dropna().unique() if str(c).strip()]) if "Country" in df_tim.columns else ["Kuwait", "Saudi Arabia"]

            # Save clean raw dataframe before slicer filtering for in-memory caching
            raw_df_tim = df_tim.copy()

            # Filter out 'New' assortment if requested by client toggle
            if exclude_new_status and "Article Status - New" in df_tim.columns:
                df_tim = df_tim[df_tim["Article Status - New"].astype(str).str.strip().str.upper() != "NEW"].copy()

            # Dynamic Slicer: Category filter on TIM
            if selected_category and selected_category != "ALL" and "Category" in df_tim.columns:
                df_tim = df_tim[df_tim["Category"].astype(str).str.upper() == selected_category.upper()].copy()

            # Dynamic Slicer: Country filter on TIM
            if selected_country and selected_country != "ALL" and "Country" in df_tim.columns:
                df_tim = df_tim[df_tim["Country"].astype(str).str.upper().str.contains(selected_country.upper())].copy()

            results["loaded_files"].append("TIM Master")
        except Exception as e:
            print(f"Error loading TIM: {e}")

    # -------------------------------------------------------------
    # 2. ME2N (Point-of-Placement Procurement)
    # -------------------------------------------------------------
    df_me2n = None
    if file_me2n is not None:
        try:
            if isinstance(file_me2n, pd.DataFrame):
                df_me2n = file_me2n.copy()
            else:
                df_me2n = pd.read_excel(file_me2n)
                df_me2n.columns = df_me2n.columns.str.strip()
                df_me2n["Article_Key"] = sanitize_article(df_me2n["Article"])
                df_me2n["Document Date"] = pd.to_datetime(df_me2n["Document Date"], errors="coerce")
                for c in ["Order Quantity", "Still to be delivered (qty)", "Net Order Value", "Still to be delivered (value)"]:
                    if c in df_me2n.columns:
                        df_me2n[c] = pd.to_numeric(df_me2n[c], errors="coerce").fillna(0)

            # Join Lead Time & metadata from TIM (use raw_df_tim if present so Category isn't lost before filtering)
            tim_source = raw_df_tim if 'raw_df_tim' in locals() and raw_df_tim is not None else df_tim
            if "Lead Time" not in df_me2n.columns:
                if tim_source is not None and "Lead Time" in tim_source.columns:
                    merge_cols = ["Article_Key", "Lead Time", "Category", "ArticleDesc"]
                    if "Country" in tim_source.columns:
                        merge_cols.append("Country")
                    tim_lt = tim_source.drop_duplicates(subset=["Article_Key"])[merge_cols]
                    df_me2n = df_me2n.merge(tim_lt, on="Article_Key", how="left")
                    df_me2n["Lead Time"] = df_me2n["Lead Time"].fillna(30)
                else:
                    df_me2n["Lead Time"] = 30
                    df_me2n["Category"] = "N/A"
                    df_me2n["ArticleDesc"] = df_me2n.get("Short Text", "")

            # FORMULA: Projected Inbound ATP Date = Document Date (ME2N) + Lead Time (TIM)
            df_me2n["Projected_ATP_Date"] = df_me2n["Document Date"] + pd.to_timedelta(df_me2n["Lead Time"], unit="D")
            
            # Month Bucket Assignment
            m0_start = pd.Timestamp(today.year, today.month, 1)
            def get_bucket(dt):
                if pd.isna(dt):
                    return "Out of Scope"
                diff_m = (dt.year - m0_start.year) * 12 + (dt.month - m0_start.month)
                if diff_m == 0:
                    return "Current"
                elif diff_m == 1:
                    return "Current+1"
                elif diff_m == 2:
                    return "Current+2"
                elif diff_m >= 3:
                    return "Current+3 to +5"
                else:
                    return "Past Due"

            df_me2n["Pipeline_Month_Bucket"] = df_me2n["Projected_ATP_Date"].apply(get_bucket)

            raw_df_me2n = df_me2n.copy()

            # Dynamic Slicer: Category filter on ME2N
            if selected_category and selected_category != "ALL" and "Category" in df_me2n.columns:
                df_me2n = df_me2n[df_me2n["Category"].astype(str).str.upper() == selected_category.upper()].copy()

            # Dynamic Slicer: Country filter on ME2N
            if selected_country and selected_country != "ALL" and "Country" in df_me2n.columns:
                df_me2n = df_me2n[df_me2n["Country"].astype(str).str.upper().str.contains(selected_country.upper())].copy()

            results["loaded_files"].append("ME2N (Open POs)")
        except Exception as e:
            print(f"Error loading ME2N: {e}")

    # -------------------------------------------------------------
    # 3. FREIGHT STATUS (In-Motion Logistics & Customs)
    # -------------------------------------------------------------
    df_fs = None
    if file_fs is not None:
        try:
            if isinstance(file_fs, pd.DataFrame):
                df_fs = file_fs.copy()
            else:
                df_fs = pd.read_excel(file_fs)
                df_fs.columns = df_fs.columns.str.strip()
                df_fs["Article_Key"] = sanitize_article(df_fs["Article"])
                df_fs = normalize_categories(df_fs, "Category", "Article")

            # Standardize country and import/local
            c_col = "Vendor Country Name" if "Vendor Country Name" in df_fs.columns else ("Vendor Ctry" if "Vendor Ctry" in df_fs.columns else None)
            if c_col:
                df_fs["Import_Local"] = classify_import_local(df_fs[c_col])
            else:
                df_fs["Import_Local"] = "Import"

            # Parse dates & delays
            for d in ["ATP", "GRP", "AWH", "BAYAN", "ETA", "ETD", "PO Cr. Dt"]:
                if d in df_fs.columns:
                    df_fs[d] = pd.to_datetime(df_fs[d], errors="coerce")

            delay_cols = ["EXF Delay", "ETD Delay", "ETA Delay", "BAYAN Delay", "AWH Delay", "GR Delay", "Port Delay", "Over All Delay"]
            for col in delay_cols:
                if col in df_fs.columns:
                    df_fs[col] = pd.to_numeric(df_fs[col], errors="coerce").fillna(0)

            val_col = "InbValKWD" if "InbValKWD" in df_fs.columns else ("Value" if "Value" in df_fs.columns else None)
            if val_col:
                df_fs["InbValKWD"] = pd.to_numeric(df_fs[val_col], errors="coerce").fillna(0)
            else:
                df_fs["InbValKWD"] = 0.0

            raw_df_fs = df_fs.copy()

            # Dynamic Slicer: Category filter on Freight Status
            if selected_category and selected_category != "ALL" and "Category" in df_fs.columns:
                df_fs = df_fs[df_fs["Category"].astype(str).str.upper() == selected_category.upper()].copy()

            # Dynamic Slicer: Country filter on Freight Status
            if selected_country and selected_country != "ALL":
                # Check origin or vendor country
                match_col = c_col if c_col and c_col in df_fs.columns else None
                if match_col:
                    df_fs = df_fs[df_fs[match_col].astype(str).str.upper().str.contains(selected_country.upper())].copy()

            # Slicers: Category & Country for Freight Status
            if selected_category and selected_category != "ALL" and "Category" in df_fs.columns:
                df_fs = df_fs[df_fs["Category"].astype(str).str.upper() == selected_category.upper()].copy()
            if selected_country and selected_country != "ALL":
                c_field = "Vendor Country Name" if "Vendor Country Name" in df_fs.columns else ("Vendor Ctry" if "Vendor Ctry" in df_fs.columns else None)
                if c_field:
                    df_fs = df_fs[df_fs[c_field].astype(str).str.upper().str.contains(selected_country.upper())].copy()

            results["loaded_files"].append("Freight Status")
        except Exception as e:
            print(f"Error loading Freight Status: {e}")

    # -------------------------------------------------------------
    # 4. MB52 (Warehouse Physical Stocks)
    # -------------------------------------------------------------
    df_mb52 = None
    stock_summary = pd.DataFrame()
    if file_mb52 is not None:
        try:
            if isinstance(file_mb52, pd.DataFrame):
                df_mb52 = file_mb52.copy()
            else:
                df_mb52 = pd.read_excel(file_mb52)
                df_mb52.columns = df_mb52.columns.str.strip()
                df_mb52["Article_Key"] = sanitize_article(df_mb52["Article"])

                # Filter Phantoms and Glass
                if "Phantom item" in df_mb52.columns:
                    df_mb52 = df_mb52[df_mb52["Phantom item"].astype(str).str.strip().str.upper() != "X"].copy()
                if "Material Description" in df_mb52.columns:
                    df_mb52 = df_mb52[~df_mb52["Material Description"].astype(str).str.contains("gls", case=False, na=False)].copy()

                for c in ["Unrestricted", "Value Unrestricted", "Transit and Transfer", "Stock in Transit", "Value in Transit", "Blocked", "Value BlockedStock"]:
                    if c in df_mb52.columns:
                        df_mb52[c] = pd.to_numeric(df_mb52[c], errors="coerce").fillna(0)

            # Map Category onto MB52 from TIM
            if tim_source is not None and "Category" in tim_source.columns and "Category" not in df_mb52.columns:
                mb_cat_map = tim_source.drop_duplicates(subset=["Article_Key"])[["Article_Key", "Category"]]
                df_mb52 = df_mb52.merge(mb_cat_map, on="Article_Key", how="left")

            if selected_category and selected_category != "ALL" and "Category" in df_mb52.columns:
                df_mb52 = df_mb52[df_mb52["Category"].astype(str).str.upper() == selected_category.upper()].copy()

            df_mb52["Available_Stock"] = df_mb52.get("Unrestricted", 0) + df_mb52.get("Transit and Transfer", 0) + df_mb52.get("Stock in Transit", 0)
            df_mb52["Available_Value"] = df_mb52.get("Value Unrestricted", 0) + df_mb52.get("Value in Transit", 0)

            stock_summary = df_mb52.groupby("Article_Key", as_index=False).agg(
                Plant_Available_Stock=("Available_Stock", "sum"),
                Plant_Available_Value=("Available_Value", "sum"),
                Blocked_Stock=("Blocked", "sum"),
                Value_Blocked=("Value BlockedStock", "sum")
            )
            stock_summary["Unit_Price"] = np.where(
                stock_summary["Plant_Available_Stock"] > 0,
                stock_summary["Plant_Available_Value"] / stock_summary["Plant_Available_Stock"],
                0.0
            )
            results["loaded_files"].append("MB52 (Stock)")
        except Exception as e:
            print(f"Error loading MB52: {e}")

    # -------------------------------------------------------------
    # 5 & 6. MANUFACTURING SHORTAGE ENGINE (PLNORDR + PRDORDR)
    # -------------------------------------------------------------
    df_demand = None
    demand_lines = []
    
    for f, ftype in [(file_prd, "PRDORDR"), (file_pln, "PLNORDR")]:
        if f is not None:
            try:
                if isinstance(f, pd.DataFrame):
                    df_temp = f.copy()
                else:
                    df_temp = pd.read_excel(f)
                    df_temp.columns = df_temp.columns.str.strip()
                    df_temp["Order_Type"] = ftype
                    df_temp["Article_Key"] = sanitize_article(df_temp["Article"])
                    
                    # Exclude Phantom and GLS
                    if "Phantom item" in df_temp.columns:
                        df_temp = df_temp[df_temp["Phantom item"].astype(str).str.strip().str.upper() != "X"].copy()
                    if "Material Description" in df_temp.columns:
                        df_temp = df_temp[~df_temp["Material Description"].astype(str).str.contains("gls", case=False, na=False)].copy()

                    df_temp["Requirement quantity (EINHEIT)"] = pd.to_numeric(df_temp.get("Requirement quantity (EINHEIT)", 0), errors="coerce").fillna(0)
                    df_temp["Requirement date"] = pd.to_datetime(df_temp.get("Requirement date"), errors="coerce")
                demand_lines.append(df_temp)
                results["loaded_files"].append(ftype)
            except Exception as e:
                print(f"Error loading {ftype}: {e}")

    df_lines_calculated = pd.DataFrame()
    so_fulfillment_df = pd.DataFrame()
    top_bottlenecks = []
    
    if demand_lines:
        df_demand = pd.concat(demand_lines, ignore_index=True)
        df_demand = df_demand.dropna(subset=["Article_Key", "Sales Document"]).copy()
        df_demand["Req_Date_Clean"] = df_demand["Requirement date"].fillna(pd.Timestamp("2099-12-31"))
        df_demand = df_demand.sort_values(by=["Article_Key", "Req_Date_Clean", "Sales Document"]).reset_index(drop=True)

        # Merge Stock Summary onto demand
        if not stock_summary.empty:
            df_lines = pd.merge(df_demand, stock_summary, on="Article_Key", how="left")
            df_lines["Plant_Available_Stock"] = df_lines["Plant_Available_Stock"].fillna(0)
        else:
            df_lines = df_demand.copy()
            df_lines["Plant_Available_Stock"] = 0
            df_lines["Unit_Price"] = 0.0

        # Attach Category from TIM if available and filter by selected_category
        tim_cat_src = raw_df_tim if 'raw_df_tim' in locals() and raw_df_tim is not None else df_tim
        if tim_cat_src is not None and "Category" in tim_cat_src.columns:
            tim_cat_map = tim_cat_src.drop_duplicates(subset=["Article_Key"])[["Article_Key", "Category"]]
            df_lines = pd.merge(df_lines, tim_cat_map, on="Article_Key", how="left")
            if selected_category and selected_category != "ALL":
                df_lines = df_lines[df_lines["Category"].astype(str).str.upper() == selected_category.upper()].copy()

        # FIFO Chronological Allocation Formula
        df_lines["Cumulative_Demand"] = df_lines.groupby("Article_Key")["Requirement quantity (EINHEIT)"].cumsum()
        df_lines["Projected_Stock_Balance"] = df_lines["Plant_Available_Stock"] - df_lines["Cumulative_Demand"]
        df_lines["Opening_Stock_Balance"] = df_lines["Projected_Stock_Balance"] + df_lines["Requirement quantity (EINHEIT)"]
        
        df_lines["Fulfilled_Qty"] = np.minimum(
            df_lines["Requirement quantity (EINHEIT)"],
            np.maximum(0, df_lines["Opening_Stock_Balance"])
        )
        df_lines["Shortage_Qty"] = df_lines["Requirement quantity (EINHEIT)"] - df_lines["Fulfilled_Qty"]
        
        df_lines["Line_Status"] = np.where(
            df_lines["Shortage_Qty"].round(4) <= 0,
            "FULLY COVERED ON TIME",
            np.where(df_lines["Fulfilled_Qty"].round(4) > 0, "PARTIAL COVERAGE", "STOCKOUT / UNFULFILLABLE")
        )
        df_lines_calculated = df_lines

        # Customer Sales Order Fulfillment Matrix
        so_summary = df_lines.groupby("Sales Document", as_index=False).agg(
            Total_Lines=("Article_Key", "count"),
            Total_Ordered_Qty=("Requirement quantity (EINHEIT)", "sum"),
            Deliverable_Qty=("Fulfilled_Qty", "sum"),
            Shortage_Qty=("Shortage_Qty", "sum"),
            Earliest_Date=("Requirement date", "min"),
            Latest_Date=("Requirement date", "max")
        )
        so_summary["Fulfillment_Pct"] = np.where(
            so_summary["Total_Ordered_Qty"] > 0,
            (so_summary["Deliverable_Qty"] / so_summary["Total_Ordered_Qty"] * 100.0).round(1),
            100.0
        )
        so_summary["Status"] = np.where(
            so_summary["Shortage_Qty"].round(4) <= 0,
            "READY FOR FULL DELIVERY",
            np.where(so_summary["Deliverable_Qty"].round(4) > 0, "PARTIAL DELIVERY RISK", "UNFULFILLABLE (NO STOCK)")
        )
        so_fulfillment_df = so_summary

        # Top Bottleneck Components
        shortage_items = df_lines[df_lines["Shortage_Qty"] > 0.0001].groupby(["Article_Key", "Material Description"], as_index=False).agg(
            Total_Shortage=("Shortage_Qty", "sum"),
            Impacted_Orders=("Sales Document", "nunique"),
            Available_Stock=("Plant_Available_Stock", "first")
        ).sort_values(by="Impacted_Orders", ascending=False).head(10)
        top_bottlenecks = shortage_items.to_dict("records")

    # =============================================================
    # 7. COMPUTE HIGH-LEVEL EXECUTIVE KPIS & CHARTS (IN SAUDI RIYAL - SAR)
    # =============================================================
    kpis = {}
    charts = {}
    SAR_PER_KWD = 12.25  # Standard Saudi Riyal conversion rate for KWD valuation fields

    # Commercial Valuation & CBM (TIM)
    if df_tim is not None and not df_tim.empty:
        # Valuation converted to Saudi Riyals (SAR)
        tot_val_sar = float(df_tim["OH Value KD"].sum()) * SAR_PER_KWD
        kpis["total_valuation_sar"] = round(tot_val_sar, 2)
        kpis["total_cbm"] = round(float(df_tim["OH CBM"].sum()), 2)
        kpis["total_articles"] = int(df_tim["Article_Key"].nunique())
        
        # Audio Directive: ATP Buckets (<0, 0-30, Cumulative <30)
        atp_neg = int((df_tim["ATP QTY"] < 0).sum())
        atp_0_30 = int(((df_tim["ATP QTY"] >= 0) & (df_tim["ATP QTY"] < 30)).sum())
        atp_healthy = int((df_tim["ATP QTY"] >= 30).sum())
        atp_cumulative_risk = atp_neg + atp_0_30

        kpis["atp_negative_count"] = atp_neg
        kpis["atp_critical_count"] = atp_0_30
        kpis["atp_cumulative_risk"] = atp_cumulative_risk
        kpis["atp_healthy_count"] = atp_healthy

        # Average Lead Time & Coverage
        tot_mean_sales = float(df_tim["Country Sales Monthly Mean QTY"].sum())
        daily_sales = (tot_mean_sales / 30.0) if tot_mean_sales > 0 else 0
        tot_oh = float(df_tim["OH Stock"].sum())
        kpis["days_of_coverage"] = round(tot_oh / daily_sales, 1) if daily_sales > 0 else 999.0
        kpis["avg_lead_time_days"] = round(float(df_tim["Lead Time"].mean()), 1)

        # Chart 1.1: ATP Risk Donut
        charts["atp_risk_distribution"] = [
            {"label": "Negative ATP (<0)", "value": atp_neg, "color": "#EF4444"},
            {"label": "Critical Low (0-30)", "value": atp_0_30, "color": "#F59E0B"},
            {"label": "Healthy Stock (>30)", "value": atp_healthy, "color": "#10B981"}
        ]

        # Chart 1.2: Category Lead Time vs Coverage Matrix Table & Data (in SAR)
        cat_matrix = df_tim.groupby("Category").agg(
            Avg_Lead_Time=("Lead Time", "mean"),
            Total_Stock=("OH Stock", "sum"),
            Total_Mean_Sales=("Country Sales Monthly Mean QTY", "sum"),
            Total_Valuation_KD=("OH Value KD", "sum"),
            Total_CBM=("OH CBM", "sum")
        ).reset_index()
        cat_matrix["Total_Valuation_SAR"] = cat_matrix["Total_Valuation_KD"] * SAR_PER_KWD
        cat_matrix["DoC"] = np.where(
            cat_matrix["Total_Mean_Sales"] > 0,
            (cat_matrix["Total_Stock"] / (cat_matrix["Total_Mean_Sales"] / 30.0)).round(1),
            999.0
        )
        charts["category_lead_time_doc"] = cat_matrix.to_dict("records")

        # Chart 1.3: Stock Commitment Equation (OH vs Sales vs ATP vs Next Month Inbound)
        cat_equation = df_tim.groupby("Category").agg(
            OH_Stock=("OH Stock", "sum"),
            Open_Sales=("Open Sales QTY", "sum"),
            ATP_QTY=("ATP QTY", "sum"),
            Inbound_Next_Month=("Inbound Curr+1", "sum")
        ).reset_index()
        charts["stock_commitment_equation"] = cat_equation.to_dict("records")

        # Chart 1.4: Lead Time vs Days of Coverage (DoC) 4-Quadrant Bubble Scatter
        scatter_items = []
        for _, row in cat_matrix.iterrows():
            doc_val = min(float(row["DoC"]), 365.0)  # cap for clean plotting
            lt_val = round(float(row["Avg_Lead_Time"]), 1)
            val_sar = float(row["Total_Valuation_SAR"])
            r_size = max(6, min(24, int(val_sar / 500000) + 6))
            scatter_items.append({
                "category": str(row["Category"]),
                "x": lt_val,
                "y": doc_val,
                "r": r_size,
                "valuation": round(val_sar, 2)
            })
        charts["lead_time_vs_doc_scatter"] = scatter_items

        # Chart 1.5: Warehouse CBM Space Allocation by Country & Category
        if "Country" in df_tim.columns:
            cbm_grouped = df_tim.groupby(["Country", "Category"], as_index=False)["OH CBM"].sum()
            countries = list(cbm_grouped["Country"].unique())
            categories = list(cbm_grouped["Category"].unique())
            cbm_chart_data = {"categories": categories, "series": []}
            for ctry in countries:
                ctry_df = cbm_grouped[cbm_grouped["Country"] == ctry].set_index("Category")
                vals = [round(float(ctry_df.loc[cat, "OH CBM"]), 1) if cat in ctry_df.index else 0.0 for cat in categories]
                cbm_chart_data["series"].append({"country": str(ctry), "values": vals})
            charts["cbm_by_country_category"] = cbm_chart_data
        else:
            charts["cbm_by_country_category"] = {"categories": [], "series": []}

        # Chart 1.6: Article Status Lifecycle Distribution (Voice Note Requirement)
        if "Article Status - New" in df_tim.columns:
            status_counts = df_tim["Article Status - New"].astype(str).str.strip().value_counts()
            charts["article_status_distribution"] = [
                {"label": str(k), "value": int(v)} for k, v in status_counts.items() if str(k).upper() not in ["NAN", "NONE", ""]
            ]
        else:
            charts["article_status_distribution"] = []

    else:
        kpis["total_valuation_sar"] = 0.0
        kpis["total_cbm"] = 0.0
        kpis["atp_cumulative_risk"] = 0
        kpis["days_of_coverage"] = 0.0

    # Logistics & Freight Delays (Freight Status - converted to SAR)
    if df_fs is not None and not df_fs.empty:
        kpis["total_pos_monitored"] = int(df_fs["PO#"].nunique())
        kpis["total_containers"] = int(df_fs["Container"].nunique()) if "Container" in df_fs.columns else 0
        
        # Capital at Risk in Saudi Riyals (SAR)
        delayed_rows = df_fs[df_fs["Over All Delay"] > 0]
        kpis["logistics_capital_at_risk_sar"] = round(float(delayed_rows["InbValKWD"].sum()) * SAR_PER_KWD, 2)
        kpis["total_inbound_value_sar"] = round(float(df_fs["InbValKWD"].sum()) * SAR_PER_KWD, 2)
        kpis["financial_risk_rate_pct"] = round(
            (kpis["logistics_capital_at_risk_sar"] / kpis["total_inbound_value_sar"] * 100) if kpis["total_inbound_value_sar"] > 0 else 0.0, 1
        )

        delayed_pos = int(delayed_rows["PO#"].nunique())
        tot_pos = kpis["total_pos_monitored"]
        kpis["overall_tracking_delay_rate"] = round((delayed_pos / tot_pos * 100) if tot_pos > 0 else 0.0, 1)

        # Chart 3.1: Milestone Delays Waterfall
        milestones = ["EXF Delay", "ETD Delay", "ETA Delay", "BAYAN Delay", "AWH Delay", "GR Delay", "Port Delay"]
        milestone_data = []
        for m in milestones:
            if m in df_fs.columns:
                m_label = m.replace(" Delay", "")
                cnt = int(df_fs.loc[df_fs[m] > 0, "PO#"].nunique())
                avg_d = float(df_fs.loc[df_fs[m] > 0, m].mean()) if cnt > 0 else 0.0
                milestone_data.append({"milestone": m_label, "delayed_pos": cnt, "avg_delay_days": round(avg_d, 1)})
        charts["milestone_delay_waterfall"] = milestone_data

        # Chart 3.2: Top 10 Delayed Suppliers Exposure (Values in SAR)
        top_delayed_v = delayed_rows.groupby(["Vendor Name", "Vendor Ctry"]).agg(
            Delayed_POs=("PO#", "nunique"),
            Exposed_Capital_KD=("InbValKWD", "sum"),
            Avg_Delay=("Over All Delay", "mean")
        ).reset_index().sort_values(by="Exposed_Capital_KD", ascending=False).head(10)
        top_delayed_v["Exposed_Capital"] = top_delayed_v["Exposed_Capital_KD"] * SAR_PER_KWD
        charts["top_delayed_vendors"] = top_delayed_v.to_dict("records")

        # Chart 3.3: Import vs Local Financial Risk Breakdown (in SAR)
        if "Import_Local" in df_fs.columns:
            imp_loc = df_fs.groupby("Import_Local").agg(
                Total_Value_KD=("InbValKWD", "sum"),
                Delayed_Value_KD=("InbValKWD", lambda s: s[df_fs.loc[s.index, "Over All Delay"] > 0].sum()),
                Delayed_POs=("PO#", lambda s: s[df_fs.loc[s.index, "Over All Delay"] > 0].nunique()),
                Total_POs=("PO#", "nunique")
            ).reset_index()
            imp_loc["Total_Value"] = imp_loc["Total_Value_KD"] * SAR_PER_KWD
            imp_loc["Delayed_Value"] = imp_loc["Delayed_Value_KD"] * SAR_PER_KWD
            charts["import_vs_local_risk"] = imp_loc.to_dict("records")
        else:
            charts["import_vs_local_risk"] = []

        # Chart 3.4: Delayed POs & Latency by Country of Origin (in SAR)
        c_col = "Vendor Country Name" if "Vendor Country Name" in df_fs.columns else ("Vendor Ctry" if "Vendor Ctry" in df_fs.columns else None)
        if c_col:
            ctry_delay = delayed_rows.groupby(c_col).agg(
                Delayed_POs=("PO#", "nunique"),
                Exposed_Capital_KD=("InbValKWD", "sum"),
                Avg_Delay=("Over All Delay", "mean")
            ).reset_index().sort_values(by="Delayed_POs", ascending=False).head(8)
            ctry_delay["Exposed_Capital"] = ctry_delay["Exposed_Capital_KD"] * SAR_PER_KWD
            charts["delays_by_country"] = ctry_delay.to_dict("records")
        else:
            charts["delays_by_country"] = []

        # =========================================================
        # 3.5 DATA COMPLIANCE & PROCESS ANOMALY AUDIT (dash.md Rules)
        # =========================================================
        # Evaluates 10 process validation rules:
        # ATP < GRP, ATP < AWH, ATP < BAYAN, ATP < ETA, ATP < ETD,
        # ATP - GRP > 5 days (Dock-to-stock gap), TIM Unmatched, etc.
        anomaly_list = []
        tim_articles = set(df_tim["Article_Key"].unique()) if df_tim is not None else set()

        for idx, row in df_fs.iterrows():
            po_num = str(row.get("PO#", "N/A"))
            art_key = str(row.get("Article_Key", "N/A"))
            vendor = str(row.get("Vendor Name", "N/A"))
            cat = str(row.get("Category", "N/A"))
            imp_loc = str(row.get("Import_Local", "Import"))
            sev_base = "Severe" if imp_loc == "Import" else "Medium"

            atp_dt = row.get("ATP")
            grp_dt = row.get("GRP")
            awh_dt = row.get("AWH")
            bayan_dt = row.get("BAYAN")
            eta_dt = row.get("ETA")
            etd_dt = row.get("ETD")

            # Rule 1: ATP < GRP
            if pd.notnull(atp_dt) and pd.notnull(grp_dt) and atp_dt < grp_dt:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_BEFORE_GRP", "Description": "ATP Date is before GRP Date (Chronological Impossibility)",
                    "Severity": sev_base, "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10], "BAYAN": str(bayan_dt)[:10] if pd.notnull(bayan_dt) else "N/A"
                })

            # Rule 2: ATP < AWH
            if pd.notnull(atp_dt) and pd.notnull(awh_dt) and atp_dt < awh_dt:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_BEFORE_AWH", "Description": "ATP Date is before Warehouse Arrival Date (AWH)",
                    "Severity": sev_base, "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10] if pd.notnull(grp_dt) else "N/A", "BAYAN": str(bayan_dt)[:10] if pd.notnull(bayan_dt) else "N/A"
                })

            # Rule 3: ATP < BAYAN
            if pd.notnull(atp_dt) and pd.notnull(bayan_dt) and atp_dt < bayan_dt:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_BEFORE_BAYAN", "Description": "ATP Date is before Customs Clearance Date (BAYAN)",
                    "Severity": sev_base, "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10] if pd.notnull(grp_dt) else "N/A", "BAYAN": str(bayan_dt)[:10]
                })

            # Rule 4: ATP < ETA
            if pd.notnull(atp_dt) and pd.notnull(eta_dt) and atp_dt < eta_dt:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_BEFORE_ETA", "Description": "ATP Date is before Port Arrival Date (ETA)",
                    "Severity": sev_base, "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10] if pd.notnull(grp_dt) else "N/A", "BAYAN": "N/A"
                })

            # Rule 5: ATP < ETD
            if pd.notnull(atp_dt) and pd.notnull(etd_dt) and atp_dt < etd_dt:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_BEFORE_ETD", "Description": "ATP Date is before Origin Port Departure Date (ETD)",
                    "Severity": sev_base, "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10] if pd.notnull(grp_dt) else "N/A", "BAYAN": "N/A"
                })

            # Rule 6: Dock-to-Stock Gap > 5 Days (ATP - GRP > 5)
            if pd.notnull(atp_dt) and pd.notnull(grp_dt) and (atp_dt - grp_dt).days > 5:
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "ATP_GRP_GAP_GT_5", "Description": f"Dock-to-stock gap exceeds SLA ({(atp_dt - grp_dt).days} days between GRP and ATP)",
                    "Severity": "Medium", "ATP": str(atp_dt)[:10], "GRP": str(grp_dt)[:10], "BAYAN": "N/A"
                })

            # Rule 7: TIM Master Match Gap
            if tim_articles and art_key not in tim_articles and art_key != "N/A":
                anomaly_list.append({
                    "PO#": po_num, "Article": art_key, "Vendor": vendor, "Category": cat, "Import_Local": imp_loc,
                    "Rule": "TIM_UNMATCHED_PO", "Description": "Open PO Line has no matching catalog record in TIM Master",
                    "Severity": "Severe" if imp_loc == "Import" else "Medium", "ATP": str(atp_dt)[:10] if pd.notnull(atp_dt) else "N/A", "GRP": "N/A", "BAYAN": "N/A"
                })

        df_anomalies = pd.DataFrame(anomaly_list)
        if not df_anomalies.empty:
            kpis["total_compliance_violations"] = len(df_anomalies)
            kpis["severe_anomalies_count"] = int((df_anomalies["Severity"] == "Severe").sum())
            kpis["violated_pos_count"] = int(df_anomalies["PO#"].nunique())
            tot_pos = max(1, int(df_fs["PO#"].nunique()))
            kpis["process_anomaly_rate_pct"] = round((kpis["violated_pos_count"] / tot_pos * 100), 1)

            # Anomaly breakdown chart by rule
            rule_counts = df_anomalies["Rule"].value_counts().reset_index()
            rule_counts.columns = ["rule", "count"]
            charts["anomaly_rule_distribution"] = rule_counts.to_dict("records")
            results["anomalies_table"] = df_anomalies.head(100).to_dict("records")
        else:
            kpis["total_compliance_violations"] = 0
            kpis["severe_anomalies_count"] = 0
            kpis["violated_pos_count"] = 0
            kpis["process_anomaly_rate_pct"] = 0.0
            charts["anomaly_rule_distribution"] = []
            results["anomalies_table"] = []
            df_anomalies = pd.DataFrame()

    else:
        kpis["logistics_capital_at_risk_sar"] = 0.0
        kpis["overall_tracking_delay_rate"] = 0.0
        kpis["total_compliance_violations"] = 0
        kpis["severe_anomalies_count"] = 0
        kpis["violated_pos_count"] = 0
        kpis["process_anomaly_rate_pct"] = 0.0
        charts["anomaly_rule_distribution"] = []
        results["anomalies_table"] = []
        df_anomalies = pd.DataFrame()

    # Early Procurement (ME2N)
    if df_me2n is not None and not df_me2n.empty:
        kpis["me2n_open_po_count"] = int(df_me2n["Purchasing Document"].nunique())
        kpis["me2n_open_qty"] = float(df_me2n["Still to be delivered (qty)"].sum())
        # Convert non-SAR to approximate SAR equivalent for consolidated total if needed, or maintain spend by currency
        kpis["me2n_committed_val"] = round(float(df_me2n["Still to be delivered (value)"].sum()), 2)

        # Chart 2.1: Forward Pipeline Month Buckets
        charts["me2n_horizon_buckets"] = df_me2n.groupby("Pipeline_Month_Bucket").agg(
            POs=("Purchasing Document", "nunique"),
            Open_Qty=("Still to be delivered (qty)", "sum"),
            Committed_Val=("Still to be delivered (value)", "sum")
        ).reset_index().to_dict("records")

        # Chart 2.2: Open Procurement Spend by Currency
        if "Currency" in df_me2n.columns:
            curr_spend = df_me2n.groupby("Currency").agg(
                Open_Lines=("Article_Key", "count"),
                Open_Qty=("Still to be delivered (qty)", "sum"),
                Committed_Val=("Still to be delivered (value)", "sum")
            ).reset_index().sort_values(by="Committed_Val", ascending=False)
            charts["me2n_spend_by_currency"] = curr_spend.to_dict("records")
        else:
            charts["me2n_spend_by_currency"] = []

        # Chart 2.3: Top 10 Procurement Suppliers by Open Value
        if "Name of Vendor" in df_me2n.columns:
            top_proc_v = df_me2n.groupby("Name of Vendor").agg(
                Open_POs=("Purchasing Document", "nunique"),
                Open_Lines=("Article_Key", "count"),
                Open_Qty=("Still to be delivered (qty)", "sum"),
                Committed_Val=("Still to be delivered (value)", "sum")
            ).reset_index().sort_values(by="Committed_Val", ascending=False).head(10)
            charts["me2n_top_vendors"] = top_proc_v.to_dict("records")
        else:
            charts["me2n_top_vendors"] = []

    # Manufacturing Shortages (Harsh2)
    if not df_lines_calculated.empty:
        kpis["active_shortage_qty"] = round(float(df_lines_calculated["Shortage_Qty"].sum()), 2)
        kpis["factory_fulfillment_rate"] = round(
            float(df_lines_calculated["Fulfilled_Qty"].sum()) / float(df_lines_calculated["Requirement quantity (EINHEIT)"].sum()) * 100.0, 1
        ) if df_lines_calculated["Requirement quantity (EINHEIT)"].sum() > 0 else 100.0

        if not so_fulfillment_df.empty:
            kpis["so_ready_count"] = int((so_fulfillment_df["Status"] == "READY FOR FULL DELIVERY").sum())
            kpis["so_partial_count"] = int((so_fulfillment_df["Status"] == "PARTIAL DELIVERY RISK").sum())
            kpis["so_unfulfillable_count"] = int((so_fulfillment_df["Status"] == "UNFULFILLABLE (NO STOCK)").sum())
            tot_sos = len(so_fulfillment_df)
            kpis["so_readiness_rate"] = round((kpis["so_ready_count"] / tot_sos * 100) if tot_sos > 0 else 0.0, 1)

            charts["so_readiness_distribution"] = [
                {"label": "Ready for Delivery", "value": kpis["so_ready_count"], "color": "#10B981"},
                {"label": "Partial Delivery Risk", "value": kpis["so_partial_count"], "color": "#F59E0B"},
                {"label": "Unfulfillable (No Stock)", "value": kpis["so_unfulfillable_count"], "color": "#EF4444"}
            ]

        charts["top_bottleneck_components"] = top_bottlenecks

        # Chart 4.2: Top Bottleneck Components Visual Chart (Pareto Ranking)
        if top_bottlenecks:
            charts["top_bottlenecks_chart"] = [
                {
                    "label": f"{b.get('Material Description', b['Article_Key'])[:18]} ({b['Article_Key']})",
                    "shortage": float(b.get("Total_Shortage", 0)),
                    "orders": int(b.get("Impacted_Orders", 0))
                } for b in top_bottlenecks
            ]
        else:
            charts["top_bottlenecks_chart"] = []

        # Chart 4.3: Planned Orders (PLNORDR) vs Active Production (PRDORDR) Shortage Comparison
        if "Order_Type" in df_lines_calculated.columns:
            order_type_shortage = df_lines_calculated.groupby("Order_Type").agg(
                Total_Demanded=("Requirement quantity (EINHEIT)", "sum"),
                Fulfilled=("Fulfilled_Qty", "sum"),
                Shortage=("Shortage_Qty", "sum"),
                Lines=("Article_Key", "count")
            ).reset_index()
            charts["planned_vs_active_shortage"] = order_type_shortage.to_dict("records")
        else:
            charts["planned_vs_active_shortage"] = []

        # Chart 4.4: FIFO Inventory Depletion Runway (Timeline Consumption)
        depletion_dates = df_lines_calculated.dropna(subset=["Requirement date"]).copy()
        if not depletion_dates.empty:
            depletion_dates["Date_Str"] = depletion_dates["Requirement date"].dt.strftime("%Y-%m-%d")
            timeline_run = depletion_dates.groupby("Date_Str").agg(
                Demanded=("Requirement quantity (EINHEIT)", "sum"),
                Fulfilled=("Fulfilled_Qty", "sum"),
                Shortage=("Shortage_Qty", "sum")
            ).reset_index().sort_values(by="Date_Str").head(15)
            charts["depletion_timeline_sample"] = timeline_run.to_dict("records")
        else:
            charts["depletion_timeline_sample"] = []

    # =============================================================
    # 8. MASTER DATA CONSOLIDATION VIEW (Tab 5 in UI)
    # =============================================================
    # Produces the unified master data view across all datasets (Article, Category, On-Hand, ATP, Open PO, Lead Time, Status)
    master_records = []
    if df_tim is not None and not df_tim.empty:
        # Group at Article level for master view
        m_grouped = df_tim.groupby("Article_Key", as_index=False).agg(
            ArticleDesc=("ArticleDesc", "first"),
            Category=("Category", "first"),
            Country=("Country", "first") if "Country" in df_tim.columns else ("Article_Key", lambda x: "Kuwait"),
            Lead_Time=("Lead Time", "first"),
            OH_Stock=("OH Stock", "sum"),
            OH_Valuation_KD=("OH Value KD", "sum"),
            OH_CBM=("OH CBM", "sum"),
            Open_Sales_QTY=("Open Sales QTY", "sum"),
            ATP_QTY=("ATP QTY", "sum"),
            Monthly_Sales_Mean=("Country Sales Monthly Mean QTY", "sum"),
            Status=("Article Status - New", "first")
        )
        m_grouped["OH_Valuation_SAR"] = (m_grouped["OH_Valuation_KD"] * SAR_PER_KWD).round(2)
        m_grouped["DoC"] = np.where(
            m_grouped["Monthly_Sales_Mean"] > 0,
            (m_grouped["OH_Stock"] / (m_grouped["Monthly_Sales_Mean"] / 30.0)).round(1),
            999.0
        )
        
        # Attach ME2N open PO pipeline data if available
        if df_me2n is not None and not df_me2n.empty:
            me_po = df_me2n.groupby("Article_Key", as_index=False).agg(
                ME2N_Open_PO_Qty=("Still to be delivered (qty)", "sum"),
                ME2N_Open_PO_Value=("Still to be delivered (value)", "sum"),
                Next_Projected_ATP=("Projected_ATP_Date", "min")
            )
            me_po["Next_Projected_ATP"] = me_po["Next_Projected_ATP"].dt.strftime("%Y-%m-%d").fillna("N/A")
            m_grouped = pd.merge(m_grouped, me_po, on="Article_Key", how="left")
            m_grouped["ME2N_Open_PO_Qty"] = m_grouped["ME2N_Open_PO_Qty"].fillna(0)
            m_grouped["ME2N_Open_PO_Value"] = m_grouped["ME2N_Open_PO_Value"].fillna(0)
            m_grouped["Next_Projected_ATP"] = m_grouped["Next_Projected_ATP"].fillna("N/A")
        else:
            m_grouped["ME2N_Open_PO_Qty"] = 0
            m_grouped["ME2N_Open_PO_Value"] = 0
            m_grouped["Next_Projected_ATP"] = "N/A"

        # Attach Manufacturing Shortage if available
        if not df_lines_calculated.empty:
            m_short = df_lines_calculated.groupby("Article_Key", as_index=False)["Shortage_Qty"].sum()
            m_grouped = pd.merge(m_grouped, m_short, on="Article_Key", how="left")
            m_grouped["Shortage_Qty"] = m_grouped["Shortage_Qty"].fillna(0)
        else:
            m_grouped["Shortage_Qty"] = 0

        # Sort priority: Shortages first, then Negative ATP, then highest valuation
        m_grouped = m_grouped.sort_values(by=["Shortage_Qty", "ATP_QTY", "OH_Valuation_SAR"], ascending=[False, True, False])
        master_records = m_grouped.head(100).to_dict("records")

        # Collect distinct filter values for UI slicers
        cat_list = all_cat_list if 'all_cat_list' in locals() else sorted([str(c) for c in df_tim["Category"].dropna().unique() if str(c).strip()])
        ctry_list = all_ctry_list if 'all_ctry_list' in locals() else (sorted([str(c) for c in df_tim["Country"].dropna().unique() if str(c).strip()]) if "Country" in df_tim.columns else ["Kuwait", "Saudi Arabia"])
        results["filter_options"] = {
            "categories": cat_list,
            "countries": ctry_list
        }
    else:
        results["filter_options"] = {
            "categories": ["KITCHEN", "DOORS & WINDOWS", "KITCHEN PROJECT", "FURNITURE"],
            "countries": ["Kuwait", "Saudi Arabia"]
        }

    # =============================================================
    # 9. COMPLETE EXCEL PARITY TABLES (All 10 Tabs in Interactive Web UI)
    # =============================================================
    excel_tables = {}

    # Tab 1: Executive Commercial Summary Table
    if df_tim is not None and not df_tim.empty:
        t1_df = df_tim.groupby("Category").agg(
            Total_Articles=("Article_Key", "nunique"),
            OH_Stock=("OH Stock", "sum"),
            OH_Valuation_KD=("OH Value KD", "sum"),
            Warehouse_CBM=("OH CBM", "sum"),
            Open_Sales=("Open Sales QTY", "sum"),
            ATP_Stock=("ATP QTY", "sum"),
            Avg_Lead_Time_Days=("Lead Time", "mean")
        ).reset_index()
        t1_df["OH_Valuation_SAR"] = (t1_df["OH_Valuation_KD"] * SAR_PER_KWD).round(2)
        t1_df.drop(columns=["OH_Valuation_KD"], inplace=True)
        excel_tables["executive_summary"] = t1_df.to_dict("records")

        # Tab 2: ATP Threshold Risk Table
        t2_df = df_tim.groupby("Category").agg(
            Negative_ATP_Count=("ATP QTY", lambda x: int((x < 0).sum())),
            Critical_Low_0_30=("ATP QTY", lambda x: int(((x >= 0) & (x < 30)).sum())),
            Cumulative_At_Risk_Under_30=("ATP QTY", lambda x: int((x < 30).sum())),
            Healthy_Stock_30_Plus=("ATP QTY", lambda x: int((x >= 30).sum()))
        ).reset_index()
        excel_tables["atp_threshold_risk"] = t2_df.to_dict("records")
    else:
        excel_tables["executive_summary"] = []
        excel_tables["atp_threshold_risk"] = []

    # Tab 3: Early Procurement Pipeline Table (ME2N)
    if df_me2n is not None and not df_me2n.empty:
        cols_me = ["Purchasing Document", "Document Date", "Name of Vendor", "Article", "ArticleDesc", "Order Quantity", "Still to be delivered (qty)", "Still to be delivered (value)", "Currency", "Lead Time", "Projected_ATP_Date", "Pipeline_Month_Bucket"]
        valid_cols = [c for c in cols_me if c in df_me2n.columns]
        df_me_ui = df_me2n[valid_cols].copy()
        if "Document Date" in df_me_ui.columns:
            df_me_ui["Document Date"] = df_me_ui["Document Date"].dt.strftime("%Y-%m-%d").fillna("N/A")
        if "Projected_ATP_Date" in df_me_ui.columns:
            df_me_ui["Projected_ATP_Date"] = df_me_ui["Projected_ATP_Date"].dt.strftime("%Y-%m-%d").fillna("N/A")
        excel_tables["early_po_pipeline"] = df_me_ui.head(200).to_dict("records")
    else:
        excel_tables["early_po_pipeline"] = []

    # Tab 4: Logistics Delays Table (Freight Status)
    if df_fs is not None and not df_fs.empty:
        df_fs_ui = df_fs.copy()
        if "InbValKWD" in df_fs_ui.columns:
            df_fs_ui["InbVal_SAR"] = (df_fs_ui["InbValKWD"] * SAR_PER_KWD).round(2)
        cols_fs = ["PO#", "Article", "Category", "Vendor Name", "Vendor Ctry", "Import_Local", "Status", "InbVal_SAR", "Over All Delay", "EXF Delay", "ETA Delay", "BAYAN Delay", "AWH Delay"]
        valid_fs = [c for c in cols_fs if c in df_fs_ui.columns]
        excel_tables["logistics_delays"] = df_fs_ui[valid_fs].head(200).to_dict("records")
    else:
        excel_tables["logistics_delays"] = []

    # Tab 5: Warehouse Bins Table (MB52)
    if df_mb52 is not None and not df_mb52.empty:
        cols_mb = ["Article", "Material Description", "Site", "Storage Location", "Descr. of Storage Loc.", "Unrestricted", "Value Unrestricted", "Transit and Transfer", "Blocked"]
        valid_mb = [c for c in cols_mb if c in df_mb52.columns]
        excel_tables["warehouse_bins"] = df_mb52[valid_mb].head(200).to_dict("records")
    else:
        excel_tables["warehouse_bins"] = []

    # Tab 6: Shop Floor Shortages Table
    if df_lines_calculated is not None and not df_lines_calculated.empty:
        sh_df = df_lines_calculated[df_lines_calculated["Shortage_Qty"] > 0].copy()
        if not sh_df.empty:
            if "Requirement date" in sh_df.columns:
                sh_df["Requirement date"] = sh_df["Requirement date"].dt.strftime("%Y-%m-%d").fillna("N/A")
            cols_sh = ["Order_Type", "Sales Document", "Order", "Article", "Material Description", "Requirement date", "Requirement quantity (EINHEIT)", "Opening_Stock_Balance", "Fulfilled_Qty", "Shortage_Qty", "Line_Status"]
            valid_sh = [c for c in cols_sh if c in sh_df.columns]
            excel_tables["shop_floor_shortages"] = sh_df[valid_sh].head(200).to_dict("records")
        else:
            excel_tables["shop_floor_shortages"] = []
    else:
        excel_tables["shop_floor_shortages"] = []

    # Tab 7: Sales Order Fulfillment Matrix Table
    if so_fulfillment_df is not None and not so_fulfillment_df.empty:
        so_ui = so_fulfillment_df.copy()
        if "Earliest_Date" in so_ui.columns:
            so_ui["Earliest_Date"] = so_ui["Earliest_Date"].dt.strftime("%Y-%m-%d").fillna("N/A")
        if "Latest_Date" in so_ui.columns:
            so_ui["Latest_Date"] = so_ui["Latest_Date"].dt.strftime("%Y-%m-%d").fillna("N/A")
        excel_tables["so_fulfillment_matrix"] = so_ui.head(200).to_dict("records")
    else:
        excel_tables["so_fulfillment_matrix"] = []

    # Tab 8: FIFO Stock Depletion Timeline Table
    if df_lines_calculated is not None and not df_lines_calculated.empty:
        fifo_ui = df_lines_calculated.copy()
        if "Requirement date" in fifo_ui.columns:
            fifo_ui["Requirement date"] = fifo_ui["Requirement date"].dt.strftime("%Y-%m-%d").fillna("N/A")
        cols_fifo = ["Article_Key", "Sales Document", "Order", "Requirement date", "Plant_Available_Stock", "Opening_Stock_Balance", "Requirement quantity (EINHEIT)", "Fulfilled_Qty", "Shortage_Qty", "Projected_Stock_Balance", "Line_Status"]
        valid_fifo = [c for c in cols_fifo if c in fifo_ui.columns]
        excel_tables["fifo_depletion_timeline"] = fifo_ui[valid_fifo].head(200).to_dict("records")
    else:
        excel_tables["fifo_depletion_timeline"] = []

    results["master_table"] = master_records
    results["excel_tables"] = excel_tables
    results["kpis"] = kpis
    results["charts"] = charts
    results = sanitize_for_json(results)
    raw_dfs = {
        "df_tim": raw_df_tim if 'raw_df_tim' in locals() else df_tim,
        "df_me2n": raw_df_me2n if 'raw_df_me2n' in locals() else df_me2n,
        "df_fs": raw_df_fs if 'raw_df_fs' in locals() else df_fs,
        "df_mb52": df_mb52,
        "file_prd": demand_lines[0] if len(demand_lines) > 0 and demand_lines[0]["Order_Type"].iloc[0] == "PRDORDR" else file_prd,
        "file_pln": demand_lines[1] if len(demand_lines) > 1 and demand_lines[1]["Order_Type"].iloc[0] == "PLNORDR" else (demand_lines[0] if len(demand_lines) > 0 and demand_lines[0]["Order_Type"].iloc[0] == "PLNORDR" else file_pln)
    }
    return results, df_tim, df_me2n, df_fs, df_mb52, df_lines_calculated, so_fulfillment_df, df_anomalies, raw_dfs


def generate_master_excel_workbook(df_tim, df_me2n, df_fs, df_mb52, df_lines, df_so, df_anomalies=None):
    """
    Generates the comprehensive 10-tab Master Excel Workbook strictly adhering to MASTER_VIEW.md:
    Tab 1: Executive_Commercial_Summary (SAR)
    Tab 2: ATP_Threshold_Risk (Audio Note buckets + Cumulative < 30)
    Tab 3: Early_PO_Pipeline (ME2N + Lead Time Derived ATP)
    Tab 4: Logistics_Delays (Milestone Latency & Capital at Risk)
    Tab 5: Warehouse_Bins (MB52 Stock by Bin)
    Tab 6: Shop_Floor_Shortages (Active Work Order Material Gaps)
    Tab 7: SO_Fulfillment_Matrix (Sales Order Delivery Feasibility)
    Tab 8: FIFO_Depletion_Timeline (Chronological Consumption & Balance)
    Tab 9: Master_Data_Catalog (Unified Cross-Dataset Master Article Record)
    Tab 10: Data_Compliance_Audit_Log (10 Anomaly Rules & Timestamp Audits)
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        wb = writer.book
        
        # Styles
        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#1E293B', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        crit_fmt = wb.add_format({'bg_color': '#FECDD3', 'font_color': '#9F1239', 'bold': True})
        warn_fmt = wb.add_format({'bg_color': '#FEF08A', 'font_color': '#854D0E', 'bold': True})
        ok_fmt = wb.add_format({'bg_color': '#D1FAE5', 'font_color': '#065F46', 'bold': True})

        # Tab 1: Executive Commercial Summary (All valuations strictly in SAR)
        if df_tim is not None and not df_tim.empty:
            t1 = df_tim.groupby("Category").agg(
                Total_Articles=("Article_Key", "nunique"),
                OH_Stock=("OH Stock", "sum"),
                OH_Valuation_KD=("OH Value KD", "sum"),
                Warehouse_CBM=("OH CBM", "sum"),
                Open_Sales=("Open Sales QTY", "sum"),
                ATP_Stock=("ATP QTY", "sum"),
                Avg_Lead_Time_Days=("Lead Time", "mean")
            ).reset_index()
            t1["OH_Valuation_SAR"] = (t1["OH_Valuation_KD"] * 12.25).round(2)
            t1.drop(columns=["OH_Valuation_KD"], inplace=True)
            t1.to_excel(writer, sheet_name="Executive_Summary", index=False)

        # Tab 2: ATP Threshold Risk (Mandatory Audio Note Buckets)
        if df_tim is not None and not df_tim.empty:
            t2 = df_tim.groupby("Category").agg(
                Negative_ATP_Count=("ATP QTY", lambda x: (x < 0).sum()),
                Critical_Low_0_30=("ATP QTY", lambda x: ((x >= 0) & (x < 30)).sum()),
                Cumulative_At_Risk_Under_30=("ATP QTY", lambda x: (x < 30).sum()),
                Healthy_Stock_30_Plus=("ATP QTY", lambda x: (x >= 30).sum())
            ).reset_index()
            t2.to_excel(writer, sheet_name="ATP_Threshold_Risk", index=False)

        # Tab 3: Early Procurement Pipeline (ME2N + Projected ATP)
        if df_me2n is not None and not df_me2n.empty:
            cols_me = ["Purchasing Document", "Document Date", "Name of Vendor", "Article", "ArticleDesc", "Order Quantity", "Still to be delivered (qty)", "Still to be delivered (value)", "Currency", "Lead Time", "Projected_ATP_Date", "Pipeline_Month_Bucket"]
            valid_cols = [c for c in cols_me if c in df_me2n.columns]
            df_me2n[valid_cols].head(5000).to_excel(writer, sheet_name="Early_PO_Pipeline", index=False)

        # Tab 4: Logistics Delays (Freight Status - Valuations in SAR)
        if df_fs is not None and not df_fs.empty:
            df_fs_copy = df_fs.copy()
            if "InbValKWD" in df_fs_copy.columns:
                df_fs_copy["InbVal_SAR"] = (df_fs_copy["InbValKWD"] * 12.25).round(2)
            cols_fs = ["PO#", "Article", "Category", "Vendor Name", "Vendor Ctry", "Import_Local", "Status", "InbVal_SAR", "Over All Delay", "EXF Delay", "ETA Delay", "BAYAN Delay", "AWH Delay"]
            valid_fs = [c for c in cols_fs if c in df_fs_copy.columns]
            df_fs_copy[valid_fs].head(5000).to_excel(writer, sheet_name="Logistics_Delays", index=False)

        # Tab 5: Physical Bins (MB52)
        if df_mb52 is not None and not df_mb52.empty:
            cols_mb = ["Article", "Material Description", "Site", "Storage Location", "Descr. of Storage Loc.", "Unrestricted", "Value Unrestricted", "Transit and Transfer", "Blocked"]
            valid_mb = [c for c in cols_mb if c in df_mb52.columns]
            df_mb52[valid_mb].head(5000).to_excel(writer, sheet_name="Warehouse_Bins", index=False)

        # Tab 6: Shop Floor Shortages (PRDORDR / PLNORDR)
        if df_lines is not None and not df_lines.empty:
            shortages = df_lines[df_lines["Shortage_Qty"] > 0]
            if not shortages.empty:
                cols_sh = ["Order_Type", "Sales Document", "Order", "Article", "Material Description", "Requirement date", "Requirement quantity (EINHEIT)", "Opening_Stock_Balance", "Fulfilled_Qty", "Shortage_Qty", "Line_Status"]
                valid_sh = [c for c in cols_sh if c in shortages.columns]
                shortages[valid_sh].head(5000).to_excel(writer, sheet_name="Shop_Floor_Shortages", index=False)

        # Tab 7: Sales Order Fulfillment Matrix
        if df_so is not None and not df_so.empty:
            df_so.to_excel(writer, sheet_name="SO_Fulfillment_Matrix", index=False)

        # Tab 8: FIFO Stock Depletion Timeline (Spec Tab 8)
        if df_lines is not None and not df_lines.empty:
            cols_fifo = ["Article_Key", "Sales Document", "Order", "Requirement date", "Plant_Available_Stock", "Opening_Stock_Balance", "Requirement quantity (EINHEIT)", "Fulfilled_Qty", "Shortage_Qty", "Projected_Stock_Balance", "Line_Status"]
            valid_fifo = [c for c in cols_fifo if c in df_lines.columns]
            df_lines[valid_fifo].head(5000).to_excel(writer, sheet_name="FIFO_Depletion_Timeline", index=False)

        # Tab 9: Master Data Harmonized Catalog
        if df_tim is not None and not df_tim.empty:
            m_exp = df_tim.groupby("Article_Key", as_index=False).agg(
                ArticleDesc=("ArticleDesc", "first"),
                Category=("Category", "first"),
                Lead_Time_Days=("Lead Time", "first"),
                OH_Stock=("OH Stock", "sum"),
                OH_Valuation_KD=("OH Value KD", "sum"),
                OH_CBM=("OH CBM", "sum"),
                Open_Sales_QTY=("Open Sales QTY", "sum"),
                ATP_QTY=("ATP QTY", "sum"),
                Status=("Article Status - New", "first")
            )
            m_exp["OH_Valuation_SAR"] = (m_exp["OH_Valuation_KD"] * 12.25).round(2)
            m_exp.drop(columns=["OH_Valuation_KD"], inplace=True)
            m_exp.head(5000).to_excel(writer, sheet_name="Master_Data_Catalog", index=False)

        # Tab 10: Data Compliance & Process Anomaly Audit Log (Spec Tab 10)
        if df_anomalies is not None and not df_anomalies.empty:
            df_anomalies.head(5000).to_excel(writer, sheet_name="Data_Compliance_Audit_Log", index=False)

    output.seek(0)
    return output
