import boto3
import pandas as pd
from datetime import datetime, timedelta

# Configurable variables
profile_name = "aws profile"  # <-- change this
region_name = "us-east-1"          # <-- change this
days_back = 30  #<----- change this as needed

# AWS Pricing (as of April 2024)
INVOCATION_COST_PER_MILLION = 0.20
COMPUTE_COST_PER_GB_SECOND = 0.0000166667

# Start session
session = boto3.Session(profile_name=profile_name, region_name=region_name)
lambda_client = session.client('lambda')
cloudwatch = session.client('cloudwatch')

end_time = datetime.utcnow()
start_time = end_time - timedelta(days=days_back)

def get_metric(function_name, metric, stat):
    response = cloudwatch.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName=metric,
        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
        StartTime=start_time,
        EndTime=end_time,
        Period=86400,
        Statistics=[stat]
    )
    return sum(dp[stat] for dp in response.get('Datapoints', []))

# Gather data
functions_data = []
paginator = lambda_client.get_paginator('list_functions')
for page in paginator.paginate():
    for fn in page['Functions']:
        fn_name = fn['FunctionName']
        memory_mb = fn.get('MemorySize', 128)
        last_modified = fn['LastModified']
        runtime = fn.get('Runtime', 'N/A')

        invocations = get_metric(fn_name, 'Invocations', 'Sum')
        avg_duration = get_metric(fn_name, 'Duration', 'Average')  # in ms

        invocation_cost = (invocations / 1_000_000) * INVOCATION_COST_PER_MILLION
        compute_seconds = (avg_duration / 1000) * invocations
        compute_cost = (memory_mb / 1024) * compute_seconds * COMPUTE_COST_PER_GB_SECOND

        functions_data.append({
            'Function Name': fn_name,
            'Runtime': runtime,
            'Memory (MB)': memory_mb,
            'Last Modified': last_modified,
            'Invocations (30d)': int(invocations),
            'Avg Duration (ms)': round(avg_duration, 2),
            'Invocation Cost ($)': round(invocation_cost, 6),
            'Compute Cost ($)': round(compute_cost, 6),
            'Total Cost ($)': round(invocation_cost + compute_cost, 6),
            'Is Active': invocations > 0
        })

# Save to Excel
df = pd.DataFrame(functions_data)
df.to_excel("lambda_cost_report.xlsx", index=False)

print("✅ Report saved as lambda_cost_report.xlsx")
