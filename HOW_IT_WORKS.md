# System Workflow & Logic Architecture

This document visualizes the complete data flow and explains the core algorithms used in the Faculty Proforma System.

## 1. System Workflow Diagram

```mermaid
graph TD
    %% Frontend Layer
    subgraph Frontend Logic
        A[User Selects Regulation<br>(U18 / R24)] --> B[Upload Excel File]
        B -->|POST /upload| C[Returns Upload ID]
        C -->|POST /analyze?reg=...| D[Trigger Analysis]
    end

    %% Backend Layer
    subgraph Backend Services
        D --> E[Analysis Endpoint]
        E --> F[SubjectMergerService]
        
        %% Merging Logic
        F --> G{Regulation Strategy}
        G -- U18 --> H[Pattern: CodeT + CodeL<br>Base: Code]
        G -- R24 --> I[Pattern: Code + CodeL<br>Base: Code]
        
        H & I --> J[Group & Sum Records]
        J --> K[Merged Subject Object]
        
        %% Calculation Logic
        K --> L[AttendanceCalculator]
        L --> M[Calc Original %]
        M --> N{Is Original % >= 65?}
        N -- Yes --> O[Add OD/ML to Attended]
        N -- No --> P[Keep Original Attended]
        
        O & P --> Q[Assign Safety Category]
    end

    %% Response Layer
    Q --> R[JSON Response]
    R --> S[Dashboard UI Display]
```

## 2. Code Logic Breakdown

### A. Regulation Selection & Base Extraction
The critical logic happens in `extract_base_code(subject_code, regulation)` inside `backend/app/services/subject_merger.py`.

#### **U18 Strategy**
*   **Goal**: Merge subjects that explicitly denote Theory and Lab with suffixes.
*   **Code Pattern**: Ends in `T` or `L`.
*   **Logic**:
    1.  Get `clean_code` (remove `-R21` etc).
    2.  If ends with `T`: Base is `clean_code[:-1]`. Type is `T`.
    3.  If ends with `L`: Base is `clean_code[:-1]`. Type is `L`.
    4.  Example: `CS101T` & `CS101L` -> Base `CS101`.

#### **R24 Strategy**
*   **Goal**: Merge a root subject (Theory) with its explicit Lab counterpart.
*   **Code Pattern**: Root code vs Root+L.
*   **Logic**:
    1.  If ends with `L`: Base is `clean_code[:-1]`. Type is `L`.
    2.  Else (No suffix): Base is `clean_code`. Type is `T`.
    3.  Example: `CS101` (Theory) & `CS101L` (Lab) -> Base `CS101`.

### B. The Merge Process
Once components are identified by `Base Code`, they are grouped.
*   **Input**: List of all rows for a student.
*   **Grouping**: Dictionary `{ 'CS101': [Row1, Row2] }`.
*   **Aggregation**:
    *   `conducted = sum(r.conducted for r in rows)`
    *   `attended = sum(r.attended for r in rows)`
    *   `od_total = sum(r.od for r in rows)` (ODs from *both* T and L are captured)

### C. The 65% Rule (Attendance Calculator)
Located in `backend/app/services/attendance_calculator.py`.

The system strictly enforces the rule: **OD/ML benefits are earned, not given.**

```python
original_percentage = (attended / conducted) * 100

if original_percentage >= 65.0:
    final_attended = attended + od + ml
    # Benefit applied!
else:
    final_attended = attended
    # Benefit denied due to low attendance.
```

## 3. Data Data Structure
The final object sent to the frontend looks like this:

```json
{
  "subject_code": "CS101",
  "is_combined": true,
  "final_percentage": 78.5,
  "components": [
    { "subject_code": "CS101T", "percentage": 75.0, "od_count": 1 },
    { "subject_code": "CS101L", "percentage": 82.0, "od_count": 0 }
  ]
}
```
*   The **Components** array allows the UI to show the dropdown details.
*   The **Final Percentage** is what determines the color (Safe/Danger).
