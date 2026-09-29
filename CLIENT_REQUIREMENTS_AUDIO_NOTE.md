# Client Requirements & Dashboard Specification (from Audio Note)

**Source:** WhatsApp Audio Note (`WhatsApp Ptt 2026-09-28 at 09.49.08.ogg`)  
**Language:** English (Transcribed & Translated from mixed English / Kannada-Malayalam dialect)  
**Scope:** Consolidated Inventory & Supply Chain Dashboard (TIM Master + Open PO + Internal Doors Extension)

---

## 1. Executive Summary & Objective

The client requires a **consolidated dashboard** integrating 3 to 4 source files (including the TIM Master file and Open PO reports). The goal is to provide unified visibility into warehouse inventory, procurement commitments, demand coverage, and replenishment readiness across all product categories (Kitchens, Doors & Windows / Internal Doors, Furniture, etc.).

A key emphasis is extending the existing dashboard capabilities to cover the **Internal Doors / Doors & Windows project**, tracking Open POs, inventory status, and replenishment requirements.

---

## 2. Source Files & Data Inputs

1. **TIM Master File (`TIM 22092026.xlsx`):**
   - Serves as the central master repository containing **79 columns** (master data, vendor info, lead times, historical order rates, safety stock, and on-hand figures).
   - Functions both as master data and an operational input file.
2. **Open Purchase Orders (Freight / PO Status Report):**
   - Active tracking of open PO lines, vendor delays, shipment tracking (ETD, ETA, Port, Bayan customs, Warehouse Arrival).
3. **Internal Doors Project Input (SAP / CSV extracts):**
   - Direct manufacturing / replenishment input taken directly from SAP/CSV for specialized internal door production.

---

## 3. Core KPIs & Functional Requirements

The voice note specifies the following key metrics and visualizations:

### 3.1. Inventory Valuation & Physical Volume
- **Total Inventory Valuation (KD):** Aggregate monetary value of on-hand inventory in Kuwaiti Dinars, with drill-downs per Category and Anchor Group.
- **Warehouse Space Utilization (CBM):** Total Cubic Meters ($m^3$) occupied in the warehouse, broken down by category and country.

### 3.2. Days of Coverage (DoC)
- **Demand-Based Days of Coverage:** How many days the current stock will last based on historical sales / demand run-rate.
- Identified per SKU and rolled up by category.

### 3.3. Status Filtering & New Assortment Isolation
- The `Article Status - New` column contains:
  - `Active`
  - `Active Seasonal`
  - `New` (New Assortment)
  - `Discontinued`
- **Client Requirement:** Provide a **top-level filter / toggle** on the dashboard to easily include or exclude specific statuses (especially `New` / New Assortment).
- *Reasoning:* Newly launched articles with zero or initial stock should not distort overstock or replenishment calculation formulas.

### 3.4. ATP (Available To Promise) Threshold Bucketing
The client explicitly requested tiered SKU count metrics for ATP per Category:
- **Negative / Below Zero ATP (`ATP < 0`):** Backordered or overcommitted SKUs where demand exceeds stock.
- **Critical Low ATP (`0 <= ATP < 30` days or units):** Fast-depleting SKUs approaching stockout.
- **Cumulative View Requirement:** The client stressed that when viewing thresholds (e.g., Under 30), it should display both the specific bucket and the cumulative count (e.g., 4 items under 0 + 15 items under 30 = 19 items requiring urgent attention).

### 3.5. Average Lead Time per Category
- Display the **Average Lead Time (in days)** required by suppliers for each category.
- Helps identify categories with long replenishment cycles that require earlier purchase ordering.

### 3.6. Open Sales Orders vs. Balance vs. On-Hand
- Summarize **Total Open Sales Orders** committed to customers category-wise.
- Display the balance between:
  $$\text{On-Hand Stock (OH)} \quad\longleftrightarrow\quad \text{Committed / Open Sales QTY} \quad\longleftrightarrow\quad \text{Available to Promise (ATP)}$$

### 3.7. Inbound Pipeline & Next-Month Visibility
- Track incoming shipments due in the current month (`Inbound Curr`) and next month (`Inbound Curr+1`) to verify incoming replenishment against open order requirements.

---

## 4. Architectural Note on Direct Replenishment
- As noted in the audio, while TIM is comprehensive for sales and commercial stock, direct manufacturing replenishment for specific internal door projects will be augmented with direct SAP data extractions to feed production replenishment files directly.

---

## 5. Next Steps & Implementation Roadmap

1. **Dashboard UI Filters:**
   - Add status multi-select (Active, Discontinued, New) to allow excluding new assortments from KPI formulas.
2. **Category-Level ATP Distribution Card:**
   - Build a visual breakdown card showing SKUs `< 0`, `< 30`, and healthy stock levels.
3. **Category Lead Time & CBM Matrix:**
   - Provide summary cards/tables displaying Category-wise Average Lead Time, Total CBM, and Total Valuation.
