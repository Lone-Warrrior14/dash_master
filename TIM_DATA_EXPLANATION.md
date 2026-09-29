# Total Inventory Management (TIM) Master Guide

Comprehensive guide and data explanation for the master inventory dataset (`TIM 22092026.xlsx`), covering schema definitions, business timeline conventions, category standardization, full dataset statistics across all **279,419 items**, and sample reference data.

---

## 1. Complete Dataset Summary (All 279,419 Records)

An exhaustive scan across all records in the TIM master sheet reveals the following distribution:

### Key Metrics
- **Total Articles / SKUs:** `279,419`
- **Total On-Hand Stock (OH Stock):** `18,740,331 units`
- **Total On-Hand Valuation:** `8,343,982 KD` (~8.34M Kuwaiti Dinars)
- **Items with Physical Stock (`OH Stock > 0`):** `16,113` articles (~5.8% of catalog)
- **Items Requiring Re-order (`Order Requirement > 0`):** `8,623` articles

---

### Geographic Distribution
| Country | SKU Count | Percentage |
| :--- | :---: | :---: |
| **Kuwait** | 140,838 | 50.4% |
| **Saudi Arabia** | 138,581 | 49.6% |

---

### Anchor Groupings
| Anchor Grouping | SKU Count | Share |
| :--- | :---: | :---: |
| **Kitchens** | 205,114 | 73.4% |
| **Doors & Windows** | 60,765 | 21.7% |
| **Furniture** | 12,128 | 4.3% |
| **Bathroom** | 891 | 0.3% |
| **Woodwork** | 441 | 0.2% |
| **Wardrobes** | 80 | <0.1% |

---

### Categories Breakdown
| Category | SKU Count | Notes / Normalized Group |
| :--- | :---: | :--- |
| **KITCHEN PRODUCTION** | 148,186 | Standardized to `KITCHEN` (Production components, raw panels, carcasses) |
| **KITCHENS** | 56,928 | Standardized to `KITCHEN` (Finished kitchen sets & fronts) |
| **INTERNAL DOORS** | 35,667 | Interior door leaves & frames |
| **D&W PRODUCTION** | 16,411 | Standardized to `DOORS & WINDOWS` |
| **FURNITURE PRODUCTION** | 12,128 | Sofas, upholstery foam, cushions, hardware |
| **DOORS & WINDOWS** | 8,687 | Standardized to `DOORS & WINDOWS` |
| **BATHROOM PRODUCTION** | 891 | Standardized to `KITCHEN` (Merged into Kitchen division) |
| **WOODWORK PRODUCTION** | 441 | Custom joinery & millwork |
| **WARDROBE PRODUCTION** | 80 | Closet & wardrobe elements |

---

### Lifecycle Status Distribution
| Article Status | SKU Count | Description |
| :--- | :---: | :--- |
| **New** | 148,164 (53.0%) | Newly cataloged or introduced SKUs (often awaiting initial stocking) |
| **Discontinued** | 106,845 (38.2%) | Phased-out or retired components/products no longer procured |
| **Active** | 24,166 (8.6%) | Currently stocked, procured, and sold catalog articles |
| **Active Seasonal** | 244 (0.1%) | Season-dependent catalog lines |

---

### Material Classifications
| Article Classification | SKU Count |
| :--- | :---: |
| **Finished Goods** | 177,349 |
| **Sellables** | 81,301 |
| **Semi Finished** | 17,250 |
| **Raw Materials** | 3,519 |

---

## 2. Category Normalization Rules

### A. Kitchen Consolidation (`KITCHEN`)
> [!IMPORTANT]
> **Kitchen Category Consolidation:**
> The following three raw categories are consolidated into a single unified category — **`KITCHEN`**:
> - `KITCHENS` (56,928 SKUs)
> - `BATHROOM PRODUCTION` (891 SKUs)
> - `KITCHEN PRODUCTION` (148,186 SKUs)
>
> **Combined Total:** **206,005 articles** (~73.7% of catalog) are consolidated under **`KITCHEN`**.

### B. Doors & Windows Normalization (`DOORS & WINDOWS`)
> [!IMPORTANT]
> **Doors & Windows Equivalency Rule:**
> Within the TIM dataset, items belonging to the Doors & Windows division appear under the following category label variants:
> - `D&W PRODUCTION` (16,411 SKUs)
> - `D&W PRODUCTIONS`
> - `DOORS & WINDOWS` (8,687 SKUs)
> - `DOORS AND WINDOWS`
>
> All of these labels refer to the **exact same product category** (`DOORS & WINDOWS`). Together with `INTERNAL DOORS` (35,667 SKUs), they constitute the entire Doors & Windows product group of **60,765 total articles** in the file.

---

## 3. Timeline & Period Conventions (Past vs. Future)

The sheet clearly separates **past ordering history** from **future incoming shipments (Inbound)**:

### A. Past Order / Demand History (`Curr` to `Curr-12`)
These columns track past historical order demand moving backwards in time:

