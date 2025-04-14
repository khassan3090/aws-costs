import boto3
import pandas as pd

# Pricing estimates (adjust as needed)
INGESTION_COST_PER_GB = 0.50  # $/GB ingested
STORAGE_COST_PER_GB_MONTH = 0.03  # $/GB/month after 30 days

# Initialize boto3 client
client = boto3.client('logs')

log_groups = []
next_token = None

# Fetch all log groups
while True:
    if next_token:
        response = client.describe_log_groups(limit=50, nextToken=next_token)
    else:
        response = client.describe_log_groups(limit=50)
    log_groups.extend(response['logGroups'])
    next_token = response.get('nextToken')
    if not next_token:
        break

# Compile data
data = []
for group in log_groups:
    name = group['logGroupName']
    stored_bytes = group.get('storedBytes', 0)
    retention_days = group.get('retentionInDays', 'Never Expire')

    stored_gb = stored_bytes / (1024 ** 3)
    storage_cost = stored_gb * STORAGE_COST_PER_GB_MONTH if retention_days == 'Never Expire' or (isinstance(retention_days, int) and retention_days > 30) else 0.0
    ingestion_cost = stored_gb * INGESTION_COST_PER_GB

    data.append({
        'Log Group': name,
        'Stored (GB)': round(stored_gb, 2),
        'Retention (days)': retention_days,
        'Estimated Ingestion Cost ($)': round(ingestion_cost, 2),
        'Estimated Storage Cost ($)': round(storage_cost, 2),
    })

# Write to Excel
df = pd.DataFrame(data)
df.to_excel("cloudwatch_log_group_costs.xlsx", index=False)
print("Saved to cloudwatch_log_group_costs.xlsx")

