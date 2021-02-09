ARG nexus

FROM $nexus/jobs/jupyter-job:latest

RUN apt-get update
RUN apt-get install -y build-essential python-dev

COPY notebooks ./