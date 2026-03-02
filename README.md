# Airflow Sizing Assessment Skill

A comprehensive skill for analyzing Apache Airflow environments across different platforms to support migration planning, cost optimization, and capacity planning.

## Supported Platforms

- **AWS MWAA** (Amazon Managed Workflows for Apache Airflow)
- **Google Cloud Composer** (GCC)
- **OSS Airflow** (self-hosted on Kubernetes, VMs, or bare metal)

## What It Analyzes

1. **Infrastructure Details**
   - Cloud provider and region(s)
   - Number of environments
   - Machine sizes and instance types
   - Current CPU/Memory utilization

2. **Airflow Configuration**
   - Airflow version
   - Executor type (Celery, Kubernetes, Local)
   - Worker configuration and autoscaling
   - Kubernetes resource limits (if applicable)

3. **DAG Metrics**
   - Total DAG count (active and paused)
   - Average completion times (p50, p90, average)
   - Longest-running DAGs
   - Compute location analysis (in-worker vs external)

4. **Optimization Insights**
   - Resource utilization patterns
   - Autoscaling effectiveness
   - Cost optimization opportunities

## Prerequisites

### For AWS MWAA
- AWS CLI installed and configured
- IAM permissions:
  - `mwaa:ListEnvironments`
  - `mwaa:GetEnvironment`
  - `mwaa:CreateCliToken`
  - `cloudwatch:GetMetricStatistics`
  - `s3:ListBucket` (for DAG analysis)

### For Google Cloud Composer
- gcloud CLI installed and authenticated
- IAM permissions:
  - `composer.environments.list`
  - `composer.environments.get`
  - `monitoring.timeSeries.list`
  - `storage.objects.list` (for DAG analysis)

### For OSS Airflow on Kubernetes
- kubectl configured with access to the cluster
- RBAC permissions to:
  - List/describe pods, deployments, services
  - Execute commands in pods
  - Access Helm releases (if applicable)

### For OSS Airflow (Direct)
- SSH/direct access to Airflow installation
- Access to `airflow` CLI command
- Read access to Airflow config and DAG directory

## Usage

```bash
/airflow-sizing
```

The skill will:
1. Auto-detect available Airflow platforms
2. Request confirmation before collecting data
3. Systematically gather environment information
4. Analyze DAG files for compute patterns
5. Generate a comprehensive sizing report
6. Offer to save the report and suggest next steps

## Output

The skill generates a detailed markdown report containing:
- Executive summary with key metrics
- Per-environment breakdowns
- Configuration details
- Performance metrics
- Compute location analysis
- Recommendations for optimization

## Example Report Sections

```markdown
### Environment: production-airflow
**Platform**: AWS MWAA
**Region**: us-east-1

#### Configuration
- Airflow Version: 2.8.1
- Executor: Celery
- Machine Size: mw1.large (4 vCPU, 8GB RAM)
- Autoscaling: Min 2 / Max 10 workers

#### Current Utilization
- CPU Usage: 45% average (p50: 42%, p90: 68%)
- Memory Usage: 62% average (p50: 59%, p90: 78%)

#### DAG Metrics
- Total DAGs: 47 (42 active, 5 paused)
- Average Runtime: p50: 12m, p90: 45m, avg: 18m

#### Compute Location
- In-worker: 25% (PythonOperator: 45, BashOperator: 12)
- External: 75% (SnowflakeOperator: 89, S3Operator: 34)
```

## Notes

- Data collection is read-only and non-invasive
- Some metrics may require time to collect (especially CloudWatch)
- The skill handles authentication errors gracefully
- Compute location analysis uses heuristics (operator type detection)
- Report may contain sensitive information (environment names, regions)

## Tips

- Ensure all required CLIs are authenticated before running
- For multi-region deployments, run the assessment in each region
- Review IAM/RBAC permissions if data collection fails
- Save the report for future reference and comparison
- Use the recommendations section for planning next steps

## Future Enhancements

Potential additions:
- Database connection and pool analysis
- Plugin and provider packages inventory
- Security configuration assessment
- Network topology mapping
- Historical trend analysis
- Cost estimation integration
