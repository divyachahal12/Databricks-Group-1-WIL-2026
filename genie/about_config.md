# Genie About Configuration

## Agent Name

Clinical Data Repository Analytics

## Description - Paste into Genie

Analyse curated healthcare Gold datasets covering patient journeys, ICU clinical activity and hospital operational pressure.

The Agent supports natural-language questions about hospital admissions, length of stay, ICU utilisation, clinical monitoring and operational workload.

Results are generated from governed Databricks Gold datasets and may differ between users depending on their Unity Catalog permissions.

The Agent is intended for analytics and platform demonstration purposes and should not be used to provide medical diagnosis or treatment advice.

---

# Common Questions

Add the following as Genie Common Questions.

## Patient Journey

How many hospital admissions are represented in the dataset?

Which clinical services have the longest average hospital length of stay?

What percentage of admissions required ICU care?

What are the most common diagnoses?

## ICU Clinical Monitoring

Which ICU care units have the highest clinical monitoring activity?

Which clinical measurements generate the most warnings?

## Hospital Pressure

Which dates had the highest hospital workload?

Which care units experienced the highest operational pressure?

---

# CONFIRM AFTER GOLD

Before finalising the About page:

- Confirm final Agent name.
- Confirm the three Gold tables are included in the Agent.
- Remove common questions that cannot be reliably answered by the final Gold schemas.
- Add one security-focused question if it provides a useful final demo.