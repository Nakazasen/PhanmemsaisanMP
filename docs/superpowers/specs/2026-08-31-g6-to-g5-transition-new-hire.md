# G6 to G5 transition handling — specification

## Source request

Workbook `Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx`, sheet
`Hạng mục cần cải tiến`, rows 820–835.  The request is to add a manual
`G6=>G5` count to the manual staffing screen.  A worker who changes from G6
to G5 is not a new hire, so their change must not create new-hire expenses
such as notebooks, pens, cards, philosophy material, or uniforms.

## Root cause

`AllocationEngine._get_event_delta()` independently floors positive staff and
worker headcount changes.  It has no input representing an internal G6-to-G5
transfer, so every positive staff delta is currently treated as a new staff
hire.

## Functional requirements

1. The **Nhập nhân sự thủ công** screen shall show an editable `G6=>G5`
   column for every FY month (not for the T3 baseline).
2. The value is a non-negative integer, blank means zero, and it is persisted
   by fiscal year, cost center, and period in the annual manual-input store.
3. A run shall copy this FY-scoped input into its isolated run database with
   the other manual staffing inputs.
4. For new-hire-driven allocation only, the effective staff new-hire count is
   `max(0, positive_staff_delta - g6_to_g5_count)`.  Worker new-hire count is
   unchanged.  `headcount_all` new-hire rules use the sum of the adjusted
   staff count and unchanged worker count.
5. The adjustment applies consistently to ordinary new-hire rules,
   uniform/new-hire allocation, and recruitment-health new-hire counts.
6. All non-new-hire drivers and the canonical monthly headcount values remain
   unchanged.  A missing or zero transition row preserves current results.
7. The field label must be available in Vietnamese, Japanese, and English.

## Acceptance examples

For a month with staff 10 -> 15 and workers 100 -> 95, entering `G6=>G5=5`
produces zero staff new hires and zero new-hire expense for staff-only or
combined rules (assuming no worker increase).  With `G6=>G5=3`, the same
case produces two staff new hires.  A worker-only new-hire rule remains zero
in both cases, and a normal headcount rule still uses the unmodified monthly
headcount.

## Safety boundaries

- Do not alter imported HR/department-plan headcount.
- Do not apply the adjustment to bus, lucky-money, monthly headcount,
  fixed-month, manual-event, or other non-new-hire drivers.
- Do not infer a transition from a staff/worker delta; only an explicit
  saved manual value permits the adjustment.
