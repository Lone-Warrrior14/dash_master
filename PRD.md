# Product Requirements Document (PRD)
## Unified Enterprise Inventory, Logistics & Manufacturing Intelligence Platform

**Document Version:** 1.0.0  
**Status:** Approved for Implementation  
**Target Systems:** Total Inventory Management (TIM), Inbound Logistics (`Freight Status`), SAP ERP (`ME2N`, `MB52`), Production Planning (`PLNORDR`, `PRDORDR`)  
**Primary Stakeholders:** Executive Leadership, Supply Chain & Logistics Directors, Procurement Managers, Plant Operations Managers

---

## 1. Executive Summary & Vision

### 1.1 Problem Statement
The organization currently operates across disconnected operational and commercial data silos:
- Commercial master data and replenishment targets reside in **TIM Master** (`279,419` records).
- Real-time physical inventory is distributed across plants and storage locations in SAP **MB52**.
- Open procurement commitments exist in two conflicting horizons: early PO placement in SAP **ME2N** vs. approved shipping tracking in **Freight Status**.
- Factory floor fabrication for custom products (specifically the **Doors & Windows / Internal Doors** project) is managed via planned orders (**PLNORDR**, 78k lines) and active production runs (**PRDORDR**, 6.1k lines), where material starvation leads to delayed customer handovers.

Because these data sources are disconnected, planners face:
1. **Blind Spots in Early Replenishment:** Waiting weeks for freight updates rather than calculating projected arrivals immediately upon PO placement.
2. **Distorted Demand Metrics:** Newly introduced catalog articles distorting inventory turn rates and overstock formulas.
3. **Unplanned Factory Stoppages:** Inability to predict exact stock depletion dates against customer delivery schedules.

### 1.2 Vision & Product Objective
Deliver an integrated, real-time **Consolidated Supply Chain Intelligence Platform** that harmonizes commercial targets, point-of-placement PO commitments, physical bin stock, and factory assembly requirements into a single interface.

---

## 2. User Personas & Core Use Cases

| Persona | Role | Primary Goals & Questions Answered |
| :--- | :--- | :--- |
| **Executive Leadership** | VP / C-Suite | *"What is our total on-hand capital valuation (KD)? What percentage of committed PO capital is currently delayed at customs or sea?"* |
| **Supply Chain Director** | Logistics Head | *"Which milestone stage (EXF, ETD, BAYAN customs, AWH) is causing the greatest logistics latency? Which vendors have the highest failure rates?"* |
| **Procurement Planner** | Category Buyer | *"When will newly placed POs arrive based on supplier lead times? Which items have negative or critical low ATP (<30)?"* |
| **Plant Operations Manager**| Factory Head | *"Which customer Sales Orders are 100% fulfillable today vs. blocked by component shortages? What is the exact Stock Depletion Date for raw panels and adhesives?"* |

---

## 3. Data Ecosystem & System Ingestion Architecture

```mermaid
graph TD
    subgraph Layer 1: Commercial & Demand Master
        TIM["TIM Master (TIM 22092026.xlsx)<br/>279,419 SKUs | 79 Columns<br/>OH Stock, OH Value (KD), ATP, CBM, Sales Mean, Lead Time"]
    end

    subgraph Layer 2: Point-of-Placement Procurement
        ME2N["ME2N.XLSX (Client Preferred)<br/>2,183 PO Lines | 27 Columns<br/>Immediate PO Placement, Document Date, Undelivered Qty"]
    end

    subgraph Layer 3: Approved Shipping & Logistics
        FS["Freight Status 22092026.XLSX<br/>3,850 PO Rows | 124 Columns<br/>Milestones: EXF, ETD, ETA, BAYAN, AWH, GR, Delays"]
    end

    subgraph Layer 4: Physical Warehouse Storage
        MB52["MB52.XLSX (SAP Stock)<br/>2,123 Rows | 24 Columns<br/>Unrestricted Stock, In-Transit, Blocked, Storage Locations"]
    end

    subgraph Layer 5: Shop Floor Manufacturing Execution
        PLN["PLNORDR.XLSX (Planned Orders)<br/>78,008 Rows | Future Component Demand & Shortages"]
        PRD["PRDORDR.XLSX (Active Production)<br/>6,130 Rows | Active Shop Floor Shortages"]
    end

    TIM ---|Primary Key: Article (93.6% Match)| FS
    TIM ---|Primary Key: Article (79.5% Match)| ME2N
    TIM ---|Primary Key: Article (77.9% Match)| MB52
    ME2N ---|Join Key: PO# / Item No| FS
    MB52 ---|FIFO Allocation by Requirement Date| PLN
    MB52 ---|FIFO Allocation by Requirement Date| PRD
```

