# SAP ME2N Open Purchase Orders Explanation (`me2n.XLSX`)

Comprehensive documentation and data explanation for the SAP **ME2N** open purchasing report extract (`me2n.XLSX`). This file tracks open vendor purchase orders, remaining delivery balances, and committed procurement values across suppliers.

---

## 1. File Overview & Key Dimensions

- **Source System:** SAP ERP (Transaction Code: `ME2N` - *Purchasing Documents by PO Number*)
- **Total Records:** `2,183` PO line items
- **Total Columns:** `27` columns
- **Unique Articles Procured:** `677` distinct SKUs
- **Top Purchasing Sites:**
  - Site `1100` (Kuwait Central): **798 lines**
  - Site `9101` (KSA Central DC): **451 lines**
  - Site `1888` (Kuwait Manufacturing / Factory): **309 lines**
  - Site `1101` (Kuwait Retail): **296 lines**
  - Other Sites (`1201`, `1111`, `1301`, `9102`): **329 lines**

---

## 2. Order Quantities & Currency Breakdown

### A. Quantities
- **Total Ordered Quantity (`Order Quantity`):** `745,890.80 units`
- **Remaining Undelivered Quantity (`Still to be delivered (qty)`):** `737,753.79 units` (~98.9% pending receipt)
- **Pending Invoice Quantity (`Still to be invoiced (qty)`):** Matches open delivery requirements.

### B. Procurement Value by Currency
| Currency | Lines | Total Net Order Value | Still to be Delivered Value | Primary Spend Focus |
| :---: | :---: | :---: | :---: | :--- |
| **USD** | 992 | **$2,837,856.14** | **$2,790,299.66** | International hardware, veneers, raw glues & metals |
| **SAR** | 825 | **SAR 2,043,119.26** | **SAR 1,952,379.15** | Regional Gulf procurement & Saudi plant supplies |
| **KWD** | 360 | **KWD 10,155.05** | **KWD 10,046.16** | Local Kuwait subcontracts & supplies |
| **EUR** | 3 | **€10,516.08** | **€10,516.08** | European specialized accessories & tools |
| **AED** | 3 | **AED 5,390.00** | **AED 5,390.00** | UAE freight & distribution parts |

---

## 3. Schema & Column Definitions (27 Columns)

