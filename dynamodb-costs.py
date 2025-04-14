import boto3
import argparse
from datetime import datetime
import xlsxwriter

# Cost constants (adjust if needed)
STORAGE_COST_PER_GB = 0.25  # USD per GB-month
RCU_COST = 0.00013          # USD per RCU-hour
WCU_COST = 0.00065          # USD per WCU-hour
ON_DEMAND_READ_COST = 0.25 / 1_000_000  # USD per million read request units
ON_DEMAND_WRITE_COST = 1.25 / 1_000_000  # USD per million write request units

def list_tables(client):
    tables = []
    last_evaluated_table_name = None

    while True:
        if last_evaluated_table_name:
            response = client.list_tables(ExclusiveStartTableName=last_evaluated_table_name)
        else:
            response = client.list_tables()
        
        tables.extend(response.get('TableNames', []))
        last_evaluated_table_name = response.get('LastEvaluatedTableName')
        if not last_evaluated_table_name:
            break

    return tables

def estimate_cost(desc):
    # Estimate storage cost
    size_gb = desc.get("TableSizeBytes", 0) / (1024 ** 3)
    storage_cost = size_gb * STORAGE_COST_PER_GB

    billing_mode = desc.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")

    if billing_mode == "PAY_PER_REQUEST":
        # Estimate cost using on-demand usage (very rough estimate)
        # Assuming 1M read + 1M write per month as placeholder
        read_cost = ON_DEMAND_READ_COST * 1_000_000
        write_cost = ON_DEMAND_WRITE_COST * 1_000_000
        throughput_cost = read_cost + write_cost
    else:
        # Provisioned
        rcus = desc.get("ProvisionedThroughput", {}).get("ReadCapacityUnits", 0)
        wcus = desc.get("ProvisionedThroughput", {}).get("WriteCapacityUnits", 0)
        throughput_cost = (rcus * RCU_COST + wcus * WCU_COST) * 730  # 730 hours/month

    return round(storage_cost + throughput_cost, 2)

def describe_tables_to_excel(profile_name, region_name):
    session = boto3.Session(profile_name=profile_name, region_name=region_name)
    dynamodb = session.client('dynamodb')

    tables = list_tables(dynamodb)

    workbook = xlsxwriter.Workbook(f'dynamodb_tables_{region_name}_{profile_name}.xlsx')
    sheet = workbook.add_worksheet("DynamoDB Tables")
    
    headers = [
        "Table Name", "Status", "Item Count", "Size (GB)", "Billing Mode",
        "RCUs", "WCUs", "Created At", "Estimated Monthly Cost (USD)"
    ]
    for col, h in enumerate(headers):
        sheet.write(0, col, h)

    for row, table_name in enumerate(tables, start=1):
        try:
            desc = dynamodb.describe_table(TableName=table_name)['Table']

            size_gb = round(desc.get("TableSizeBytes", 0) / (1024 ** 3), 2)
            billing_mode = desc.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")
            rcus = desc.get("ProvisionedThroughput", {}).get("ReadCapacityUnits", 0)
            wcus = desc.get("ProvisionedThroughput", {}).get("WriteCapacityUnits", 0)
            created = desc.get("CreationDateTime").strftime("%Y-%m-%d %H:%M:%S")
            cost = estimate_cost(desc)

            values = [
                table_name,
                desc['TableStatus'],
                desc.get("ItemCount", 0),
                size_gb,
                billing_mode,
                rcus if billing_mode == "PROVISIONED" else "N/A",
                wcus if billing_mode == "PROVISIONED" else "N/A",
                created,
                cost
            ]

            for col, val in enumerate(values):
                sheet.write(row, col, val)

        except Exception as e:
            print(f"❌ Failed to describe {table_name}: {e}")

    workbook.close()
    print(f"✅ Output written to dynamodb_tables_{region_name}_{profile_name}.xlsx")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export DynamoDB table details to Excel")
    parser.add_argument("--profile", required=True, help="AWS CLI profile name")
    parser.add_argument("--region", required=True, help="AWS region (e.g., us-east-1)")
    args = parser.parse_args()

    describe_tables_to_excel(args.profile, args.region)
