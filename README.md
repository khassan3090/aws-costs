# AWS Cost Analyzer Scripts

This repository contains Python scripts to help you analyze AWS resource usage and associated costs for:

- **DynamoDB**
- **AWS Lambda**
- **CloudWatch Logs**

These scripts pull cost and usage data from AWS using Boto3, organize it, and export results to Excel for easy analysis and reporting.

---

## 📦 Requirements

- Python 3.8+
- AWS CLI configured with proper profiles
- Required Python libraries (install with `pip install -r requirements.txt`):

```bash
boto3
openpyxl
