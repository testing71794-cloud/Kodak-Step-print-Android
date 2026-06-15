# Permission Test Module

## Test case IDs

| Range | Category |
|-------|----------|
| PERM_001–002 | General (allow all, gallery all vs limited) |
| PERM_003–005 | Camera (deny 1st, deny 2nd, settings recovery) |
| PERM_006–008 | Location |
| PERM_009–011 | Nearby Devices |
| PERM_012–014 | Notification |
| PERM_015–017 | Photos & Videos |
| PERM_018–022 | Gallery combination scenarios |
| PERM_023–028 | App lifecycle / stability |
| PERM_029–045 | Validation scenarios (regression matrix) |

## Permission order (strict)

Camera → Location → Nearby Devices → Notification → Photos & Videos

## Files

| File | Purpose |
|------|---------|
| `permission_test_suite_enterprise.csv` | Manual + automation test spec (PERM_001–045) |
| `atp_perm_mapping.csv` | PERM → Maestro flow mapping |
| `atp_permission_mapping.csv` | PM_01–30 Maestro YAML automation flows |
| `PM_*.yaml` | Executable Maestro flows |
| `subflows/` | Reusable permission subflows |

## Regenerate PERM suite

```powershell
python scripts/generate_perm_spreadsheet_suite.py
python scripts/regenerate_permission_pm_flows.py
```

## Run Maestro automation (PM_01–30)

```powershell
.\scripts\run_permission_suite.ps1 -Device <SERIAL>
```
