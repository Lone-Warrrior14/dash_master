# SAP PRDORDR Active Production Orders Explanation (`prdordr.XLSX`)

Comprehensive documentation and data explanation for the SAP **Production Orders (PRDORDR)** active execution dataset (`prdordr.XLSX`). This file details active, released shop-floor manufacturing orders for the fabrication of door frames, leaves, architraves, panels, and kitchen parts.

---

## 1. File Overview & Key Dimensions

- **Source System:** SAP PP (Production Planning & Execution) / Shop Floor Control (T-Code: `COOIS`)
- **Total Records:** `6,130` manufacturing order component lines
- **Total Columns:** `16` columns
- **Unique Component Articles Required:** `205` SKUs
- **Total Requirement Quantity:** `47,485.06 units`
- **Total Active Shortage Quantity:** **`20,001.98 units`**
- **Shortage Lines Impacted:** **`1,859` active production lines** (~30.3% of active orders currently experience material starvation)

---

## 2. Schema & Column Definitions (16 Columns)

| Column Name | Data Type | SAP Field / Purpose | Description & Business Rules |
| :--- | :---: | :--- | :--- |
| **`Sales Document`** | Numeric (`int64`) | `VBELN` | Customer sales contract/order linked to this custom manufacturing job (e.g. `2986522`). |
| **`Pegged requirement`** | Numeric (`int64`) | `AUFNR_PEGGED` | Parent assembly node or sub-assembly work-in-progress tag. |
| **`Article`** | Numeric (`int64`) | `MATNR` | Raw material / part consumed in production (e.g., `539819`, `702646`, `515285`). |
| **`Phantom item`** | Text | `DUMPS` | Phantom assembly indicator. |
| **`Material Description`** | Text | `MAKTX` | Technical item title (e.g., `WPC Door Frame 2400x200mm`, `Wrapping PUR Glue`, `XPS Board 30mm`). |
| **`Requirement quantity (EINHEIT)`**| Numeric (`float`) | `BDMNG` | Total component quantity required for active order execution. |
| **`Unit of Entry (=ERFME)`** | Text | `ERFME` | Engineering unit of issue (`M`, `KG`, `M2`, `EA`). |
| **`Quantity (BUNIT)`** | Numeric (`float`) | `MENGE` | Quantity in base inventory unit. |
| **`Base Unit of Measure (=BUNIT)`**| Text | `MEINS` | Base inventory unit. |
| **`Charateristics 2`** | Text | Dimension / color specifications. |
| **`Requirement date`** | Date (`datetime`) | `BDTER` | Scheduled manufacturing execution date on the floor. |
| **`Charateristics 1`** | Text | Primary variant attributes. |
| **`Open Quantity (EINHEIT)`** | Numeric (`float`) | `VMENG` | Unissued material quantity still required to complete fabrication. |
| **`Shortage (EINHEIT)`** | Numeric (`float`) | `ENMNG_SHORT` | **Critical missing stock preventing order release/completion**. |
| **`Sales Office`** | Numeric (`int64`) | `VKBUR` | Branch / plant sales office code (e.g., `1099`). |
| **`Order`** | Numeric (`int64`) | `AUFNR` | 10-digit SAP Production Order ID (e.g. `3001150362`). |

---

## 3. Operational Role in Dashboard Integration

1. **Shop-Floor Critical Path & Bottlenecks:**  
   Unlike planned orders (`plnordr`), `prdordr` represents **firm production commitments** already scheduled or running on machines. The **20,001.98 unit shortage** directly delays customer handovers.
2. **Immediate Stoppage Risk Prioritization:**  
   Provides direct visibility into the exact door models (e.g., WPC frames, XPS infill boards, pur adhesives) stalled due to missing raw materials.
3. **Cross-Stream Allocation:**  
   When warehouse stock arrives in `mb52.XLSX` or shipments clear customs in `Freight Status`, PRDORDR orders receive highest reservation priority before open Planned Orders (`plnordr`).
