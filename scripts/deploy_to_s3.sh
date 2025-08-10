#!/bin/bash

# Deploy script for uploading metrics and build artifacts to S3
# This script checks for required environment variables and AWS CLI availability
# and degrades gracefully if they are not present.

set -e

echo "=== Deploy to S3 Script ==="

# Check for required environment variables
REQUIRED_VARS=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY" "S3_BUCKET")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        MISSING_VARS+=("$var")
    fi
done

if [[ ${#MISSING_VARS[@]} -ne 0 ]]; then
    echo "INFO: Missing required environment variables: ${MISSING_VARS[*]}"
    echo "INFO: Skipping S3 deployment (this is non-fatal)"
    exit 0
fi

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "INFO: AWS CLI is not installed"
    echo "INFO: Skipping S3 deployment (this is non-fatal)"
    exit 0
fi

echo "INFO: All requirements met, proceeding with S3 deployment"
echo "INFO: Target bucket: s3://$S3_BUCKET/"

# Configure AWS CLI with environment variables
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Define source directories
METRICS_DIR="metrics_pipeline/csv"
BUILD_DIR="dist"

# Function to sync directory if it exists
sync_directory() {
    local source_dir=$1
    local s3_prefix=$2
    
    if [[ -d "$source_dir" ]]; then
        echo "INFO: Syncing $source_dir to s3://$S3_BUCKET/$s3_prefix"
        if aws s3 sync "$source_dir" "s3://$S3_BUCKET/$s3_prefix" --delete; then
            echo "INFO: Successfully synced $source_dir"
        else
            echo "WARNING: Failed to sync $source_dir"
            return 1
        fi
    else
        echo "INFO: Directory $source_dir does not exist, skipping"
    fi
}

# Track deployment success
DEPLOY_SUCCESS=true

# Sync metrics CSV files
if ! sync_directory "$METRICS_DIR" "metrics/"; then
    DEPLOY_SUCCESS=false
fi

# Sync built frontend files
if ! sync_directory "$BUILD_DIR" ""; then
    DEPLOY_SUCCESS=false
fi

# Final status
if [[ "$DEPLOY_SUCCESS" == "true" ]]; then
    echo "=== Deployment Completed Successfully ==="
    echo "INFO: Files available at:"
    echo "  - Metrics: https://$S3_BUCKET.s3.$AWS_DEFAULT_REGION.amazonaws.com/metrics/"
    echo "  - Website: https://$S3_BUCKET.s3.$AWS_DEFAULT_REGION.amazonaws.com/"
else
    echo "=== Deployment Completed with Warnings ==="
    echo "WARNING: Some files may not have been uploaded successfully"
fi

exit 0