| Column Name | Data Type | SAP Field / Purpose | Description & Business Rules |
| :--- | :---: | :--- | :--- |
| **`Purchasing Document`** | Numeric (`int64`) | `EBELN` | 10-digit SAP Purchase Order number (e.g. `4500641208`). |
| **`Document Date`** | Date (`datetime`) | `BEDAT` | PO creation date in SAP. |
| **`Site`** | Numeric (`int64`) | `WERKS` | Receiving plant or factory site code. |
| **`Purchasing Group`** | Numeric (`int64`) | `EKGRP` | Buyer/Purchasing team identifier (e.g. `451`). |
| **`Name of Vendor`** | Text | `NAME1` | Supplier vendor ID and commercial trade name (e.g. `10620 Starlight Hardware Co. L`). |
| **`Purchasing Doc. Type`** | Text | `BSART` | Document category (`NB` = Standard Purchase Order). |
| **`Item`** | Numeric (`int64`) | `EBELP` | Line item index within the PO (`10`, `20`, `30`, `40`). |
| **`Article`** | Numeric (`int64`) | `MATNR` | SAP Material / SKU ID. |
| **`Short Text`** | Text | `TXZ01` | Short description of the purchased material/service. |
| **`Order Unit`** | Text | `BSTME` | Purchase unit of measure (`EA`, `M`, `KG`, `SET`, `ROLL`). |
| **`Order Quantity`** | Numeric (`float`) | `MENGE` | Total quantity originally ordered on the line. |
| **`Still to be delivered (qty)`** | Numeric (`float`) | `WEMNG_DIFF` | Open quantity not yet received in goods receipt (GR). Crucial for future stock calculations. |
| **`Still to be invoiced (qty)`** | Numeric (`int64`) | `REMNG_DIFF` | Quantity received but not yet cleared via vendor invoice verification. |
| **`Stockkeeping unit`** | Text | `MEINS` | Inventory base unit of measure. |
| **`Quantity in SKU`** | Numeric (`float`) | Converted order quantity in base UoM. |
| **`Release status`** | Text | `FRGZU` | SAP release / approval codes (e.g., `XXXX`). |
| **`Release indicator`** | Text | `FRGKE` | PO release state (`R` = Released / Approved for vendor transmission). |
| **`Net price`** | Numeric (`float`) | `NETPR` | Agreed unit buying price in PO currency. |
| **`Currency`** | Text | `WAERS` | Purchasing currency (`USD`, `SAR`, `KWD`, `EUR`, `AED`). |
| **`Net Order Value`** | Numeric (`float`) | `NETWR` | Total monetary line value (`Order Quantity` $\times$ `Net Price`). |
| **`Still to be delivered (value)`**| Numeric (`float`) | Open committed procurement expenditure remaining to be received. |
| **`Still to be invoiced (val.)`** | Numeric (`float`) | Financial commitment remaining for accounts payable. |
| **`Deletion Indicator`** | Null / Text | `LOEKZ` | Indicates cancelled lines (none present in active extract). |
| **`Acct Assignment Cat.`** | Text | `KNTTP` | SAP account assignment category (`P` for Project, `F` for Order, or blank for Stock). |
| **`Item Category`** | Text | `PSTYP` | Item procurement type (standard stock vs consignment vs subcontracting). |
| **`Item Category.1`** | Numeric (`int64`) | Internal SAP indicator code (`0` = Standard). |
| **`Req. Tracking Number`** | Text | `BEDNR` | Planner requirement memo/reference (e.g., `DEC ORDER`, `JAN 2026`). |

---

## 4. Operational Role in Dashboard Integration & Client Directives

### A. Client Preference: ME2N vs. Freight Status ("As Soon As Order Placed")
> [!IMPORTANT]
> **Client Procurement Rule & File Priority:**
> - **Freight Status:** Represents the **approved and in-motion shipping list** (freight forwarder booked, custom clearance, carrier transit).
> - **ME2N (Client Preferred):** Represents purchase orders **as soon as the order is placed** in SAP ERP (pre-shipping release, immediate procurement commitment).
> - **Why Client Prefers ME2N:** While `Freight Status` only monitors shipments already approved and underway with logistics carriers, `ME2N` captures earlier pipeline visibility from the minute a purchasing document is created. This provides a true, unlagged picture of forward replenishment before logistics booking occurs.

---

### B. Derived ATP Date Formula (Document Date + TIM Lead Time)
Because `ME2N` captures orders at point-of-creation prior to freight booking, it lacks carrier arrival dates (`ETA` / `AWH`). The forward **Projected ATP Date** for `ME2N` orders is mathematically derived by combining `ME2N` with the `TIM` Master file:

$$\mathbf{\text{Projected ATP Date}} = \mathbf{\text{Document Date}} (\text{ME2N}) + \mathbf{\text{Lead Time (days)}} (\text{TIM Master})$$

Where:
- **`Document Date` (`BEDAT` in ME2N):** The exact date the purchase order was officially created in SAP.
- **`Lead Time` (in TIM Master):** Supplier/product-specific procurement and manufacturing lead time (in calendar days) mapped via **`Article`** (and `Vendor`).
- **Business Significance:**  
  Allows the planner to calculate future product availability for newly placed POs immediately, rather than waiting weeks for the freight forwarder to update `Freight Status`.

---

### C. Future Supply Pipeline & Capital Exposure
1. **Forward Replenishment Integration:**
   $$\text{Future Supply} = \text{Warehouse Stock (MB52)} + \sum \text{Still to be delivered (qty)} (\text{ME2N})$$
2. **Commitment & Capital Exposure:**  
   Monitors outstanding supplier exposure across currencies (~$2.79M USD + ~1.95M SAR) before invoicing.
