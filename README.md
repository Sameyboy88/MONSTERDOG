![Netlify examples](netlify-badge-examples.png)

# Netlify Feature Tour

**Access this demo site**: https://feature-tour.netlify.app

[![Netlify Status](https://api.netlify.com/api/v1/badges/fad6792e-1c44-44db-bd79-ea74b42b0f89/deploy-status)](https://app.netlify.com/sites/feature-tour/deploys)

## About this example site

This site provides a path to get started learning about Netlify features.

- 📚 [Docs Getting Started Tutorial](https://docs.netlify.com/get-started/?utm_medium=social&utm_source=github&utm_campaign=devex-ph&utm_content=devex-examples)

## Speedily deploy your own version

Deploy your own version of this example site by selecting the Deploy to Netlify Button below. This will automatically:

- Clone a copy of this repo to your own GitHub account
- Create a new project in your [Netlify account](https://app.netlify.com/?utm_medium=social&utm_source=github&utm_campaign=devex&utm_content=devex-examples), linked to your new repo
- Create an automated deployment pipeline to watch for changes on your repo
- Build and deploy your new site

[![Deploy To Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/netlify/netlify-feature-tour&utm_medium=social&utm_source=github&utm_campaign=devex&utm_content=devex-examples)

## Install and run this example locally

You can clone this example repo to explore its features and implementation and to run it locally.

```shell

# 1. Clone the repository to your local development environment
git clone git@github.com:netlify/feature-tour.git

# 2. Move into the project directory
cd feature-tour

# 3. Install code dependencies
npm install

# 4. Install the Netlify CLI to let you locally serve your site using Netlify's features
npm install -g netlify-cli

# 5. Serve your site using Netlify Dev
netlify dev

```

## Additional scripts

This repository includes optional Python utilities in `scripts/`.

- **flask_nft_interface.py** – a Flask + Dash application for minting NFTs and visualizing vortex data. Environment variables configure Web3 and IPFS.
- **MONSTERDOG_METRICS_ULTIMATE_TRIPLED.py** – merges local metric files, extracts Z-score anomalies, generates a PDF report, and launches a Dash dashboard to inspect results.

Install the dependencies listed in each script and run them with Python 3.9+.

## Metrics Pipeline & CI/CD

This repository includes a comprehensive metrics ingestion and aggregation pipeline that processes NDJSON log files and converts them to CSV format with summary statistics.

### Pipeline Overview

The metrics pipeline consists of the following components:

```
metrics_pipeline/
├── ndjson/                 # Raw .ndjson log files (input)
├── csv/                    # Aggregated CSV outputs (generated)
├── dashboards/             # HTML dashboards (future)
├── metrics_aggregate.py    # Main aggregation script
└── requirements.txt        # Python dependencies
```

### Usage

To run the metrics aggregation pipeline locally:

```bash
# Process all NDJSON files and generate CSV outputs
python metrics_pipeline/metrics_aggregate.py

# View generated CSV files
ls metrics_pipeline/csv

# Check summary statistics
cat metrics_pipeline/csv/summary_stats.csv
```

The script will:
1. Scan `metrics_pipeline/ndjson/*.ndjson` for input files
2. Parse line-delimited JSON records from each file
3. Generate corresponding CSV files in `metrics_pipeline/csv/`
4. Create a summary statistics file with aggregated metrics

### Sample Data

A sample NDJSON file is included for testing:
- `metrics_pipeline/ndjson/sample_system_metrics.ndjson` - Contains sample system metrics with various data types

### CI/CD Pipeline

The repository uses GitHub Actions to automate the metrics pipeline and deployment process:

#### Workflow Jobs

1. **metrics** - Processes NDJSON files and creates CSV artifacts
   - Runs Python aggregation script
   - Uploads CSV files as artifacts
   - Displays processing summary

2. **build-react** - Builds the frontend application (conditional)
   - Only runs if `package.json` exists
   - Installs dependencies with `npm install`
   - Builds project with `npm run build`
   - Uploads build artifacts

3. **deploy** - Deploys artifacts to S3 (main branch only)
   - Downloads metrics and build artifacts
   - Runs deployment script if available
   - Syncs files to S3 bucket (requires AWS credentials)

4. **validate** - Validates pipeline outputs
   - Checks for expected output files
   - Provides workflow summary

#### Triggering the Pipeline

The pipeline runs automatically on:
- Pushes to the `main` branch
- Pull requests to `main`
- Manual workflow dispatch

#### Artifacts

After successful execution, the following artifacts are available:
- **metrics-csv** - Contains all generated CSV files and summary statistics
- **build-artifacts** - Contains built frontend files (if applicable)

### Deployment

The deployment process uses the `scripts/deploy_to_s3.sh` script, which:
- Checks for required AWS environment variables
- Syncs CSV files to `s3://bucket/metrics/`
- Syncs built frontend to `s3://bucket/`
- Degrades gracefully if AWS CLI or credentials are unavailable

Required environment variables (configure in GitHub Secrets):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY` 
- `S3_BUCKET`
- `AWS_DEFAULT_REGION` (optional, defaults to us-east-1)

### Future Extensions

The pipeline is designed to support future enhancements:

- **Plotly Dashboard Generation**: Add interactive HTML charts from CSV data
- **Prometheus Remote Write**: Stream metrics to Prometheus for real-time monitoring  
- **Grafana Integration**: Import CSV data into Grafana for advanced visualization
- **Real-time Processing**: Process streaming NDJSON data as it arrives
- **Data Validation**: Add schema validation for incoming metrics
- **Alerting**: Generate alerts based on metric thresholds and anomalies
