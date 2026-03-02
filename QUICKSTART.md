# Quick Start Guide

## Installation

The skill is already installed at:
```
~/.claude/skills/airflow-sizing/
```

## Usage

Simply invoke the skill:
```
/airflow-sizing
```

Claude will:
1. ✅ Detect your Airflow platform(s) automatically
2. ✅ Request confirmation before collecting data
3. ✅ Gather comprehensive environment information
4. ✅ Analyze DAG compute patterns
5. ✅ Generate a detailed sizing report

## Prerequisites Checklist

### For AWS MWAA
- [ ] AWS CLI installed (`aws --version`)
- [ ] AWS credentials configured (`aws configure` or `aws sso login`)
- [ ] Required IAM permissions:
  - `mwaa:*` (read access)
  - `cloudwatch:GetMetricStatistics`
  - `s3:ListBucket` (for DAG bucket)

### For Google Cloud Composer
- [ ] gcloud CLI installed (`gcloud --version`)
- [ ] Authenticated (`gcloud auth login`)
- [ ] Required permissions:
  - `composer.environments.*` (read access)
  - `monitoring.timeSeries.list`
  - `storage.objects.list`

### For OSS Airflow (Kubernetes)
- [ ] kubectl installed and configured (`kubectl version`)
- [ ] Access to Airflow namespace
- [ ] RBAC permissions to read pods/deployments

### For OSS Airflow (Direct)
- [ ] SSH/direct access to Airflow server
- [ ] `airflow` CLI available
- [ ] Read access to config and DAG directory

## Quick Permission Check

```bash
# AWS MWAA
aws mwaa list-environments

# Google Composer
gcloud composer environments list

# Kubernetes
kubectl get pods -A | grep airflow

# Direct Airflow
airflow version
```

If any of these commands work, you're ready to run the assessment!

## What You'll Get

A comprehensive report including:
- 📊 **Environment Overview**: Platform, region, Airflow version
- ⚙️ **Configuration**: Executor type, machine sizes, autoscaling
- 📈 **Performance Metrics**: CPU/memory usage, DAG runtimes
- 🔍 **Compute Analysis**: In-worker vs external compute breakdown
- 💡 **Recommendations**: Optimization opportunities

## Example Output

```
Environment: prod-airflow (AWS MWAA)
├─ Region: us-east-1
├─ Size: mw1.large (4 vCPU, 8GB)
├─ Workers: 2-10 (autoscaling)
├─ DAGs: 47 active
├─ CPU Usage: 45% avg
└─ Compute: 75% external, 25% in-worker

Top Operators:
  SnowflakeOperator: 120 tasks
  S3Operator: 95 tasks
  PythonOperator: 85 tasks
```

## Troubleshooting

### "Command not found: aws/gcloud/kubectl"
Install the required CLI tool for your platform.

### "Access denied" or "Permission denied"
Check IAM/RBAC permissions. You need read-only access.

### "No DAGs found"
The skill will still generate a report with infrastructure info.

### "Cannot connect to Airflow API"
For Kubernetes, the skill can use `kubectl exec` as fallback.

## Next Steps After Assessment

1. **Review the report** - Look for optimization opportunities
2. **Compare environments** - Identify inconsistencies
3. **Plan migrations** - Use data for capacity planning
4. **Optimize costs** - Right-size resources based on actual usage
5. **Improve architecture** - Move compute externally where appropriate

## Support

For issues or enhancements:
- Check EXAMPLES.md for detailed workflows
- Review README.md for complete documentation
- Modify analyze_dags.py to add custom operators

## Tips

- ⚡ Run during business hours for representative CPU/memory metrics
- 📅 Collect data over multiple days for better averages
- 🔄 Re-run periodically to track trends
- 💾 Save reports for historical comparison
- 🌍 Run separately for each region/environment

---

**Ready to start?** Just type `/airflow-sizing` in Claude Code!
