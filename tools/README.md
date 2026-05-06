# Tools

## KRX Calendar Fixture

Generate or refresh the checked-in KRX pilot calendar fixture through the project `.venv`:

```powershell
.\.venv\Scripts\python.exe tools\generate_krx_calendar_fixture.py --from-date 20260101 --to-date 20261231 --output tests\fixtures\krx_trading_calendar_2026.json
```

The tool uses PyKRX as the upstream refresh source.
Unit tests must read the checked-in fixture and must not call network providers for calendar decisions.
