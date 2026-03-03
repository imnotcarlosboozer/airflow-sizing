---
name: airflow-sizing
description: This skill should be used when the user asks to "size airflow", "assess airflow", "airflow sizing", "analyze airflow environment", mentions "MWAA", "Cloud Composer", or discusses Apache Airflow capacity planning, migration, or performance assessment.
version: 1.0.0
---

# Airflow Sizing Assessment Skill

You are performing a comprehensive sizing assessment of Apache Airflow environments. This skill supports:
- **OSS Airflow** (self-hosted on Kubernetes, VMs, or bare metal)
- **AWS MWAA** (Amazon Managed Workflows for Apache Airflow)
- **GCC** (Google Cloud Composer)

Your goal is to collect detailed information to help with migration planning, cost optimization, or capacity planning.

## Assessment Questions to Answer

1. **Cloud and Region** - Which cloud provider and region(s)?
2. **Number of Environments** - How many Airflow environments exist?
3. **Number of DAGs per Environment** - Total and active DAGs in each environment
4. **Average DAG Completion Time** - p50, p90, and avg runtime for recent runs
5. **Machine Sizes** - Instance types and their specs (CPU/memory)
6. **CPU/Memory Usage** - Current utilization metrics
7. **Executor Type** - CeleryExecutor, KubernetesExecutor, LocalExecutor, etc.
8. **K8s Executor Limits/Requests** - Resource configs for task pods (if using K8s)
9. **Celery Workers & Autoscaling** - Worker count, concurrency, and autoscaling config
10. **Compute Location** - Percentage of tasks running in-worker vs external systems

## Assessment Process

### Phase 1: Platform Detection

First, detect which Airflow platform(s) are in use:

1. **Check for MWAA**:
   - Run `aws mwaa list-environments` (if AWS CLI configured)
   - If successful and returns environments, this is MWAA

2. **Check for Google Cloud Composer**:
   - Run `gcloud composer environments list` (if gcloud CLI configured)
   - If successful and returns environments, this is Composer

3. **Check for OSS Airflow on Kubernetes**:
   - Run `kubectl config current-context` to check for K8s access
   - Run `helm list -A | grep -i airflow` or `kubectl get pods -A | grep -i airflow`
   - If Airflow pods/releases found, this is OSS on K8s

4. **Check for OSS Airflow via direct access**:
   - Try `airflow version` command
   - If successful, this is OSS (possibly on VMs or bare metal)

**Important**: An organization may have multiple platforms. Check all possibilities and assess each separately.

### Phase 2: Data Collection by Platform

#### For AWS MWAA:

```bash
# 1. List all environments
aws mwaa list-environments

# 2. For each environment, get details:
aws mwaa get-environment --name <env-name>

# 3. Get region
aws configure get region

# 4. Get Airflow CLI token and access Airflow API
aws mwaa create-cli-token --name <env-name>

# 5. Get CloudWatch metrics for CPU/Memory
aws cloudwatch get-metric-statistics \
  --namespace AmazonMWAA \
  --metric-name CPUUtilization \
  --dimensions Name=Environment,Value=<env-name> Name=Function,Value=Worker \
  --start-time <start> --end-time <end> \
  --period 3600 --statistics Average

# Similar for MemoryUtilization, SchedulerCPU, WebserverCPU, etc.

# 6. Get DAGs list via Airflow API (use base URL from get-environment)
# Use the CLI token to authenticate
curl -H "Authorization: Bearer <token>" \
  https://<webserver-url>/api/v1/dags

# 7. Get DAG runs for completion time analysis
curl -H "Authorization: Bearer <token>" \
  https://<webserver-url>/api/v1/dags/<dag-id>/dagRuns?limit=100
```

**MWAA-specific notes**:
- Executor is always Celery-based
- Environment class maps to machine sizes: mw1.small (1 vCPU, 2GB), mw1.medium (2 vCPU, 4GB), mw1.large (4 vCPU, 8GB), mw1.xlarge (8 vCPU, 16GB), mw1.2xlarge (16 vCPU, 32GB)
- MinWorkers, MaxWorkers, and Schedulers count are in environment details
- DAGs are stored in S3 - fetch them for compute location analysis

#### For Google Cloud Composer:

```bash
# 1. List all environments
gcloud composer environments list

# 2. For each environment, get details:
gcloud composer environments describe <env-name> --location <location>

# 3. Get region
gcloud config get-value compute/region

# 4. Get DAGs list
gcloud composer environments run <env-name> --location <location> dags list

# 5. Get DAG runs for a specific DAG
gcloud composer environments run <env-name> --location <location> dags list-runs -d <dag-id> --limit 100

# 6. Get Cloud Monitoring metrics
gcloud monitoring time-series list \
  --filter='resource.type="cloud_composer_environment" AND metric.type="composer.googleapis.com/environment/worker/cpu_usage"' \
  --format="table(metric.labels.workflow_name)"

# 7. Download DAGs for analysis
# DAGs bucket is shown in environment details
gsutil -m cp -r gs://<dag-bucket>/dags ./composer-dags/
```

