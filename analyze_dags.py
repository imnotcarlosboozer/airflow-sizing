#!/usr/bin/env python3
"""
DAG Compute Location Analyzer

Analyzes Airflow DAG files to determine what percentage of tasks run
compute in-worker vs on external systems.

Usage:
    python3 analyze_dags.py <dags_directory>
"""

import os
import sys
import glob
import json
from collections import defaultdict
from pathlib import Path


# Operator classifications
IN_WORKER_OPERATORS = {
    'PythonOperator',
    'BashOperator',
    'PythonVirtualenvOperator',
    'BranchPythonOperator',
    'ShortCircuitOperator',
    'SimpleHttpOperator',
    'EmailOperator',
    'SlackWebhookOperator',
}

EXTERNAL_COMPUTE_OPERATORS = {
    # Cloud Storage
    'S3Operator', 'S3CopyObjectOperator', 'S3DeleteObjectsOperator', 'S3FileTransformOperator',
    'GCSOperator', 'GCSToGCSOperator', 'GCSDeleteObjectsOperator',
    'AzureBlobStorageOperator',

    # Data Warehouses
    'SnowflakeOperator', 'SnowflakeSqlApiOperator',
    'BigQueryOperator', 'BigQueryInsertJobOperator', 'BigQueryGetDataOperator',
    'RedshiftSQLOperator', 'RedshiftDataOperator',
    'AthenaOperator',

    # Compute Engines
    'SparkSubmitOperator', 'SparkSqlOperator',
    'DatabricksRunNowOperator', 'DatabricksSubmitRunOperator',
    'EMRAddStepsOperator', 'EMRCreateJobFlowOperator',
    'DataprocSubmitJobOperator', 'DataprocCreateClusterOperator',
    'GlueJobOperator',

    # Container/Kubernetes
    'ECSOperator', 'ECSRunTaskOperator',
    'EKSPodOperator', 'GKEStartPodOperator',
    'KubernetesPodOperator',
    'DataflowOperator', 'DataflowCreatePythonJobOperator',

    # Data Tools
    'DbtRunOperator', 'DbtTestOperator', 'DbtCloudRunJobOperator',
    'FivetranOperator',
    'AirbyteOperator',

    # Databases
    'PostgresOperator', 'MySqlOperator', 'MsSqlOperator',
    'OracleOperator', 'SqliteOperator',

    # ML Platforms
    'SageMakerTrainingOperator', 'SageMakerTransformOperator',
    'VertexAITrainingJobOperator',
    'DataRobotOperator',
}

AMBIGUOUS_OPERATORS = {
    'DockerOperator',  # Could be local or remote
    'PythonSensor', 'HttpSensor', 'S3KeySensor',  # Sensors - generally lightweight
    'TriggerDagRunOperator',  # Meta-orchestration
}


def analyze_dag_file(filepath):
    """
    Analyze a single DAG file and count operator usage.

    Returns dict with counts of each operator type found.
    """
    operator_counts = defaultdict(int)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple pattern matching for operator instantiation
        # Format: OperatorName( or OperatorName (
        for operator in IN_WORKER_OPERATORS:
            # Count instances like: PythonOperator( or PythonOperator (
            count = content.count(f'{operator}(')
            if count > 0:
                operator_counts[operator] = count

        for operator in EXTERNAL_COMPUTE_OPERATORS:
            count = content.count(f'{operator}(')
            if count > 0:
                operator_counts[operator] = count

        for operator in AMBIGUOUS_OPERATORS:
            count = content.count(f'{operator}(')
            if count > 0:
                operator_counts[operator] = count

    except Exception as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)

    return operator_counts


def categorize_operators(operator_counts):
    """
    Categorize operator counts into in-worker, external, and ambiguous.
    """
    in_worker = 0
    external = 0
    ambiguous = 0

    in_worker_detail = defaultdict(int)
    external_detail = defaultdict(int)
    ambiguous_detail = defaultdict(int)

    for operator, count in operator_counts.items():
        if operator in IN_WORKER_OPERATORS:
            in_worker += count
            in_worker_detail[operator] = count
        elif operator in EXTERNAL_COMPUTE_OPERATORS:
            external += count
            external_detail[operator] = count
        elif operator in AMBIGUOUS_OPERATORS:
            ambiguous += count
            ambiguous_detail[operator] = count

    return {
        'in_worker': in_worker,
        'external': external,
        'ambiguous': ambiguous,
        'in_worker_detail': dict(in_worker_detail),
        'external_detail': dict(external_detail),
        'ambiguous_detail': dict(ambiguous_detail)
    }


