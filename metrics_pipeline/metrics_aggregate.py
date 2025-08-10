#!/usr/bin/env python3
"""
Metrics Aggregation Pipeline

This script processes NDJSON (newline-delimited JSON) log files containing metrics data
and converts them to CSV format with aggregation and summary statistics.

Design Decisions:
- Uses only standard library modules for core functionality to minimize dependencies
- Processes each NDJSON file separately to maintain data isolation
- Creates both detailed CSV output and summary statistics
- Handles missing or malformed JSON gracefully
- Preserves all fields from original JSON while ensuring consistent CSV structure

Usage:
    python metrics_aggregate.py

This will:
1. Scan metrics_pipeline/ndjson/*.ndjson for input files
2. Generate corresponding CSV files in metrics_pipeline/csv/
3. Create a summary statistics file: metrics_pipeline/csv/summary_stats.csv
4. Print processing results to stdout

File Structure:
- Input: metrics_pipeline/ndjson/*.ndjson
- Output: metrics_pipeline/csv/*.csv (one per input file)
- Summary: metrics_pipeline/csv/summary_stats.csv
"""

import json
import csv
import os
import glob
from pathlib import Path
from collections import defaultdict, Counter
import sys
from datetime import datetime


def parse_ndjson_file(file_path):
    """
    Parse a newline-delimited JSON file and return list of records.
    
    Args:
        file_path (str): Path to the NDJSON file
        
    Returns:
        tuple: (list of valid records, list of error messages)
    """
    records = []
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    errors.append(f"Line {line_num}: {e}")
                    
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"Error reading file {file_path}: {e}")
        
    return records, errors


def flatten_record(record, parent_key='', separator='_'):
    """
    Flatten a nested JSON record for CSV output.
    
    Args:
        record (dict): The JSON record to flatten
        parent_key (str): Parent key for nested fields
        separator (str): Separator for nested field names
        
    Returns:
        dict: Flattened record
    """
    items = []
    
    for key, value in record.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_record(value, new_key, separator).items())
        elif isinstance(value, list):
            # Convert lists to comma-separated strings
            items.append((new_key, ','.join(map(str, value))))
        else:
            items.append((new_key, value))
            
    return dict(items)


def get_all_fieldnames(records):
    """
    Extract all unique field names from a list of records.
    
    Args:
        records (list): List of flattened record dictionaries
        
    Returns:
        list: Sorted list of unique field names
    """
    fieldnames = set()
    for record in records:
        fieldnames.update(record.keys())
    return sorted(list(fieldnames))


def write_csv_file(records, output_path):
    """
    Write records to a CSV file.
    
    Args:
        records (list): List of record dictionaries
        output_path (str): Path for the output CSV file
        
    Returns:
        tuple: (success boolean, error message if any)
    """
    if not records:
        return True, "No records to write"
        
    try:
        # Flatten all records
        flattened_records = [flatten_record(record) for record in records]
        
        # Get all unique fieldnames
        fieldnames = get_all_fieldnames(flattened_records)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for record in flattened_records:
                # Fill missing fields with empty strings
                complete_record = {field: record.get(field, '') for field in fieldnames}
                writer.writerow(complete_record)
                
        return True, None
        
    except Exception as e:
        return False, f"Error writing CSV file {output_path}: {e}"


def calculate_summary_stats(all_records, file_stats):
    """
    Calculate summary statistics across all processed files.
    
    Args:
        all_records (list): Combined list of all records
        file_stats (dict): Per-file statistics
        
    Returns:
        dict: Summary statistics
    """
    if not all_records:
        return {}
        
    stats = {
        'total_files_processed': len(file_stats),
        'total_records': len(all_records),
        'processing_timestamp': datetime.now().isoformat(),
    }
    
    # Count unique metric names
    metric_names = Counter()
    hosts = Counter()
    environments = Counter()
    
    for record in all_records:
        if 'metric_name' in record:
            metric_names[record['metric_name']] += 1
        if 'host' in record:
            hosts[record['host']] += 1
        if 'environment' in record:
            environments[record['environment']] += 1
            
    stats.update({
        'unique_metrics': len(metric_names),
        'unique_hosts': len(hosts),
        'unique_environments': len(environments),
        'top_metrics': dict(metric_names.most_common(5)),
        'top_hosts': dict(hosts.most_common(5)),
        'environments': dict(environments),
    })
    
    # File-level statistics  
    stats['file_statistics'] = file_stats
    
    return stats