**Composer-specific notes**:
- Machine types in nodeConfig (e.g., n1-standard-2, n2-standard-4)
- Composer 1 uses CeleryExecutor, Composer 2 uses managed executor
- Worker config shows minCount, maxCount, cpu, memoryGb
- Check Airflow version in environment details

#### For OSS Airflow on Kubernetes:

```bash
# 1. Get current context and cloud info
kubectl config current-context

# Check cloud provider (if on cloud)
kubectl get nodes -o json | jq -r '.items[0].spec.providerID'

# 2. Find Airflow namespaces/deployments
kubectl get namespaces | grep -i airflow
kubectl get pods -A | grep -i airflow
helm list -A | grep -i airflow

# 3. Get Helm values (if deployed via Helm)
helm get values <release-name> -n <namespace>

# 4. Get Airflow config
kubectl exec -it <scheduler-pod> -n <namespace> -- airflow config list
kubectl exec -it <scheduler-pod> -n <namespace> -- airflow config get-value core executor

# 5. Get DAGs list
kubectl exec -it <scheduler-pod> -n <namespace> -- airflow dags list

# 6. Get node information and machine sizes
kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, instance: .metadata.labels["node.kubernetes.io/instance-type"], cpu: .status.capacity.cpu, memory: .status.capacity.memory}'

# 7. Get resource metrics (requires metrics-server)
kubectl top nodes
kubectl top pods -n <namespace>

# 8. Get worker deployment details
kubectl get deployment -n <namespace> -l component=worker -o yaml

# 9. Check for HPA (Horizontal Pod Autoscaler)
kubectl get hpa -n <namespace>

# 10. For KubernetesExecutor, check pod template
kubectl exec -it <scheduler-pod> -n <namespace> -- airflow config get-value kubernetes pod_template_file
# If set, try to view the template file

# 11. For CeleryExecutor, get worker concurrency
kubectl exec -it <worker-pod> -n <namespace> -- airflow config get-value celery worker_concurrency

# 12. Access Airflow REST API (port-forward if needed)
kubectl port-forward svc/<airflow-webserver-service> -n <namespace> 8080:8080 &
# Then use curl to hit localhost:8080/api/v1/...

# 13. Copy DAGs for analysis
kubectl cp <scheduler-pod>:/opt/airflow/dags ./oss-dags -n <namespace>
```

**OSS-specific notes**:
- Executor type must be determined from config
- Resource limits/requests are in pod specs or Helm values
- May have Prometheus for better metrics
- More variability in deployment patterns

#### For OSS Airflow (Direct Access):

```bash
# 1. Get Airflow version and config
airflow version
airflow config list

# 2. Get executor type
airflow config get-value core executor

# 3. List DAGs
airflow dags list

# 4. For each DAG, get recent runs
airflow dags list-runs -d <dag-id> --limit 100

# 5. Check worker configuration (if Celery)
airflow config get-value celery worker_concurrency
airflow config get-value celery worker_autoscale

# 6. Find DAGs directory
airflow config get-value core dags_folder

# 7. Check database for detailed metrics (if accessible)
# This requires database credentials from config
# Query dag_run table for completion times
```

### Phase 3: DAG Analysis for Compute Location

Once you have DAGs downloaded (from S3, GCS, K8s pod, or local filesystem):

1. **Scan all Python files in the DAGs directory**
2. **Identify operator imports**:
   - **In-worker compute**: `PythonOperator`, `BashOperator`, `PythonVirtualenvOperator`, `DockerOperator` (local)
   - **External compute**: `SnowflakeOperator`, `BigQueryOperator`, `S3Operator`, `GCSOperator`, `RedshiftOperator`, `SparkSubmitOperator`, `DatabricksOperator`, `DbtOperator`, `ECSOperator`, `GKEOperator`, `DataflowOperator`, etc.