---

## 4. Functional Requirements & Business Rules

### 4.1. Category Normalization & Consolidation
- **Kitchen Division Consolidation:**
  The raw categories `KITCHENS`, `BATHROOM PRODUCTION`, and `KITCHEN PRODUCTION` must be consolidated under a single normalized category: **`KITCHEN`** (accounting for 206,005 items).
- **Doors & Windows Normalization:**
  All variations (`D&W PRODUCTION`, `D&W PRODUCTIONS`, `DOORS & WINDOWS`, `DOORS AND WINDOWS`) must be standardized to **`DOORS & WINDOWS`**. Together with `INTERNAL DOORS`, they form the Doors & Windows division.
- **Project Kitchen Flag:**
  Articles prefixed with `"P-"` must be assigned to **`KITCHEN PROJECT`**.

### 4.2. Status Filtering & New Assortment Isolation (Mandatory Client Requirement)
- **Interactive Slicer:** The platform must provide a persistent global filter for `Article Status - New`:
  - `Active`
  - `Active Seasonal`
  - `New` (New Assortment)
  - `Discontinued`
- **Core Requirement:** Users must be able to toggle `New` off with a single click.
- **Rationale:** Newly launched items with zero historical sales run-rates must not artificially depress average demand velocities, distort Days of Coverage, or trigger false replenishment orders.

### 4.3. Procurement Pipeline: ME2N Priority & Projected ATP Date Formula
- **File Priority Rule:**  
  While `Freight Status` tracks orders that have already reached logistics carriers, the client explicitly prioritizes **`ME2N`** because it captures purchase orders **as soon as they are placed** in SAP.
- **Projected Inbound ATP Date Formula:**  
  For all open lines in `ME2N`, the expected warehouse arrival date must be calculated as:
  $$\mathbf{\text{Projected Inbound ATP Date}} = \mathbf{\text{Document Date (BEDAT in ME2N)}} + \mathbf{\text{Lead Time (days from TIM Master)}}$$

### 4.4. Available to Promise (ATP) Threshold Bucketing & Cumulative Views
The platform must calculate and display tiered SKU counts per Category:
1. **Backordered / Overcommitted (`ATP < 0`):** Customer reservations exceed available stock.
2. **Critical Low ATP (`0 <= ATP < 30`):** Approaching stockout within 30 days/units.
3. **Healthy Stock (`ATP >= 30`):** Adequately buffered stock.
4. **Cumulative At-Risk Count:**
   $$\text{Total At-Risk SKUs (< 30)} = \text{Count}(\text{ATP} < 0) + \text{Count}(0 \le \text{ATP} < 30)$$

### 4.5. Chronological FIFO Manufacturing Allocation & Shortage Engine
To satisfy custom door and kitchen assembly orders:
1. Requirements from `PLNORDR` and `PRDORDR` are concatenated and sorted chronologically:
   $$\text{Sort Order} = \big[\text{Article}, \, \text{Requirement Date (Clean)}, \, \text{Sales Document}\big]$$
2. Filters out **Phantom Items** (`Phantom item == 'X'`) and **Glass Panels** (`GLS` in Material Description).
3. Evaluates inventory depletion line-by-line:
   $$\text{Cumulative Demand}_i = \sum_{k=1}^i \text{Requirement Qty}_k$$
   $$\text{Projected Stock Balance}_i = \text{Initial Available Stock (MB52)} - \text{Cumulative Demand}_i$$
   $$\text{Stock Depletion Date} = \min_{\text{Projected Balance} < 0} (\text{Requirement Date})$$

---

## 5. Complete Mathematical Formula Inventory & Consolidated KPIs

The platform unifies all operational indicators from **`Dash`** (Logistics & Compliance), **`Harsh2`** (Plant Stock & Manufacturing Execution), and **`TIM Master`** (Audio Directives).

