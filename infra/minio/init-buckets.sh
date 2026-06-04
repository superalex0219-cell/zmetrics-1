#!/bin/sh
set -e

echo "Waiting for MinIO to be ready..."
sleep 5

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

echo "Creating buckets..."
mc mb --ignore-existing "local/$MINIO_BUCKET_FRAMES"
mc mb --ignore-existing "local/$MINIO_BUCKET_ARTIFACTS"

echo "Setting bucket policies..."
# Frames bucket: private (authenticated access only)
mc anonymous set none "local/$MINIO_BUCKET_FRAMES"
# Artifacts bucket: private
mc anonymous set none "local/$MINIO_BUCKET_ARTIFACTS"

echo "MinIO buckets initialized:"
mc ls local/