3. **Count task instantiations**:
   ```python
   # Example pattern matching:
   # - Look for operator instantiations: `SomeOperator(`
   # - Track which operators are used most frequently
   # - Calculate ratio of in-worker vs external
   ```

4. **Generate statistics**:
   - Total tasks across all DAGs
   - Percentage using in-worker compute
   - Percentage using external compute
   - Breakdown by operator type

**Implementation approach**:
```bash
# Use grep or ast parsing to analyze DAG files
grep -r "Operator(" <dags-directory> | sort | uniq -c

# More sophisticated: write a Python script to parse DAGs
python3 << 'EOF'
import os
import ast
import glob

in_worker_ops = {'PythonOperator', 'BashOperator', 'PythonVirtualenvOperator', 'DockerOperator'}
external_ops = {'SnowflakeOperator', 'BigQueryOperator', 'S3Operator', 'SparkSubmitOperator',
                'DatabricksOperator', 'DbtOperator', 'RedshiftOperator', 'GCSOperator',
                'ECSOperator', 'DataflowOperator', 'GKEOperator'}

in_worker_count = 0
external_count = 0

for dag_file in glob.glob('./dags/**/*.py', recursive=True):
    try:
        with open(dag_file, 'r') as f:
            content = f.read()
            for op in in_worker_ops:
                in_worker_count += content.count(f'{op}(')
            for op in external_ops:
                external_count += content.count(f'{op}(')
    except:
        pass

total = in_worker_count + external_count
if total > 0:
    print(f"In-worker tasks: {in_worker_count} ({in_worker_count/total*100:.1f}%)")
    print(f"External tasks: {external_count} ({external_count/total*100:.1f}%)")
EOF
```

### Phase 4: Report Generation

Generate a comprehensive sizing report with the following structure:

```markdown
# Airflow Sizing Assessment Report
**Generated**: [timestamp]
**Platform(s) Detected**: [MWAA/Composer/OSS]

---

## Executive Summary
- Total Environments: X
- Total DAGs: Y
- Primary Executor: Z
- Compute Model: [% in-worker vs % external]

---

## Environment Details

### Environment 1: [name]
**Platform**: [MWAA/Composer/OSS]
**Cloud/Region**: [AWS us-east-1 / GCP us-central1 / etc.]

#### Configuration
- **Airflow Version**: X.Y.Z
- **Executor**: [Celery/Kubernetes/Local]
- **Machine Sizes**:
  - Workers: [type] (X vCPU, Y GB RAM) x [count]
  - Scheduler: [type] (X vCPU, Y GB RAM) x [count]
  - Webserver: [type] (X vCPU, Y GB RAM) x [count]
- **Autoscaling**: Min [X] / Max [Y] workers

#### Current Utilization
- **CPU Usage**: [avg %] (p50: X%, p90: Y%)
- **Memory Usage**: [avg %] (p50: X%, p90: Y%)

#### DAG Metrics
- **Total DAGs**: X (Y active, Z paused)
- **Total Tasks**: ~X across all DAGs
- **Average DAG Runtime**:
  - p50: [duration]
  - p90: [duration]
  - Average: [duration]
- **Longest-running DAGs**: [list top 5 with runtimes]

#### Compute Location Analysis
- **In-worker compute**: X% of tasks
  - PythonOperator: Y instances
  - BashOperator: Z instances
- **External compute**: X% of tasks
  - [Top operator types with counts]

#### Resource Allocation (if K8s Executor)
- **Task Pod Requests**: X CPU, Y memory
- **Task Pod Limits**: X CPU, Y memory

#### Celery Configuration (if Celery Executor)
- **Worker Concurrency**: X tasks per worker
- **Worker Autoscale**: [min, max] if configured

---

## Recommendations

Based on the assessment, here are key findings:

1. **[Specific recommendation based on data]**
2. **[Another recommendation]**
3. **[Cost optimization opportunities if identified]**
4. **[Performance considerations]**

---

## Data Collection Notes

- [Any gaps in data collection]
- [Any assumptions made]
- [Any manual verification needed]
```

## Execution Guidelines

1. **Request Confirmation**: Before running any commands, inform the user about:
   - Which platforms you'll check
   - What commands you'll run (some may require credentials)
   - That they should ensure appropriate permissions are configured

2. **Handle Errors Gracefully**:
   - If a CLI is not found or not configured, note it and move to next platform
   - If API calls fail due to authentication, inform user and provide guidance
   - If metrics aren't available, note it in the report

3. **Parallel Collection**: Where possible, collect data from multiple environments in parallel

4. **Sensitive Data**: Remind user that the report may contain sensitive info (environment names, regions, etc.)

5. **Export Options**: Offer to save the report to a file (markdown or JSON format)

6. **Follow-up Actions**: After generating report, ask if user wants:
   - More detailed analysis of specific environments
   - Cost estimation based on the sizing data
   - Migration planning assistance
   - Optimization recommendations

## Important Notes

- **AWS Credentials**: MWAA assessment requires AWS CLI configured with appropriate IAM permissions (mwaa:ListEnvironments, mwaa:GetEnvironment, mwaa:CreateCliToken, cloudwatch:GetMetricStatistics, s3:ListBucket)
- **GCP Credentials**: Composer assessment requires gcloud CLI authenticated with Composer permissions (composer.environments.list, composer.environments.get, monitoring.timeSeries.list)
- **Kubernetes Access**: OSS on K8s requires kubectl configured and appropriate RBAC permissions
- **Airflow API**: May need to handle authentication (basic auth, OAuth, etc.)
- **Timeouts**: Some data collection (especially CloudWatch metrics) may take time - keep user informed of progress

## Example Usage

User invokes: `/airflow-sizing`

Expected interaction:
1. You detect platforms and inform user what you found
2. You request confirmation to proceed with data collection
3. You systematically collect data, showing progress
4. You analyze DAGs for compute location
5. You generate and display the comprehensive report
6. You offer to save report and suggest next steps
