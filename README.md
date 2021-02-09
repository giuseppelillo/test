# Motivation

This repo is a template, meant to provide a common skeleton and shared guidelines.

# Pipeline

Jenkins pipeline is spit in two steps:
- dags deploy: deploys in airflow the dags stored in `dags` folder
- docker push: build the dockerfile stored in `docker` folder and pushes it on nexus

# Versioning

### Dags

When a new version is ready, we rename the dag file and we bump the version in the DAG ID.

```

$ mv example-dag-v0.0.0.py example-dag-v0.0.1.py
$ cat example-dag-v0.0.1.py
dag = DAG(
    'example-dag-v0.0.1',
    default_args=default_args,
    description='A simple tutorial DAG, but new awesome version',
    schedule_interval=timedelta(days=1),
)

```

**Benefits**

- Including the version in the file allows the previous version of the DAG not overwritten in the DAG folder. So you can rerun an older version of it.
- The dag history is clearly visible in Airflow UI

**N.B.**

If you change the version in the dag but you don't rename the file, you will have a new version of the dag displayed in Airflow but both the previous version and the new one will refer to the same updated file. So you have inconsistency.


### Docker

When a new version is ready, we modify the VERSION variable in the docker stage of the Jenkinsfile.