### 5.1. Inventory & Commercial Valuation (TIM Master + MB52)
| Metric Name | Mathematical Formula | Primary Source | Business Role |
| :--- | :--- | :---: | :--- |
| **Total Inventory Valuation (KD)** | $\sum (\text{OH Value KD})$ | `TIM` | Total commercial asset value on hand |
| **Warehouse Space Utilization (CBM)**| $\sum (\text{OH CBM})$ ($m^3$) | `TIM` | Warehouse cubic meter space occupied across Kuwait & KSA |
| **Days of Coverage (DoC)** | $\frac{\text{OH Stock}}{\text{Sales Monthly Mean QTY} / 30}$ | `TIM` | Demand runway indicating how many days stock will last |
| **Commercial Stock Balance** | $\text{ATP QTY} = \text{OH Stock} - \text{Open Sales QTY}$ | `TIM` | Net available units after customer order commitments |
| **Negative ATP Count** | $\text{Count}(\text{ATP QTY} < 0)$ | `TIM` | Overcommitted SKUs where reservations exceed physical stock |
| **Critical Low ATP Count** | $\text{Count}(0 \le \text{ATP QTY} < 30)$ | `TIM` | Fast-depleting SKUs facing imminent stockout |
| **Cumulative At-Risk ATP (<30)**| $\text{Count}(\text{ATP} < 0) + \text{Count}(0 \le \text{ATP} < 30)$ | `TIM` | **Mandatory Voice Note Metric**: Combined critical threat |
| **Average Supplier Lead Time** | $\text{Mean}(\text{Lead Time})_{\text{Category}}$ | `TIM` | Category replenishment cycle in calendar days |
| **Inbound Pipeline Horizon** | $\sum_{m=0}^5 (\text{Inbound Curr}+m)$ | `TIM` | Forward scheduled commercial supply batches |

