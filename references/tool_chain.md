# Backend Tool Chain Guide

## When to Use Each Tool

### Internal Scripts (bundled with skill)

| Script | Purpose | When to run |
|--------|---------|-------------|
| `manuscript_extractor.py` | Extract NHST stats, descriptives, proportions from DOCX/PDF/text | First step — always run on input |
| `grim_tests.py` | Run GRIM/GRIMMER/DEBIT forensic tests | After extraction — run on extracted stats |
| `cross_reference_audit.py` | Check cross-section consistency | After extraction — run on extracted stats |
| `report_generator.py` | Generate final HTML report | Last step — combine all results |

### External R Tools (user must install separately)

| Tool | R Command | What it adds beyond internal scripts |
|------|----------|--------------------------------------|
| **statcheck** | `install.packages("statcheck")` | Mature p-value checking with ~60% APA detection rate; validates our Python extraction |
| **JATSdecoder** | `install.packages("JATSdecoder")` | Broader statistical extraction (20+ test types); PDF→CERMXML conversion; get.stats function |
| **tableParser** | `devtools::install_github("ingmarboeschen/tableParser")` | Structured table data extraction; table2stats conversion |
| **scrutiny** | `install.packages("scrutiny")` | Production GRIM/GRIMMER/DEBIT with visual cascade testing and digit analysis |
| **rsprite2** | `install.packages("rsprite2")` | SPRITE distribution reconstruction with constraints |

### Web Tools (for manual verification)

| Tool | URL | Use case |
|------|-----|----------|
| get-stats.app | https://www.get-stats.app | Upload DOCX/PDF for quick stat extraction and p-check |
| Manusights Audit | https://manusights.com/tools/stats-audit | Paste text for GRIM+GRIMMER+DEBIT+statcheck combined check |
| statcheck.io | https://statcheck.io | Web interface for statcheck; good for spot-checking |

## Execution Pipeline

```
Step 1: Extract
  → manuscript_extractor.py --input file.docx --output stats.json
  → (Optional) Also extract via JATSdecoder::get.stats() for broader coverage

Step 2: Forensic Tests
  → grim_tests.py --input stats.json --output grim.json
  → (Optional) scrutiny::grim_map() + scrutiny::grimmer_map() for production

Step 3: Cross-Reference
  → cross_reference_audit.py --input stats.json --output cross.json

Step 4: Report
  → report_generator.py --extracted stats.json --grim grim.json --cross cross.json --output report.html
```

## Interpreting Script Outputs

### manuscript_extractor.py output (stats.json)
```json
{
  "Results": {
    "nhst": [
      {
        "test_type": "t", "test_statistic": 2.14, "df1": 28, "df2": null,
        "reported_p": "= 0.04", "reported_p_value": 0.04, "computed_p": 0.0418,
        "consistent": true
      }
    ],
    "descriptives": [
      {"mean": 3.51, "sd": 0.82, "n": 30, "spread_label": "SD"}
    ],
    "proportions": []
  }
}
```

### grim_tests.py output (grim.json)
```json
{
  "grim": [{"grim_pass": false, "closest_possible": 3.50, ...}],
  "grimmer": [{"overall_pass": false, "discrepancy_details": "..."}],
  "debit": [],
  "summary": {"grim_pass": 0, "grim_fail": 1, ...}
}
```

### cross_reference_audit.py output (cross.json)
```json
{
  "flags": [...],
  "summary": {"total_flags": 5, "high": 1, "medium": 2, "low": 2},
  "by_severity": {"high": [...], "medium": [...], "low": [...]}
}
```
