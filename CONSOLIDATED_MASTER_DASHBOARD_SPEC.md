# Unified Enterprise Dashboard Specification (`CONSOLIDATED_MASTER_DASHBOARD_SPEC.md`)

Comprehensive specification for unifying all operational, commercial, logistics, and manufacturing datasets:
- **Commercial Master:** `TIM 22092026.xlsx`
- **Logistics & Inbound:** `Freight Status 22092026.XLSX`
- **Warehouse Storage:** `mb52.XLSX`
- **Open Vendor POs:** `me2n.XLSX`
- **Factory Demand & Shortages:** `plnordr.XLSX` & `prdordr.XLSX`
- **Mandatory Directives:** [CLIENT_REQUIREMENTS_AUDIO_NOTE.md](file:///home/lone-warrior/Downloads/dash/CLIENT_REQUIREMENTS_AUDIO_NOTE.md)

---

## 1. Unified Architecture & Multi-Source Data Model

```mermaid
graph TD
    subgraph Layer 1: Commercial & Demand Master (TIM)
        TIM["TIM Master (279,419 SKUs)<br/>OH Stock, OH Value, ATP, Lead Time, CBM, Sales Mean, Status"]
    end

    subgraph Layer 2: Shipping & Inbound Logistics (Freight Status & ME2N)
        FS["Freight Status (3,850 rows)<br/>Milestones: EXF, ETD, ETA, BAYAN, AWH, GR, Delays"]
        ME2N["ME2N Open POs (2,183 lines)<br/>Undelivered Quantities & Vendor Commitments"]
    end

    subgraph Layer 3: Physical Warehouse Bins (MB52)
        MB52["MB52 Warehouse Stock (2,123 rows)<br/>Unrestricted, Transit, Blocked, Storage Locs"]
    end

    subgraph Layer 4: Factory Floor & Manufacturing (Internal Doors Extension)
        PLN["PLNORDR Planned Orders (78k lines)<br/>Future MRP Component Demand & Shortages"]
        PRD["PRDORDR Active Production (6.1k lines)<br/>Shop Floor Work Orders & Bottlenecks"]
    end

    TIM ---|Join Key: Article (93.6% match)| FS
    FS ---|Join Key: PO# / Article| ME2N
    TIM ---|Join Key: Article| MB52
    MB52 ---|Join Key: Article (FIFO Allocation)| PLN
    MB52 ---|Join Key: Article (FIFO Allocation)| PRD
```

---

## 2. Mandatory Voice Note KPIs & Visualizations (From Audio Directive)

These items are strictly mandated by the client in [CLIENT_REQUIREMENTS_AUDIO_NOTE.md](file:///home/lone-warrior/Downloads/dash/CLIENT_REQUIREMENTS_AUDIO_NOTE.md):

### A. Executive Inventory Valuation & Physical Volume
1. **Total Inventory Valuation (KD):**  
   - Monetary valuation in Kuwaiti Dinars:
     $$\text{Total Valuation} = \sum (\text{OH Value KD})$$
   - Category drill-down (`KITCHEN`, `DOORS & WINDOWS`, `INTERNAL DOORS`, `FURNITURE`, etc.).
2. **Warehouse Space Utilization (CBM):**  
   - Total cubic meters occupied in warehouse racks:
     $$\text{Total CBM} = \sum (\text{OH CBM})$$
   - Sliceable by **Country** (Kuwait vs. Saudi Arabia) and **Category**.

### B. Days of Coverage (DoC) & Demand Velocity
- Demand-based runway calculation:
  $$\text{Days of Coverage (DoC)} = \frac{\text{Current OH Stock}}{\text{Average Daily Demand}} = \frac{\text{OH Stock}}{\text{Country Sales Monthly Mean QTY} / 30}$$
- Rollup by SKU, Sub-Category, and Division with health color badges ($< 30\text{ days}$ red, $30\text{--}90$ yellow, $> 90$ green).

### C. Status Filtering & "New Assortment" Isolation (Top-Level Toggle)
- Multi-select interactive filter allowing dynamic inclusion/exclusion of:
  - `Active`
  - `Active Seasonal`
  - `New` (New Assortment)
  - `Discontinued`
- **Client Reason:** Newly launched SKUs with 0 historical sales or zero initial stock must not distort overstock formulas, demand velocity, or replenishment metrics.

### D. Available to Promise (ATP) Threshold Bucketing & Cumulative View
The client requested tiered SKU counts per Category:
- **Negative ATP (`ATP < 0`):** Overcommitted/backordered items where orders exceed physical stock.
- **Critical Low ATP (`0 <= ATP < 30`):** Fast-depleting SKUs facing imminent stockout.
- **Healthy ATP (`ATP >= 30`):** Adequately stocked articles.
- **Cumulative Threshold Matrix:**  
  $$\text{At-Risk SKUs (< 30)} = \text{Count}(\text{ATP} < 0) + \text{Count}(0 \le \text{ATP} < 30)$$

### E. Average Supplier Lead Time per Category
- Average replenishment cycle in days:
  $$\text{Avg Lead Time} = \frac{1}{N}\sum (\text{Lead Time})$$
- Highlight long-lead categories (e.g., imported doors/glazing: 90–120 days) requiring early PO release.

### F. Stock Balance Equation (On-Hand vs. Open Sales vs. ATP)
- Complete stock commitment balance:
  $$\text{ATP QTY} = \text{OH Stock} - \text{Open Sales QTY}$$
- Category-level stacked comparison chart showing:
  $\text{Physical Stock (OH)} \iff \text{Committed Sales} \iff \text{Unallocated ATP}$.

### G. Inbound Pipeline & Next-Month Visibility
- Incoming purchase order batches:
  $$\text{Inbound Pipeline} = \text{Inbound Curr} + \text{Inbound Curr+1} + \dots + \text{Inbound Curr+5}$$
- Balance comparison showing whether $\text{Inbound Curr+1}$ covers upcoming net requirements.

### H. Early Order Placement & ME2N Client Preference (The ATP Date Formula)
> [!IMPORTANT]
> **ME2N Priority over Freight Status:**
> - **Freight Status:** Approved and in-motion shipping status tracked by freight forwarders (vessels booked, customs clearances).
> - **ME2N (Client Preferred):** Captures purchase orders **as soon as the order is placed** in SAP ERP, giving unlagged visibility before shipping approval.
> - **Projected Inbound ATP Date Formula:**
>   $$\mathbf{\text{Projected Inbound ATP Date}} = \mathbf{\text{Document Date}} (\text{ME2N}) + \mathbf{\text{Lead Time (days)}} (\text{TIM Master})$$
>   This derived formula enables immediate calculation of incoming stock availability for newly placed POs without having to wait for the carrier shipping updates in `Freight Status`.

---

## 3. End-to-End Consolidated KPI Matrix

| Module | Core KPI | Formula / Calculation | Primary Source |
| :--- | :--- | :--- | :--- |
| **Inventory** | **Total Valuation (KD)** | $\sum \text{OH Value KD}$ | `TIM` |
| **Inventory** | **Warehouse Space (CBM)** | $\sum \text{OH CBM}$ | `TIM` |
| **Inventory** | **Stock Days of Coverage** | $\text{OH Stock} / (\text{Sales Mean QTY} / 30)$ | `TIM` |
| **Inventory** | **Physical Plant Stock** | $\sum (\text{Unrestricted} + \text{Transit})$ | `mb52` |
| **Inventory** | **Blocked / Defective Stock** | $\sum \text{Blocked Qty}$ & $\sum \text{Value Blocked}$ | `mb52` |
| **Procurement (Early)**| **Point-of-Placement Orders** | $\text{Count}(\text{PO\#})$, $\sum \text{Still to be delivered (qty)}$ | **`me2n` (Client Preferred)** |
| **Procurement (Early)**| **Projected Inbound ATP Date**| $\text{Document Date (ME2N)} + \text{Lead Time (TIM)}$ | `me2n` + `TIM` |
| **Procurement**| **Open Supplier Balances** | $\sum \text{Still to be delivered (val.)}$ | `me2n` |
| **Logistics (Transit)**| **Approved Shipping POs** | $\text{Distinct Count}(\text{PO\#})$, $\sum \text{POOpenQty}$ | `Freight Status` |
| **Logistics** | **Milestone Delay Counts** | $\text{Count}(\text{PO\# where Stage Delay} > 0)$ | `Freight Status` |
| **Logistics** | **Capital at Risk (KWD)** | $\sum (\text{InbValKWD where Over All Delay} > 0)$ | `Freight Status` |
| **Logistics** | **Financial Risk Rate** | $\text{Delayed Value} / \text{Gross Value} \times 100$ | `Freight Status` |
| **Manufacturing**| **Critical Active Shortages** | $\sum \text{Shortage Qty}$ (Active Shop Floor) | `prdordr` |
| **Manufacturing**| **Projected MRP Shortages** | $\sum \text{Shortage Qty}$ (Planned Orders) | `plnordr` |
| **Manufacturing**| **Stock Depletion Date** | $\min(\text{Requirement Date where Projected Stock} < 0)$ | `mb52` + `plnordr`/`prdordr` |
| **Manufacturing**| **Days on Hand (Runway)** | $\text{Total Stock Value} / (\text{Total Demand Value} / 30)$ | `mb52` + `plnordr`/`prdordr` |

---

## 4. Visualizations & Chart Catalog

### 1. Executive Summary Strip (Top Cards)
- **Total Portfolio Valuation:** KD 8.34M (TIM) / Real-time Plant Valuation (MB52).
- **Warehouse Space Utilization:** Total CBM occupied vs. capacity.
- **Overall Logistics Delay Rate:** % of active POs experiencing shipping delays.
- **Capital at Risk:** KWD delayed in transit/customs.
- **Factory Shortage Bottlenecks:** Active shop-floor shortage quantity and impacted orders.

### 2. Mandatory Client Charts
- **ATP Risk Distribution (Stacked Bar / Donut):**
  - `< 0 ATP` (Negative / Overcommitted)
  - `0 - 30 ATP` (Critical Runway)
  - `> 30 ATP` (Healthy)
  - *Includes cumulative toggle: "Total At-Risk (< 30)"*.
- **Category Lead Time vs. Days of Coverage (Scatter / Bubble Plot):**
  - X-Axis: Supplier Lead Time (Days)
  - Y-Axis: Days of Coverage (DoC)
  - Bubble Size: Total Valuation (KD)
  - *Directly highlights categories at risk of stockout due to high lead time and low coverage*.
- **Stock Commitment Breakdown (Grouped Bar Chart):**
  - Bar 1: Physical On-Hand Stock (`OH Stock`)
  - Bar 2: Customer Committed (`Open Sales QTY`)
  - Bar 3: Free to Promise (`ATP QTY`)
  - Bar 4: Next-Month Pipeline (`Inbound Curr+1`)
- **Warehouse CBM Distribution (Treemap / Bar Chart):**
  - Space consumption split by Category and Country (Kuwait vs. Saudi Arabia).

### 3. Supply Chain & Logistics Delay Charts (From Dash)
- **Milestone Delay Waterfall:**  
  `EXF (Factory)` $\rightarrow$ `ETD (Port)` $\rightarrow$ `ETA (Vessel)` $\rightarrow$ `BAYAN (Customs)` $\rightarrow$ `AWH (Warehouse)` $\rightarrow$ `GR (Dock)`.
- **Import vs. Local Financial Risk (Side-by-Side Donut):**  
  Gross value vs. Value at Risk.
- **Top 10 Delayed Suppliers Matrix:**  
  Supplier name, country, delayed PO count, average delay days, and delayed value.

### 4. Manufacturing & Internal Doors Extension Charts (From Harsh2)
- **FIFO Cumulative Demand vs. Stock Runway Timeline:**  
  Area chart showing inventory depletion curves leading to exact **Stock Depletion Dates**.
- **Top Bottleneck Components Bar Chart:**  
  Top 10 components creating the largest active shop-floor stoppage.
- **Sales Order Delivery Feasibility (Donut):**  
  `Ready for Full Delivery` (100% stock) vs. `Partial Delivery Risk` vs. `Unfulfillable (No Stock)`.

---

## 5. Master Data Integration & Field Mapping Table

| Unified Concept | TIM Master Field | Freight Status Field | MB52 Field | ME2N Field | Production Orders (`pln`/`prd`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Material Key** | `Article` | `Article` | `Article` | `Article` | `Article` |
| **Description** | `ArticleDesc` | `Article Description` | `Material Description` | `Short Text` | `Material Description` |
| **Category** | `Category` / `Anchor Grouping` | `Category` | `Merchandise Category` | — | — |
| **Supplier** | `Vendor` / `Vendor Desc.` | `Vendor Name` / `Vendor` | — | `Name of Vendor` | — |
| **Current Stock** | `OH Stock` | — | `Unrestricted` + `Transit` | — | — |
| **Stock Value** | `OH Value KD` | — | `Value Unrestricted` | — | — |
| **Open Sales** | `Open Sales QTY` | — | — | — | `Requirement quantity` |
| **Open Supply** | `Inbound Curr+1` | `POOpenQty` / `Inbound Qty` | `Stock in Transit` | `Still to be delivered (qty)` | — |
| **Commitment Val.** | — | `InbValKWD` / `Value` | — | `Still to be delivered (val.)` | — |
| **Customer Order** | — | — | — | — | `Sales Document` |
| **Shop Floor Job** | — | — | — | — | `Order` / `AUFNR` |

---

## 6. Interactive Filter Architecture

To satisfy all user personas (Executive, Warehouse Manager, Logistics Specialist, Production Planner), the unified dashboard features:

1. **Article Status Slicer:** Multi-select toggle (`Active`, `Active Seasonal`, `Discontinued`, `New`) to isolate new assortments.
2. **Division / Category Selector:** `KITCHEN` (consolidated), `DOORS & WINDOWS`, `INTERNAL DOORS`, `FURNITURE`, etc.
3. **Country / Site Hierarchy:** Country (`Kuwait`, `Saudi Arabia`) $\rightarrow$ Site (`1111`, `1888`, `9101`) $\rightarrow$ Storage Location.
4. **Supply Stream Filter:** `All`, `Import Only`, `Local Only`.
5. **Timeline / Horizon Slicer:** `Current Month`, `Current-1`, `Current-2`, `Future Inbound Horizon (+1 to +5)`.
