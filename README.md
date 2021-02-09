# Motivation

This repo is a template, meant to provide a common skeleton and shared guidelines.

# Pipeline

Jenkins pipeline is spit in two steps:
- dags deploy: deploys in airflow the dags stored in `dags` folder
- docker push: build the dockerfile stored in `docker` folder and pushes it on nexus

# Versioning

Both dags and docker images use the same version, which is retrieved directly in Jenkins pipeline.

# How to setup

## Notebooks

Place all notebooks inside `notebooks` directory. Dockerfile will copy all files present in that directory to the root of the Docker image.
In case you need some particular dependency, you need to install it.

Example:

```dockerfile
ARG nexus

FROM $nexus/jobs/jupyter-job:latest

RUN apt-get update
RUN apt-get install -y build-essential python-dev

RUN pip install gspread

COPY notebooks ./
```

## Airflow Dags

### Dag name

Dag name should be versioned. Suggested format for the dag name is the following:
```
{dag_name}-{version}
```
To handle this it's possible to use the function `dag_name` provided by the `utils` package.
Example:

```python
from airflow import DAG
from utils import dag_name

dag = DAG(
    dag_name('my-dag'),
    default_args=default_args,
    schedule_interval=None,
    catchup=False)
```

### KubernetesPodOperator configuration

Namespace for the `KubernetesPodOperator` should be `airflow-v2`.

The version of the image used should be the same as the version of the dag. To handle this it's possible to use the function `docker_image` provided by the `utils` package.

Example:

```python
from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator
from utils import docker_image

t1 = KubernetesPodOperator(namespace='airflow-v2',
                           provide_context=True,
                           image=docker_image(NEXUS_ADDR + "/my-image"),
                           image_pull_policy='Always',
                           image_pull_secrets='regcred',
                           cmds=["papermill"],
                           arguments=["my-notebook.ipynb", "out.ipynb"],
                           name="my-task",
                           task_id="my-task",
                           get_logs=True,
                           is_delete_operator_pod=True,
                           dag=dag
                           )

```

# Git Workflow

The suggested use of this repository should follow [Trunk-Based Development](https://trunkbaseddevelopment.com/).

Version numbers will follow the [semantic versioning](https://semver.org) guidelines.

- `master` branch will always contain the most updated version of the software.
- Release branches will be used to create tags that will be associated with a particular release.
- A release branch will be associated to all the releases with the same major and minor number.

## Naming conventions

Release branch: `{major}.{minor}.x`. Example: `1.0.x`

Version tag: `v{major}.{minor}.{patch}`. Example: `v1.0.0`

## Workflow

All new features and bug fixes should be developed in a separate branch and merged to `master` through a Pull Request. Only small commits should be allowed directly to the master branch.

### New version (major or minor)

Example: create a new version 1.2.0

1. Create the release branch `1.2.x`
2. Create a tag `v1.2.0`. It is encoureged to use the Github releases. In that case you can also specify the title of the release and a description, which could include the release notes. 
3. Continuous Integration pipeline is triggered

### New patch

Example: fix a typo in version 1.2.0, releasing a new version 1.2.1

1. Commit patch to `master`. E.g. commit hash: `a591dcbfd1c1b3f1616de0810670ce6658fedc0b`
2. Cherry-pick the commit from `master` to the branch `1.2.x`
    ```shell
    git checkout 1.2.x
    git cherry-pick a591dcbfd1c1b3f1616de0810670ce6658fedc0b
    ```
3. Create a tag `v1.2.1`
4. Continuous Integration pipeline is triggered



