# Trade CSV Schema (v1)

This schema defines the minimum columns required by the app. Extra columns are allowed and ignored unless referenced in filters.

## Required Columns

| Column        | Type        | Example                | Notes |
|---------------|-------------|------------------------|-------|
| trade_id      | string/int  | 1024                   | Unique per trade (entry/exit rows share the same id if you split rows). |
| symbol        | string      | NQ, BTCUSDT, SOLUSD    | Case-insensitive. |
| side          | string      | long / short           | Normalize to lowercase; only `long` or `short`. |
| entry_time    | datetime    | 2025-09-05 06:31:00    | ISO8601 preferred; timezone optional. |
| exit_time     | datetime    | 2025-09-05 07:05:00    | Must be ≥ entry_time. |
| entry_price   | float       | 15987.25               | Positive. |
| exit_price    | float       | 16045.75               | Positive. |
| qty           | float/int   | 2                      | Contracts/shares/units; can be fractional. |
| fees          | float       | 3.50                   | Total commissions/fees for the trade (can be 0). |
| session       | string      | NY, LON, ASIA          | Optional now; can be derived later. |
| notes         | string      | “A+ sweep → iFVG”      | Free text, optional. |

## Derived Columns (computed by app)

- **pnl**: `(exit_price - entry_price) * qty * (1 if side=='long' else -1) - fees`
- **r_multiple**: optional; if a `risk` column is present, `pnl / risk`

## Assumptions

- One row **per trade** (entry & exit in same row).  
- Times are parseable by pandas.  
- If extra columns exist (e.g., `setup_grade`, `risk`, `tag`), they’ll be passed through and may enable extra filters.

## Validation Rules

1. All **required columns present**.
2. No **nulls** in required columns.
3. **entry_time ≤ exit_time** for every row.
4. **side** ∈ {long, short} (case-insensitive).
5. **qty > 0**, **prices > 0**.
6. **fees ≥ 0**.

## Supported Inputs
- Native schema (1 row per trade) — **preferred**.
- TradingView strategy tester CSV (2 rows per trade). We infer:
  - `side` from the Signal text if no explicit column.
  - `fees` default to 0 (TV doesn’t include commissions).
  - keep optional TV fields (run_up, drawdown, cum_pnl) in notes for now.
