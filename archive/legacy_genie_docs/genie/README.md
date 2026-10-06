# Clinical Data Repository - Genie Configuration

This folder contains the configuration and evaluation material required to build the final Databricks Genie Agent.

The Agent will use curated Gold-layer datasets only.

## Genie Configuration Mapping

| File | Databricks Genie Location |
|---|---|
| `about_config.md` | Configure → About |
| `source_metadata.md` | Configure → Sources |
| `general_instructions.md` | Configure → Instructions |
| `semantic_definitions.md` | Configure → Examples → Measure / Filter / Field / Join |
| `example_questions.md` | Configure → Examples → Example query |
| `benchmark_questions.md` | Benchmark |

## Planned Gold Sources

1. `gold.patient_journey`
2. `gold.icu_clinical_monitoring`
3. `gold.hospital_pressure_daily`

Additional diagnosis or procedure detail sources will only be added if required after Gold implementation.

## Implementation Order

1. Build and validate Gold tables.
2. Complete all sections marked **CONFIRM AFTER GOLD**.
3. Add Gold tables to Genie Sources.
4. Add table and column descriptions.
5. Configure joins, measures and filters.
6. Paste the final General Instructions.
7. Add verified Example Queries.
8. Run Benchmarks against trusted SQL.
9. Test Admin, Manager and Analyst / Viewer security behaviour.
10. Freeze the Agent configuration for the final demonstration.

## Important Rule

Do not add Bronze or Silver tables to the final Genie Agent.

Gold should contain the business-ready structure. Genie should analyse the Gold layer rather than performing core data engineering logic itself.