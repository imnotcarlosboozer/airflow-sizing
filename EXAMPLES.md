# Airflow Sizing Skill - Examples

## Example Workflows

### Example 1: Assessing AWS MWAA Environment

**User invokes:**
```
/airflow-sizing
```

**Skill execution:**

1. **Platform Detection**
```bash
$ aws mwaa list-environments
{
    "Environments": ["prod-airflow", "dev-airflow"]
}
```

2. **Environment Details**
```bash
$ aws mwaa get-environment --name prod-airflow
{
    "Environment": {
        "Name": "prod-airflow",
        "WebserverUrl": "https://xxx.airflow.amazonaws.com",
        "ExecutionRoleArn": "arn:aws:iam::...",
        "EnvironmentClass": "mw1.large",
        "MinWorkers": 2,
        "MaxWorkers": 10,
        "Schedulers": 2,
        "AirflowVersion": "2.8.1",
        "SourceBucketArn": "arn:aws:s3:::my-dags-bucket",
        "DagS3Path": "dags/"
    }
}
```

3. **Get Metrics**
```bash
$ aws cloudwatch get-metric-statistics \
  --namespace AmazonMWAA \
  --metric-name CPUUtilization \
  --dimensions Name=Environment,Value=prod-airflow Name=Function,Value=Worker \
  --start-time 2026-03-01T00:00:00Z \
  --end-time 2026-03-02T00:00:00Z \
  --period 3600 \
  --statistics Average

Average CPU: 45%
```

4. **Get DAGs**
```bash
# Get CLI token and call Airflow API
$ aws mwaa create-cli-token --name prod-airflow
$ curl https://xxx.airflow.amazonaws.com/api/v1/dags

Total DAGs: 47 (42 active, 5 paused)
```

5. **Download and Analyze DAGs**
```bash
$ aws s3 sync s3://my-dags-bucket/dags ./mwaa-dags
$ python3 analyze_dags.py ./mwaa-dags

In-worker: 125 tasks (25%)
External: 375 tasks (75%)
```

**Generated Report:**
```markdown
# Airflow Sizing Assessment Report
**Generated**: 2026-03-02 14:30:00 UTC

## Executive Summary
- Total Environments: 2 (prod-airflow, dev-airflow)
- Total DAGs: 47 active
- Primary Executor: Celery (MWAA managed)
- Compute Model: 25% in-worker, 75% external

## Environment: prod-airflow

**Platform**: AWS MWAA
**Region**: us-east-1
**Airflow Version**: 2.8.1

### Configuration
- Environment Class: mw1.large (4 vCPU, 8GB RAM)
- Workers: Min 2, Max 10 (auto-scaling enabled)
- Schedulers: 2

### Current Utilization
- CPU: 45% average (p50: 42%, p90: 68%)
- Memory: 62% average (p50: 59%, p90: 78%)

### DAG Metrics
- Total DAGs: 47 (42 active, 5 paused)
- Total Tasks: ~500
- Average Runtime:
  - p50: 12 minutes
  - p90: 45 minutes
  - Average: 18 minutes

### Compute Location
**In-worker (25%)**:
- PythonOperator: 85 instances
- BashOperator: 40 instances

**External (75%)**:
- SnowflakeOperator: 120 instances
- S3Operator: 95 instances
- BigQueryOperator: 80 instances
- SparkSubmitOperator: 45 instances
- DbtOperator: 35 instances

### Recommendations
1. ✅ Autoscaling is well-configured (current max workers rarely hit)
2. ✅ Majority of compute is external - good architecture
3. ⚠️  Consider upgrading to mw1.xlarge if p90 CPU >80%
4. 💡 Review PythonOperator tasks - candidates for moving to external compute
```

---

### Example 2: Assessing OSS Airflow on Kubernetes

**User invokes:**
```
/airflow-sizing
```

**Skill execution:**

1. **Platform Detection**
```bash
$ kubectl get pods -A | grep airflow
airflow    airflow-scheduler-0         1/1   Running
airflow    airflow-webserver-0         1/1   Running
airflow    airflow-worker-0            1/1   Running
```

2. **Get Configuration**
```bash
$ helm get values airflow-release -n airflow
executor: CeleryExecutor
workers:
  replicas: 3
  resources:
    requests:
      cpu: 1000m
      memory: 2Gi
    limits:
      cpu: 2000m
      memory: 4Gi
```

3. **Get Node Information**
```bash
$ kubectl get nodes -o json | jq '.items[] | {instance: .metadata.labels["node.kubernetes.io/instance-type"]}'
Instance type: m5.xlarge (4 vCPU, 16GB RAM)
```

4. **Get Metrics**
```bash
$ kubectl top pods -n airflow
NAME                    CPU     MEMORY
airflow-scheduler-0     250m    1500Mi
airflow-webserver-0     100m    800Mi
airflow-worker-0        850m    2800Mi
airflow-worker-1        900m    3100Mi
airflow-worker-2        720m    2600Mi
```