| Column Bucket | Period Meaning |
| :--- | :--- |
| **`Curr`** | **Current Month** (orders/sales month-to-date) |
| **`Curr-1`** | **1 Month Ago** (last month) |
| **`Curr-2`** | **2 Months Ago** |
| **`Curr-3`** to **`Curr-11`** | **3 to 11 Months Ago** |
| **`Curr-12`** | **12 Months Ago** (same month last year for year-over-year seasonality) |

Planners use this rolling past history to evaluate demand velocity and establish baseline metrics such as **`Country Sales Monthly Mean QTY`**.

---

### B. Future Inbound Pipeline (`Inbound Curr` to `Inbound Curr+5`)

**What does "Inbound" mean?**
> **Inbound** refers to purchase orders, replenishment batches, or shipments that have already been placed with vendors or factories and are **on their way into the warehouse** (incoming supply).

The plus (`+`) buckets project forward into the upcoming months:

| Column Bucket | Period Meaning | Supply Status | Active SKUs | Scheduled Inbound Units |
| :--- | :--- | :--- | :---: | :---: |
| **`Inbound Curr`** | **Current Month** | Shipments arriving / clearing customs this month | 1,982 | 2,412,516 |
| **`Inbound Curr+1`** | **Next Month** | Shipments scheduled to arrive 1 month in the future | 1,119 | 1,411,366 |
| **`Inbound Curr+2`** | **2 Months Ahead** | Shipments scheduled to arrive 2 months in the future | 445 | 3,310,052 |
| **`Inbound Curr+3`** | **3 Months Ahead** | Shipments scheduled to arrive 3 months in the future | 240 | 1,391,800 |
| **`Inbound Curr+4`** | **4 Months Ahead** | Shipments scheduled to arrive 4 months in the future | 160 | 899,036 |
| **`Inbound Curr+5`** | **5 Months Ahead** | Shipments scheduled to arrive 5 months in the future | 43 | 521,161 |
| **Total Inbound Pipeline** | | **Across entire catalog** | — | **9,945,931 units** |

**Why this matters in inventory planning:**
The net re-order requirement is calculated by balancing:
$$\text{Net Requirement} = \text{Target Stock} - (\text{On-Hand Stock} + \text{Future Inbound Pipeline})$$
If sufficient stock is already scheduled to arrive via **`Inbound Curr+1`**, the system will not trigger an unnecessary new order.


---

## 4. Key Master Column Groupings (79 Total Columns)

1. **Hierarchy & Master Data:** `Country`, `Article`, `ArticleDesc`, `Anchor Grouping`, `Category`, `Sub Category`, `Prod. Line`, `MC Desc`, `BUoM`, `Vendor`, `Vendor Desc.`.
2. **Procurement Parameters:** `Buying UoM`, `Buying Price`, `CBM`, `Landed Cost`, `Lead Time`, `Target Coverage`.
3. **Inventory Levels & Valuation:** `OH Stock`, `OH Value KD`, `OH CBM`, `Safety Stock QTY`, `Target Stock QTY`, `Target Stock Value`.
4. **Availability & Commitments:** `Open Sales QTY`, `ATP QTY` (Available to Promise), `ATP Value`, `ATP Days`.
5. **Replenishment Requirements:** `Order Requirement - Initial`, `Order Requirement`, `Order Requirement Days`, `Order Requirement Value`, `Order Requirement CBM`.
6. **Inbound Pipeline:** `Inbound Curr`, `Inbound Curr+1` to `Inbound Curr+5`.

---

## 5. Sample Reference: First 10 Records

Below is an illustration of the first 10 records as an example of raw data entries:

| # | Article | Description | Anchor / Category | Vendor | Status | Classification | OH Stock | OH Val (KD) | ATP | Order Req |
| :---: | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | `100731` | SHELL 1-Seat LT Cushion 87x87x14 MIX | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **2** | `100732` | SHELL 1-Seat RT Cushion 87x87x14 MIX | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **3** | `100733` | SHELL Chaise Lounge LT Cushn150x87x14MIX | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **4** | `100734` | SHELL Chaise Lounge RT Cushn150x87x14MIX | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **5** | `100735` | SHELL Light Green Foam 80x53x5cm | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **6** | `100736` | SHELL Light Green Foam 82x53x5cm | Furniture / FOAM | Kuwait Sponge Industries Co | Discontinued | Raw Materials | 0 | 0 | 0 | 0 |
| **7** | `100755` | NY DBL Door T2-Silver 148x718 Black | Kitchens / KITCHEN FRONTS | *None* | New | Finished Goods | 0 | 0 | 0 | 0 |
| **8** | `100756` | NY DBL Door T2-Silver 148x718 Bronze | Kitchens / KITCHEN FRONTS | *None* | New | Finished Goods | 0 | 0 | 0 | 0 |
| **9** | `100757` | NY DBL Door T2-Silver 148x718 Silver | Kitchens / KITCHEN FRONTS | *None* | Active | Finished Goods | 1 | 8 | 0 | 0 |
| **10**| `100758` | NY DBL Door T2-Silver 148x958 Black | Kitchens / KITCHEN FRONTS | *None* | New | Finished Goods | 0 | 0 | 0 | 0 |
