# Motivation

This repo is a template, meant to provide a common skeleton and shared guidelines.

# Pipeline

Jenkins pipeline is spit in two steps:
- dags deploy: deploys in airflow the dags stored in `dags` folder
- docker push: build the dockerfile stored in `docker` folder and pushes it on nexus

# Versioning

Both dags and docker images use the same version, which is retrieved directly in Jenkins pipeline.