### 5.2. Early Procurement & Inbound Logistics Formulas (`Dash` + `ME2N`)
| Metric Name | Mathematical Formula | Primary Source | Business Role |
| :--- | :--- | :---: | :--- |
| **Projected Inbound ATP Date** | $\text{Document Date (ME2N)} + \text{Lead Time (TIM)}$ | `ME2N` + `TIM` | **Client Preferred**: Unlagged arrival date at point of PO placement |
| **Open Procurement Commitment** | $\sum \text{Still to be delivered (val.)}$ | `ME2N` | Gross outstanding financial capital committed in SAP |
| **PO-Level Stage Delay** | $\max_{\text{lines} \in \text{PO}}(\max(0, \, \text{Stage Delay}_{\text{line}}))$ | `Dash` (`FS`) | Clipped non-negative max delay days per milestone per PO |
| **Total PO Delay Days** | $\sum_{\text{stage} \in \text{Milestones}} \text{PO Stage Delay}$ | `Dash` (`FS`) | Cumulative latency across all 7 supply milestones |
| **Milestone Delay Counts** | $\text{Count}(\text{PO\# with Stage Delay} > 0)$ | `Dash` (`FS`) | Delay frequency across `EXF`, `ETD`, `ETA`, `BAYAN`, `AWH`, `GR`, `PORT` |
| **Overall Tracking Delay Rate** | $\frac{\text{Delayed PO Count}}{\text{Total Audited POs}} \times 100$ | `Dash` (`FS`) | On-time delivery performance score |
| **Import Portfolio Value** | $\sum_{\text{Import}} \text{InbValKWD}$ | `Dash` (`FS`) | Gross monetary value of overseas shipments |
| **Import Capital at Risk** | $\sum_{\text{Import \& Over All Delay} > 0} \text{InbValKWD}$ | `Dash` (`FS`) | Foreign spend exposed to logistics delays |
| **Import Financial Risk Rate** | $\frac{\text{Import Capital at Risk}}{\text{Import Portfolio Value}} \times 100$ | `Dash` (`FS`) | Percentage of overseas portfolio suffering delays |
| **Average Import Delay Days** | $\text{Mean}(\text{Over All Delay})_{\text{Import Delayed}}$ | `Dash` (`FS`) | Average arrival delay for international freight |
| **Local Portfolio Value** | $\sum_{\text{Local}} \text{InbValKWD}$ | `Dash` (`FS`) | Gross domestic spend (Kuwait & Saudi Arabia) |
| **Local Capital at Risk** | $\sum_{\text{Local \& Over All Delay} > 0} \text{InbValKWD}$ | `Dash` (`FS`) | Domestic spend exposed to delivery delays |
| **Local Financial Risk Rate** | $\frac{\text{Local Capital at Risk}}{\text{Local Portfolio Value}} \times 100$ | `Dash` (`FS`) | Percentage of domestic portfolio delayed |
| **Process Anomaly Rate (%)** | $\frac{\text{Violated PO Count}}{\text{Total Audited POs}} \times 100$ | `Dash` | Process compliance score (out-of-sequence timestamps, missing TIM data) |

### 5.3. Manufacturing Execution & Shortage Formulas (`Harsh2` + `MB52`)
| Metric Name | Mathematical Formula | Primary Source | Business Role |
| :--- | :--- | :---: | :--- |
| **Available Plant Stock (MB52)** | $\text{Unrestricted} + \text{Transit/Transfer}$ | `Harsh2` (`MB52`) | Physical stock available for immediate production consumption |
| **Total Plant Stock Valuation** | $\sum (\text{Value Unrestricted} + \text{Value Transit})$ | `Harsh2` (`MB52`) | Real-time valuation of shop-floor inventory assets |
| **Blocked / Defective Stock** | $\sum \text{Blocked Qty}$ & $\sum \text{Value Blocked}$ | `Harsh2` (`MB52`) | Non-conforming or damaged inventory locked from picking |
| **Total Scheduled Demand Qty** | $\sum \text{Requirement Quantity (EINHEIT)}$ | `Harsh2` | Combined demand across planned & active fabrication runs |
| **Total Scheduled Demand Value**| $\sum (\text{Demand Qty} \times \text{Unit Price})$ | `Harsh2` | Gross monetary value of scheduled factory production |
| **FIFO Fulfilled Quantity** | $\min(\text{Req Qty}, \, \max(0, \, \text{Opening Balance}))$ | `Harsh2` | Component units covered by physical warehouse stock |
| **Total Shortage Quantity** | $\sum (\text{Demand Qty} - \text{Fulfilled Qty})$ | `Harsh2` | Net missing units causing factory line starvation |
| **Total Shortage Valuation** | $\sum (\text{Shortage Qty} \times \text{Unit Price})$ | `Harsh2` | Financial value of unfulfilled manufacturing demand |
| **Overall Factory Fulfillment %** | $\frac{\text{Total Demand Qty} - \text{Total Shortage Qty}}{\text{Total Demand Qty}} \times 100$ | `Harsh2` | Assembly line material sufficiency rating |
| **Critical Stockout SKU Count** | $\text{Count}(\text{Initial Stock} \le 0 \text{ \& Demand} > 0)$ | `Harsh2` | Materials with 0 stock halting customer production |
| **Stockout Risk SKU Count** | $\text{Count}(\text{Net Projected Balance} < 0)$ | `Harsh2` | Materials whose scheduled demand exceeds starting stock |
| **Sufficient Stock SKU Count** | $\text{Count}(\text{Net Projected Balance} \ge 0)$ | `Harsh2` | Materials fully covered through all scheduled runs |
| **Stock Depletion Date** | $\min_{\text{Projected Balance} < 0}(\text{Requirement Date})$ | `Harsh2` | **Exact calendar day inventory reaches zero** |
| **Days on Hand (DOH / Runway)** | $\frac{\text{Total Stock Value}}{\text{Total Scheduled Demand Value} / 30}$ | `Harsh2` | Operating manufacturing runway in calendar days |
| **Impacted Customer SICs Count** | $\text{Distinct Count}(\text{Sales Document with Shortage})$ | `Harsh2` | Customer sales orders blocked by component shortages |
| **SO Ready for Delivery Count** | $\text{Count}(\text{Sales Document with Shortage Qty} \le 0)$ | `Harsh2` | Customer contracts 100% fulfillable immediately |
| **SO Partial Delivery Risk Count**| $\text{Count}(\text{Shortage} > 0 \text{ \& Deliverable} > 0)$ | `Harsh2` | Orders with partial components completed |
| **SO Fulfillment Percentage** | $\frac{\text{Deliverable Qty}}{\text{Total Ordered Qty}} \times 100$ | `Harsh2` | Line-item completion percentage per customer contract |

---

## 6. Dashboard Layout & Visualizations Specification

### View 1: Executive Overview & Commercial Balance (TIM + MB52)
- **Top Metric Cards:**
  - `Total Inventory Valuation (KD)`
  - `Warehouse Space Utilization (CBM)`
  - `Portfolio Days of Coverage (DoC)`
  - `Cumulative At-Risk ATP (<30)` *(Mandatory Audio Directive)*
- **Visuals:**
  - **Chart 1.1: ATP Risk Distribution (Dual-Layer Donut):** Negative ($<0$), Critical ($0\text{--}30$), and Healthy ($>30$) with interactive cumulative toggle.
  - **Chart 1.2: Supplier Lead Time vs. Coverage Matrix (Bubble Scatter):** X-axis is Lead Time, Y-axis is DoC, bubble size is Valuation. Isolates high-lead-time / low-coverage risk zones.
  - **Chart 1.3: Stock Commitment Balance (Grouped Bar):** $\text{On-Hand} \iff \text{Open Sales} \iff \text{ATP} \iff \text{Next-Month Inbound}$.
  - **Chart 1.4: Warehouse Space Allocation (Treemap):** CBM footprint split by Country (Kuwait vs. Saudi Arabia) and Category.

### View 2: Procurement & Inbound Logistics (ME2N + Freight Status)
- **Top Metric Cards:**
  - `Unlagged Placed PO Pipeline (ME2N)`
  - `Approved In-Motion Shipping Value (Freight Status)`
  - `Logistics Capital at Risk (KWD)`
  - `Overall Tracking Delay Rate (%)`
- **Visuals:**
  - **Chart 2.1: Milestone Logistics Delay Waterfall:** Gate latency across `EXF` $\rightarrow$ `ETD` $\rightarrow$ `ETA` $\rightarrow$ `BAYAN Customs` $\rightarrow$ `AWH` $\rightarrow$ `GR Processing`.
  - **Chart 2.2: Derived Inbound Horizon Timeline:** Stacked timeline forecasting arrivals via $\text{Document Date (ME2N)} + \text{Lead Time (TIM)}$.
  - **Chart 2.3: Import vs. Local Financial Risk (Side-by-Side Gauges):** Gross portfolio value vs. capital exposed to delays.
  - **Chart 2.4: Top 10 Delayed Suppliers Exposure Chart:** Supplier ranking by exposed capital and delay days.

### View 3: Manufacturing & Internal Doors Production (PLNORDR + PRDORDR + MB52)
- **Top Metric Cards:**
  - `Active Factory Shortage Units (PRDORDR)`
  - `Planned MRP Shortages (PLNORDR)`
  - `Customer SO Delivery Readiness (%)`
  - `Plant Manufacturing Runway (Days on Hand)`
- **Visuals:**
  - **Chart 3.1: FIFO Inventory Depletion Runway (Interactive Area & Stepped Line):** Cumulative demand curves with vertical **Stock Depletion Pins** identifying the exact date of line stoppage.
  - **Chart 3.2: Pareto Top 10 Bottleneck Components:** Missing parts ranked by shortage volume and blocked customer Sales Documents (SICs).
  - **Chart 3.3: Customer Sales Order Readiness Ring:** `Ready for Delivery` (100%) vs. `Partial Risk` vs. `Unfulfillable`.

---

## 7. Master Excel Workbook Outputs (10 Exportable Worksheets)

The platform provides a 1-click export of the consolidated multi-source data model into a unified Excel report:
1. **`Executive_Commercial_Summary`:** Category valuations, CBM, DoC, and lead times.
2. **`ATP_Threshold_Risk_Distribution`:** Tiered and cumulative SKU counts ($<0$, $0\text{--}30$, $>30$).
3. **`Early_Procurement_Pipeline`:** Unlagged PO placement tracker with derived ATP dates.
4. **`Logistics_Shipping_Delays`:** Container milestone tracking, delay days, and capital at risk.
5. **`Physical_Warehouse_Bins`:** Bin-level unrestricted, in-transit, and blocked stocks by plant.
6. **`Shop_Floor_Shortage_Bottlenecks`:** Active PRDORDR component shortages stalling machines.
7. **`Planned_MRP_Demand_Forecast`:** Forward PLNORDR requirements vs. incoming supply coverage.
8. **`FIFO_Stock_Depletion_Timeline`:** Order-by-order depletion audit and Stock Depletion Dates.
9. **`Sales_Order_Fulfillment_Matrix`:** Customer Sales Order delivery readiness and completion percentages.
10. **`Data_Compliance_Audit_Log`:** Out-of-sequence date errors and missing TIM master records.

---

## 8. Non-Functional Requirements & Performance Benchmarks

1. **Columnar Ingestion Performance:** Ingest and process all 6 files (over 360,000 combined rows) in under 5 seconds using memory-mapped Parquet/Arrow structures.
2. **Key Sanitization:** Normalize all `Article` IDs by stripping whitespace, removing leading zeros, and cleaning `.0` floating-point suffixes to ensure zero-loss joins.
3. **Export Compatibility:** Generate standardized `.xlsx` workbooks with frozen headers, formatted currency cells, and conditional formatting rules for visual inspection.