def write_summary_file(summary_stats, output_path):
    """
    Write summary statistics to a CSV file.
    
    Args:
        summary_stats (dict): Summary statistics dictionary
        output_path (str): Path for the summary CSV file
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Metric', 'Value'])
            
            # Write basic stats
            for key, value in summary_stats.items():
                if key not in ['top_metrics', 'top_hosts', 'environments', 'file_statistics']:
                    writer.writerow([key, value])
                    
            # Write top metrics
            if 'top_metrics' in summary_stats:
                writer.writerow(['', ''])
                writer.writerow(['Top Metrics', 'Count'])
                for metric, count in summary_stats['top_metrics'].items():
                    writer.writerow([metric, count])
                    
            # Write file statistics
            if 'file_statistics' in summary_stats:
                writer.writerow(['', ''])
                writer.writerow(['File', 'Records', 'Errors'])
                for filename, stats in summary_stats['file_statistics'].items():
                    writer.writerow([filename, stats['record_count'], len(stats['errors'])])
                    
        return True, None
        
    except Exception as e:
        return False, f"Error writing summary file: {e}"


def process_metrics_pipeline():
    """
    Main function to process all NDJSON files in the metrics pipeline.
    
    Returns:
        tuple: (success boolean, results summary)
    """
    # Define paths
    script_dir = Path(__file__).parent
    ndjson_dir = script_dir / 'ndjson'
    csv_dir = script_dir / 'csv'
    
    # Find all NDJSON files
    ndjson_pattern = str(ndjson_dir / '*.ndjson')
    ndjson_files = glob.glob(ndjson_pattern)
    
    if not ndjson_files:
        return False, f"No NDJSON files found in {ndjson_dir}"
        
    print(f"Found {len(ndjson_files)} NDJSON file(s) to process")
    
    # Process each file
    all_records = []
    file_stats = {}
    total_errors = []
    
    for ndjson_file in ndjson_files:
        print(f"\nProcessing: {ndjson_file}")
        
        # Parse the NDJSON file
        records, errors = parse_ndjson_file(ndjson_file)
        
        # Track statistics
        filename = os.path.basename(ndjson_file)
        file_stats[filename] = {
            'record_count': len(records),
            'errors': errors
        }
        
        if errors:
            print(f"  Warnings: {len(errors)} parsing errors")
            total_errors.extend(errors)
            
        if records:
            print(f"  Parsed: {len(records)} records")
            all_records.extend(records)
            
            # Generate output CSV filename
            csv_filename = os.path.splitext(filename)[0] + '.csv'
            csv_path = csv_dir / csv_filename
            
            # Write CSV file
            success, error = write_csv_file(records, str(csv_path))
            if success:
                print(f"  Output: {csv_path}")
            else:
                print(f"  Error: {error}")
                total_errors.append(error)
        else:
            print(f"  No valid records found in {filename}")
    
    # Calculate and write summary statistics
    if all_records:
        summary_stats = calculate_summary_stats(all_records, file_stats)
        summary_path = csv_dir / 'summary_stats.csv'
        
        success, error = write_summary_file(summary_stats, str(summary_path))
        if success:
            print(f"\nSummary statistics written to: {summary_path}")
        else:
            print(f"\nError writing summary: {error}")
            total_errors.append(error)
    
    # Final results
    results = {
        'files_processed': len(ndjson_files),
        'total_records': len(all_records),
        'total_errors': len(total_errors),
        'csv_files_created': len([f for f in file_stats.values() if f['record_count'] > 0]),
    }
    
    print(f"\n=== Processing Complete ===")
    print(f"Files processed: {results['files_processed']}")
    print(f"Total records: {results['total_records']}")
    print(f"CSV files created: {results['csv_files_created']}")
    print(f"Errors encountered: {results['total_errors']}")
    
    if total_errors:
        print("\nErrors:")
        for error in total_errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(total_errors) > 10:
            print(f"  ... and {len(total_errors) - 10} more errors")
    
    return len(total_errors) == 0, results


if __name__ == "__main__":
    success, results = process_metrics_pipeline()
    sys.exit(0 if success else 1)