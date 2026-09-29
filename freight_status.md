# Freight Status & Inbound Pipeline Explanation (`freight_status.md`)

Comprehensive documentation and data explanation for the open purchase order and shipping logistics tracker (`Freight Status 22092026.XLSX`). This dataset monitors milestone progress, shipping lead times, port clearances, customs delays, and inbound receipts.

---

## 1. File Overview & Key Dimensions

- **Source File:** `Freight Status 22092026.XLSX`
- **Total Records:** `3,850` shipping / PO line items
- **Total Columns:** `124` tracking and delay metric columns
- **Total Ordered Quantity (`PO Qty`):** `6,077,411.44 units`
- **Total Open Inbound Quantity (`POOpenQty`):** `2,819,034.37 units`
- **Category Breakdown:**
  - `DOORS & WINDOWS`: **2,141 rows**
  - `INTERNAL DOORS`: **1,115 rows**
  - `KITCHEN PRODUCTION`: **528 rows**
  - `KITCHEN PROJECT`: **66 rows**

---

## 2. Inbound Shipment Milestones & Status Distribution

The file tracks shipments across 7 key chronological supply-chain milestones:

| Status Code | Stage Meaning | Row Count | Operational Impact |
| :--- | :--- | :---: | :--- |
| **`EXF`** | **Ex-Factory** | **3,198** | PO placed; goods being manufactured or packed at supplier factory |
| **`ETA`** | **Estimated Time of Arrival** | **486** | Ocean / Air cargo in active transit towards regional ports |
| **`ARRIVAL W/H`** | **Warehouse Arrival** | **106** | Shipments arrived at warehouse staging area awaiting final offloading |
| **`BAYAN`** | **Kuwait Customs (Bayan)** | **42** | Undergoing Kuwait customs clearance and declaration processing |
| **`GRP`** | **Goods Receipt Processing** | **10** | Physical unloading and inspection at destination site |
| **`ETD`** | **Estimated Time of Departure** | **6** | Staged at origin port awaiting vessel boarding |
| **`BOOKED`** | **Vessel / Container Booked** | **2** | Freight forwarder space confirmed |

---

## 3. Key Column Categories (124 Columns Summary)

1. **PO & Article Identifiers:**  
   `PO#`, `PO Item No`, `Article`, `Article Description`, `Vendor Name`, `VendorArticleNo.`, `Site`, `Category`, `Sub Category`.
2. **Quantities & UoMs:**  
   `PO Qty`, `POOpenQty`, `Inbound Qty`, `Inb.GR Qty`, `POQtyUoM`, `BaseUoM`, `POQtyinBUoM`, `Inbound Qty BUoM`, `OpenQtyVol-CBM`, `TotPOQtyVol-CBM`.
3. **Milestone Dates:**  
   `PO Cr. Dt` (Creation), `PO Rel Dt` (Release), `PO EXF`, `IB EXF DATE`, `ETD` (Departure), `ETA` (Arrival), `BAYAN` (Customs), `AWH` (At Warehouse), `GRP` (Goods Receipt), `ATP` (Available to Promise).
4. **Delay & Criticality Indicators:**  
   `EXF Delay`, `EXF Critical`, `ETD Delay`, `ETD Critical`, `ETA Delay`, `ETA Critical`, `BAYAN Delay`, `BAYAN Critical`, `AWH Delay`, `AWH Critical`, `GR Delay`, `GR Critical`, `Port Delay`, `Over All Delay`, `Over All Critical`.
5. **Logistics & Commercials:**  
   `Container`, `Container #`, `Container Size`, `Shipping Typ`, `Vendor Ctry`, `Incoterms`, `Payment Term`, `POCurr`, `Value`, `InbValKWD`, `Issue_Count`, `Issue_Details`, `Import / Local`, `Severity`.

---

## 4. Operational Role in Dashboard Integration

1. **Resolving Production Shortages:**  
   Directly correlates with `plnordr.md` (148k shortage units) and `prdordr.md` (20k shortage units) to show when missing raw materials are arriving.
2. **Customs & Clearance Bottlenecks:**  
   Tracks consignments caught in `BAYAN` customs clearance or delayed at ports, alerting supply chain managers to expedite release.
3. **Refining Future Supply (`Inbound` in TIM):**  
   Replaces high-level monthly inbound buckets (`Inbound Curr+1`, etc.) with vessel-specific container numbers, ETAs, and verified carrier dates.
