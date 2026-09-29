"""Single source of the database schema version expected by this code.

Append the new file name here in the same commit that adds a migration;
test_schema.py fails when this list and neon/migrations/ diverge.
"""
MIGRATIONS = (
    '001_initial.sql',
    '002_workspace.sql',
    '003_inventory_payables.sql',
    '004_business_history.sql',
    '005_integrations_backups.sql',
    '006_catalog_details.sql',
    '007_import_options.sql',
    '008_integrated_sales.sql',
)
LATEST = MIGRATIONS[-1]