5. **Get DAGs and Analyze**
```bash
$ kubectl exec -it airflow-scheduler-0 -n airflow -- airflow dags list
Total: 32 DAGs

$ kubectl cp airflow-scheduler-0:/opt/airflow/dags ./k8s-dags -n airflow
$ python3 analyze_dags.py ./k8s-dags

In-worker: 280 tasks (60%)
External: 187 tasks (40%)
```

**Key Insight**: This environment is more in-worker heavy, suggesting potential for optimization by moving compute externally.

---

### Example 3: Assessing Google Cloud Composer

**User invokes:**
```
/airflow-sizing
```

**Skill execution:**

1. **List Environments**
```bash
$ gcloud composer environments list
NAME          LOCATION    STATE
prod-composer us-central1 RUNNING
```

2. **Get Details**
```bash
$ gcloud composer environments describe prod-composer --location us-central1

config:
  nodeConfig:
    machineType: n1-standard-4
  softwareConfig:
    airflowVersion: 2.7.3
    executorType: CELERY
  workloadsConfig:
    scheduler:
      cpu: 2
      memoryGb: 7.5
      count: 2
    worker:
      cpu: 2
      memoryGb: 7.5
      minCount: 2
      maxCount: 6
```

3. **Get DAGs**
```bash
$ gcloud composer environments run prod-composer --location us-central1 dags list
Total: 28 DAGs (25 active)
```

4. **Download DAGs**
```bash
$ gsutil -m cp -r gs://us-central1-prod-composer-bucket/dags ./composer-dags
$ python3 analyze_dags.py ./composer-dags

In-worker: 95 tasks (35%)
External: 175 tasks (65%)
```

5. **Get Monitoring Metrics**
```bash
$ gcloud monitoring time-series list \
  --filter='resource.type="cloud_composer_environment" AND metric.type="composer.googleapis.com/environment/worker/cpu_usage"'

Average worker CPU: 38%
```

---

## Common Patterns Found

### Pattern 1: Well-Architected (External-Heavy)
```
In-worker: 20-30%
External: 70-80%

Characteristics:
- Most data processing in Snowflake/BigQuery/Spark
- Airflow used primarily for orchestration
- Lower resource requirements
- Easier to scale
```

### Pattern 2: Compute-Heavy (In-Worker)
```
In-worker: 60-80%
External: 20-40%

Characteristics:
- Heavy use of PythonOperator
- Data transformations in Python
- Higher resource requirements
- May benefit from moving compute externally
```

### Pattern 3: Hybrid
```
In-worker: 40-60%
External: 40-60%

Characteristics:
- Mix of in-worker data processing and external jobs
- Often in transition/migration phase
- Opportunities for optimization
```

---

## Troubleshooting

### Issue: AWS CLI not authenticated
```bash
$ aws configure
# Enter credentials

# Or use SSO
$ aws sso login
```

### Issue: kubectl not configured
```bash
# Get kubeconfig from cloud provider
$ aws eks update-kubeconfig --name my-cluster --region us-east-1
# or
$ gcloud container clusters get-credentials my-cluster --region us-central1
```

### Issue: Cannot access Airflow API
```bash
# For K8s, use port-forward
$ kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# Then access at localhost:8080
```

### Issue: No metrics available
```bash
# Check if metrics-server is installed (K8s)
$ kubectl get deployment metrics-server -n kube-system

# If not installed:
$ kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Issue: DAG analysis finds no operators
- Check if DAG files are in the expected format
- Verify Python files contain actual DAG definitions
- Some DAGs might use dynamic task generation

---

## Advanced Usage

### Custom Operator Classification

Edit `analyze_dags.py` to add your custom operators:

```python
EXTERNAL_COMPUTE_OPERATORS.add('MyCustomSparkOperator')
IN_WORKER_OPERATORS.add('MyCustomPythonOperator')
```

### Multi-Region Assessment

Run the skill separately for each region:

```bash
# Region 1
$ export AWS_DEFAULT_REGION=us-east-1
$ /airflow-sizing

# Region 2
$ export AWS_DEFAULT_REGION=eu-west-1
$ /airflow-sizing
```

### Historical Analysis

Adjust CloudWatch time windows for historical data:

```bash
$ aws cloudwatch get-metric-statistics \
  --start-time 2026-02-01T00:00:00Z \
  --end-time 2026-03-01T00:00:00Z \
  --period 86400  # Daily aggregation
```

### Export to JSON

Save report as structured data:

```json
{
  "environments": [
    {
      "name": "prod-airflow",
      "platform": "mwaa",
      "region": "us-east-1",
      "dags": 47,
      "workers": {"min": 2, "max": 10},
      "compute_ratio": {"in_worker": 0.25, "external": 0.75}
    }
  ]
}
```