def analyze_dags_directory(dags_dir):
    """
    Analyze all Python files in a DAGs directory.

    Returns comprehensive statistics about operator usage.
    """
    dags_path = Path(dags_dir)

    if not dags_path.exists():
        print(f"Error: Directory {dags_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    if not dags_path.is_dir():
        print(f"Error: {dags_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Find all Python files
    dag_files = list(dags_path.rglob('*.py'))

    if not dag_files:
        print(f"Warning: No Python files found in {dags_dir}", file=sys.stderr)
        return None

    print(f"Analyzing {len(dag_files)} DAG files...", file=sys.stderr)

    # Aggregate counts across all files
    total_counts = defaultdict(int)

    for dag_file in dag_files:
        file_counts = analyze_dag_file(dag_file)
        for operator, count in file_counts.items():
            total_counts[operator] += count

    # Categorize
    categorized = categorize_operators(total_counts)

    total_tasks = categorized['in_worker'] + categorized['external'] + categorized['ambiguous']

    result = {
        'summary': {
            'total_dag_files': len(dag_files),
            'total_tasks': total_tasks,
            'in_worker_tasks': categorized['in_worker'],
            'external_tasks': categorized['external'],
            'ambiguous_tasks': categorized['ambiguous'],
        },
        'percentages': {},
        'breakdown': categorized
    }

    # Calculate percentages
    if total_tasks > 0:
        result['percentages'] = {
            'in_worker_pct': round(categorized['in_worker'] / total_tasks * 100, 1),
            'external_pct': round(categorized['external'] / total_tasks * 100, 1),
            'ambiguous_pct': round(categorized['ambiguous'] / total_tasks * 100, 1),
        }

    return result


def format_output(result):
    """Format analysis result as human-readable text."""
    if not result:
        return "No data to display."

    summary = result['summary']
    pct = result['percentages']
    breakdown = result['breakdown']

    output = []
    output.append("=" * 60)
    output.append("DAG COMPUTE LOCATION ANALYSIS")
    output.append("=" * 60)
    output.append("")

    output.append(f"Total DAG files analyzed: {summary['total_dag_files']}")
    output.append(f"Total tasks found: {summary['total_tasks']}")
    output.append("")

    if summary['total_tasks'] > 0:
        output.append("COMPUTE LOCATION BREAKDOWN:")
        output.append("-" * 60)
        output.append(f"In-Worker Compute:  {summary['in_worker_tasks']:4d} tasks ({pct['in_worker_pct']:5.1f}%)")
        output.append(f"External Compute:   {summary['external_tasks']:4d} tasks ({pct['external_pct']:5.1f}%)")
        output.append(f"Ambiguous:          {summary['ambiguous_tasks']:4d} tasks ({pct['ambiguous_pct']:5.1f}%)")
        output.append("")

        if breakdown['in_worker_detail']:
            output.append("IN-WORKER OPERATORS:")
            output.append("-" * 60)
            for op, count in sorted(breakdown['in_worker_detail'].items(), key=lambda x: x[1], reverse=True):
                output.append(f"  {op:30s}: {count:4d}")
            output.append("")

        if breakdown['external_detail']:
            output.append("EXTERNAL COMPUTE OPERATORS:")
            output.append("-" * 60)
            for op, count in sorted(breakdown['external_detail'].items(), key=lambda x: x[1], reverse=True):
                output.append(f"  {op:30s}: {count:4d}")
            output.append("")

        if breakdown['ambiguous_detail']:
            output.append("AMBIGUOUS OPERATORS:")
            output.append("-" * 60)
            for op, count in sorted(breakdown['ambiguous_detail'].items(), key=lambda x: x[1], reverse=True):
                output.append(f"  {op:30s}: {count:4d}")
            output.append("")

    output.append("=" * 60)
    output.append("")
    output.append("NOTES:")
    output.append("- In-worker: Tasks that execute code within Airflow workers")
    output.append("- External: Tasks that trigger compute on external systems")
    output.append("- Ambiguous: Tasks that could be either (e.g., DockerOperator, Sensors)")
    output.append("- Analysis is based on operator type heuristics")

    return "\n".join(output)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_dags.py <dags_directory>", file=sys.stderr)
        sys.exit(1)

    dags_dir = sys.argv[1]

    result = analyze_dags_directory(dags_dir)

    if result:
        # Print human-readable output
        print(format_output(result))

        # Also output JSON for programmatic use
        json_file = 'dag_analysis_result.json'
        with open(json_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nDetailed results saved to: {json_file}", file=sys.stderr)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
