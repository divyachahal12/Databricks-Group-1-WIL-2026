Silver Layer Summary

The Silver layer applies targeted cleaning and validation to the MIMIC-IV tables while keeping the original clinical structure and source traceability. All Bronze records were retained in the Silver layer.

D_ITEMS

Main changes:
Text fields were trimmed and blank strings converted to null for label, abbreviation, linksto, category, unitname and param_type.

Important notes:
itemid is unique and complete, making it a reliable lookup key for ICU event tables.
There is high missingness in unitname, lownormalvalue and highnormalvalue, but these are optional metadata fields so the nulls were preserved.
This table will be particularly useful in Gold for converting numeric itemid values into meaningful measurement names, categories and units.

CAREGIVER

Main changes:
No transformation was required.

Important notes:
caregiver_id is unique and complete.
The demo table only contains deidentified caregiver IDs, with no names, roles or other staff attributes.
Its main use is validating caregiver IDs in ICU event tables and potentially calculating distinct caregiver counts.

PROVIDER

Main changes:
No transformation was required.

Important notes:
provider_id is unique and complete.
Like CAREGIVER, the demo version contains identifiers only and does not provide names, roles or other provider information.
It is mainly useful for validating provider IDs in hospital order data.

CHARTEVENTS

Main changes:
value and valueuom were trimmed and blank strings converted to null.

Important notes:
No duplicate event groups were found.
All itemid values successfully match D_ITEMS.
All populated caregiver_id values successfully match CAREGIVER.
caregiver_id is missing for 24,240 records, or around 3.6%.
valuenum and valueuom have substantial missingness, but this is expected because CHARTEVENTS contains numeric, textual and categorical observations.

For Gold, valuenum should be used when analysing numeric measurements, but value should also be retained because many clinically meaningful observations are stored as text.
D_ITEMS should normally be joined or referenced when interpreting CHARTEVENTS so users and Genie do not have to work directly with itemid values.

DATETIMEEVENTS

Main changes:
valueuom was trimmed and blank strings converted to null.

Important notes:
The major key and clinical fields were complete.
No duplicate event groups were found.
All itemid values successfully match D_ITEMS.
All caregiver_id values successfully match CAREGIVER.
The value field contains timestamps rather than ordinary numeric or text measurements and should remain treated as a datetime value.

POE

Main changes:
order_type, order_subtype, transaction_type and order_status were trimmed and blank values standardised.
A new discontinue_reference_valid field was added to validate discontinue_of_poe_id relationships.

Important notes:
poe_id is unique.
All populated order_provider_id values successfully match PROVIDER.
order_subtype is missing for around 64% of records, but this appears to be because the field is only relevant to some order types.
order_provider_id is missing for around 1.75% of records and these nulls were preserved.

The discontinue_reference_valid field has three possible values:
true means the referenced POE exists in the current dataset.
false means a reference exists but the referenced POE cannot be found.
null means the order does not contain a discontinue_of_poe_id reference.

There are 24 false references. These records otherwise appear valid and are likely affected by the demo dataset being a subset of the full MIMIC-IV data, so they were preserved rather than removed.

POE_DETAIL

Main changes:
field_name and field_value were trimmed and blank strings converted to null.

Important notes:
The key fields are complete.
No duplicate detail records were found.
Every poe_id successfully matches a record in the Silver POE table.
Multiple POE_DETAIL rows can belong to the same POE order, so this is a one-to-many relationship.

Important relationships for later integration

CHARTEVENTS.itemid links to D_ITEMS.itemid.

DATETIMEEVENTS.itemid links to D_ITEMS.itemid.

CHARTEVENTS.caregiver_id links to CAREGIVER.caregiver_id.

DATETIMEEVENTS.caregiver_id links to CAREGIVER.caregiver_id.

POE.order_provider_id links to PROVIDER.provider_id.

POE_DETAIL.poe_id links to POE.poe_id.

Across the wider project, subject_id will be important for linking to patient-level data, hadm_id for hospital admission data, and stay_id for ICU stay data.

Important notes for the Gold layer

The main thing to avoid is creating one huge joined table from all the Silver tables. Many of these tables contain multiple records for the same patient, admission or ICU stay. Joining them directly using subject_id or hadm_id can create many-to-many relationships and massively inflate row counts.

Gold tables should instead be designed around specific analytical questions. Event-level tables should usually be filtered, enriched or aggregated before they are combined with other domains.

For example, CHARTEVENTS could be enriched with D_ITEMS and then summarised by ICU stay. POE could be summarised by hospital admission before being joined to admission-level information from another team member.

POE and POE_DETAIL also need particular care because one POE order can have several POE_DETAIL rows. Joining them is valid when the detail is needed, but the POE row will be repeated for each associated detail record.

D_ITEMS is likely to be particularly important for Gold and Genie because raw itemid values are not meaningful to users. Adding labels, categories and units to selected ICU measurements will make Gold datasets much easier to analyse.

CAREGIVER and PROVIDER have limited analytical value in the demo data because they only contain IDs. They are still useful for relationship validation and basic counts, but they should not be treated as full staff dimension tables.

Source traceability

The Silver tables retain the Bronze metadata fields:
_source_file
_source_module
_ingestion_timestamp

These are useful for lineage, validation and debugging, although they probably do not need to be exposed in user-facing Gold datasets.

Completed Silver tables

workspace.silver.d_items
workspace.silver.caregiver
workspace.silver.provider
workspace.silver.chartevents
workspace.silver.datetimeevents
workspace.silver.poe
workspace.silver.poe_detail

All seven Silver tables retain the same number of records as their corresponding Bronze tables.