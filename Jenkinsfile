pipeline {

  agent none

  stages {
    stage('Deploy DAGS') {
      agent { label 'airflow-template' }
      steps {
        container('airflow-container') {

          script {

            sh '''
              apk add bash
              apk add zip
              apk add git
              bash
            '''

            sh '''#!/bin/bash

            VERSION=`git describe --abbrev=0 --tags`
            echo '__version__="'$VERSION'"' > dags/_version.py

            PROJECT=`basename $(pwd)`
            cd dags
            touch __init__.py
            zip  -r \$PROJECT.zip *
            cd ..
            cp dags/\$PROJECT.zip /mnt/efs/airflow-dags
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
      }
      steps {
          container('docker-container') {
            script {

              sh '''
              apk add bash
              apk add git
              '''

              sh '''

              VERSION=`git describe --abbrev=0 --tags`
              JOBNAME=`git config --local remote.origin.url|sed -n 's#.*/\\([^.]*\\)\\.git#\\1#p'`-image
              TAG=$NEXUS/\$JOBNAME
              docker login $NEXUS -u $NEXUS_CREDENTIALS_USR -p $NEXUS_CREDENTIALS_PSW >&  /dev/null
              docker build --network=host --build-arg nexus=$NEXUS -t \$JOBNAME:$VERSION .
              docker tag \$JOBNAME:\$VERSION \$TAG:\$VERSION
              docker push \$TAG:\$VERSION
              docker logout $NEXUS >& /dev/null
              '''
          }
        }
      }
    }
  }
}