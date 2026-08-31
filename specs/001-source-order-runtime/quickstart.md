# Verification quickstart

1. Confirm and save files in **Thứ tự tệp nguồn** with a non-default order.
2. Run calculation and export Complete-v1 output.
3. Confirm source blocks/provenance appear in the saved sequence.
4. Re-run without changing inputs: sequence and values remain deterministic.
5. Run focused automated tests:

```powershell
py -3 -m pytest tests/test_complete_v1_source_order_writer.py tests/test_canonical_gui_export_path.py tests/test_source_order_output.py tests/test_fiscal_run_context.py -q
```
