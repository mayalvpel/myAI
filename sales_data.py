import csv
import json

def process_sales_data(csv_file, json_file):
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        data = [dict(row) for row in reader]
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == '__main__':
    process_sales_data('sales_data.csv', 'report.json')