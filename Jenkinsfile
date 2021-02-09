pipeline {

  agent none
  environment {
      PROJECT = 'pdnd-pipeline-template'
  }

  stages {
    stage('Deploy DAGS') {
      agent { label 'airflow-template' }
      steps {
        container('airflow-container') {

          script {

            sh '''
              apk add bash
              bash
            '''

            sh '''#!/bin/bash
            cp -r dags /mnt/efs/airflow-dags/$PROJECT
            '''

          }
        }
      }
    }


    stage('Docker Push') {
      agent { label 'docker-template' }
      environment {
        NEXUS = 'gateway.pdnd.dev'
        NEXUS_CREDENTIALS = credentials('pdnd-nexus')
        JOBNAME = 'example-job'
        VERSION = 'v1.0.0'
      }
      steps {
          container('docker-container') {
            script {
              sh '''

              cp -r notebooks/* docker/
              cd docker
              TAG=$NEXUS/$JOBNAME

              docker login $NEXUS -u $NEXUS_CREDENTIALS_USR -p $NEXUS_CREDENTIALS_PSW >&  /dev/null
              docker build --build-arg nexus=$NEXUS -t $JOBNAME:$VERSION .
              docker tag $JOBNAME:$VERSION \$TAG:$VERSION
              docker push \$TAG:$VERSION
              docker logout $NEXUS >& /dev/null
              '''
          }
        }
      }
    }
  }
}