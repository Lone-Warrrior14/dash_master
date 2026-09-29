# SAP PLNORDR Planned Production Orders Explanation (`plnordr.XLSX`)

Comprehensive documentation and data explanation for the SAP **Planned Orders (PLNORDR)** requirement dataset (`plnordr.XLSX`). This file represents material requirements planning (MRP) generated planned orders and component demand intended to fulfill projected and forward customer orders.

---

## 1. File Overview & Key Dimensions

- **Source System:** SAP PP (Production Planning) / MRP (T-Codes: `MD16`, `COOIS`)
- **Total Records:** `78,008` planned requirement lines
- **Total Columns:** `16` columns
- **Unique Articles Required:** `352` raw materials, hardware components, and semi-finished pieces
- **Total Requirement Quantity:** `514,821.17 units`
- **Total Shortage Quantity:** **`148,068.80 units`**
- **Shortage Lines Impacted:** **`24,967` planned line items** (~32% of all requirements face immediate stock shortages)

---

## 2. Schema & Column Definitions (16 Columns)

| Column Name | Data Type | SAP Field / Purpose | Description & Business Rules |
| :--- | :---: | :--- | :--- |
| **`Sales Document`** | Numeric (`float`) | `VBELN` | Upstream customer sales order number triggering this production plan. |
| **`Pegged requirement`** | Numeric (`int64`) | `AUFNR_PEGGED` | The parent assembly or higher-level production order requirement. |
| **`Article`** | Numeric (`int64`) | `MATNR` | Component material required (e.g. `520864`, `619091`, glue, screws, hinges, door frames). |
| **`Phantom item`** | Text | `DUMPS` | Phantom assembly indicator for transient multi-level BOM groupings. |
| **`Material Description`** | Text | `MAKTX` | Component name and dimensions (e.g. `Corner Protection 56x50MM-Black`, `Edge Band Glue 608.00`). |
| **`Requirement quantity (EINHEIT)`**| Numeric (`float`) | `BDMNG` | Total quantity of component needed for the scheduled planned run. |
| **`Unit of Entry (=ERFME)`** | Text | `ERFME` | Unit of measure entered in the BOM (e.g., `EA`, `KG`, `M`, `M2`). |
| **`Quantity (BUNIT)`** | Numeric (`float`) | `MENGE` | Component requirement quantity expressed in base unit of measure. |
| **`Base Unit of Measure (=BUNIT)`**| Text | `MEINS` | Base inventory unit. |
| **`Charateristics 2`** | Text | Variant configuration parameters (e.g. color, finish, dimensions). |
| **`Requirement date`** | Date (`datetime`) | `BDTER` | Scheduled target date by which the components must be available on the shop floor. |
| **`Charateristics 1`** | Text | Secondary variant configuration details. |
| **`Open Quantity (EINHEIT)`** | Numeric (`float`) | `VMENG` | Remaining unfulfilled requirement quantity yet to be issued to production. |
| **`Shortage (EINHEIT)`** | Numeric (`float`) | `ENMNG_SHORT` | **Missing quantity not covered by current on-hand warehouse inventory**. Triggers reordering or expedition. |
| **`Sales Office`** | Numeric (`float`) | `VKBUR` | Originating sales branch/office (e.g., `1101`). |
| **`Order`** | Numeric (`int64`) | `PLNUM` | SAP Planned Order unique identification number (e.g. `59714488`). |

---

## 3. Operational Role in Dashboard Integration

1. **Forward Demand Visibility (Internal Doors & Kitchen Manufacturing):**  
   Highlights upcoming consumption of raw materials (boards, foils, locks, adhesives) before production orders are officially dispatched to the plant floor.
2. **Bottleneck & Shortage Alerts:**  
   With **148,068 units across 24,967 rows** in shortage status, this dataset identifies exactly which supplier POs in `me2n.XLSX` and `Freight Status` must be accelerated to prevent manufacturing stoppages.
3. **Capacity & Planning Horizons:**  
   Allows factory management to group requirements by `Requirement date` and `Sales Office` to schedule batch production efficiently.
