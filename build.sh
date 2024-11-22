#!/bin/bash

# Submit the build to Cloud Build
gcloud builds submit \
  --config cloudbuild.yaml \
  .