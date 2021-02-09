#!/bin/bash

IMAGENAME="DOCKER-IMAGE-NAME"

usage()
{
  echo "Usage: $0 -v <image version> -u <pdnd user>"
  exit 2
}

set_variable()
{
  local varname=$1
  shift
  if [ -z "${!varname}" ]; then
    eval "$varname=\"$@\""
  else
    echo "Error: $varname already set"
    usage
  fi
}

while getopts v:u: flag
do
    case "${flag}" in
        v) set_variable VERSION $OPTARG ;;
        u) set_variable USERNAMEPAGOPA $OPTARG ;;
    esac
done

[ -z "$VERSION" ] && usage
[ -z "$USERNAMEPAGOPA" ] && usage

NEXUS=gateway.pdnd.dev

docker login $NEXUS -u user -p user >&  /dev/null

TAG=$NEXUS/$IMAGENAME

docker pull $TAG:$VERSION

docker logout $NEXUS >& /dev/null

VAULT_PAIR=$(curl --silent --insecure -H "X-Vault-Token: $VAULT_TOKEN" --request GET "$VAULT_ADDR"/v1/secret/data/pdnd-prod/users/$USERNAMEPAGOPA | jq '.data | .data | { workload_username: .workload_username, password: .password}')

WORKLOAD_USERNAME=$(echo "$VAULT_PAIR" | jq -r '.workload_username')
PASSWORD=$(echo "$VAULT_PAIR" | jq -r '.password')

cat > config.json << EOF
{
  "kernel_python_credentials" : {
    "username": "$WORKLOAD_USERNAME",
    "password": "$PASSWORD",
    "url": "https://pdnd-prod-dh-1-master0.pdnd-pro.qbnn-s7j3.cloudera.site/pdnd-prod-dh-1/cdp-proxy-api/livy/",
    "auth": "Basic_Access"
  },

  "kernel_scala_credentials" : {
    "username": "$WORKLOAD_USERNAME",
    "password": "$PASSWORD",
    "url": "https://pdnd-prod-dh-1-master0.pdnd-pro.qbnn-s7j3.cloudera.site/pdnd-prod-dh-1/cdp-proxy-api/livy/",
    "auth": "Basic_Access"
  },

  "logging_config": {
    "version": 1,
    "formatters": {
      "magicsFormatter": { 
        "format": "%(asctime)s\t%(levelname)s\t%(message)s",
        "datefmt": ""
      }
    },
    "handlers": {
      "magicsHandler": { 
        "class": "hdijupyterutils.filehandler.MagicsFileHandler",
        "formatter": "magicsFormatter",
        "home_path": "~/.sparkmagic"
      }
    },
    "loggers": {
      "magicsLogger": { 
        "handlers": ["magicsHandler"],
        "level": "DEBUG",
        "propagate": 0
      }
    }
  },

  "wait_for_idle_timeout_seconds": 15,
  "livy_session_startup_timeout_seconds": 60,

  "fatal_error_suggestion": "The code failed because of a fatal error:\n\t{}.\n\nSome things to try:\na) Make sure Spark has enough available resources for Jupyter to create a Spark context.\nb) Contact your Jupyter administrator to make sure the Spark magics library is configured correctly.\nc) Restart the kernel.",

  "ignore_ssl_errors": false,

  "session_configs": {
    "driverMemory": "1000M",
    "executorCores": 2
  },

  "use_auto_viz": true,
  "coerce_dataframe": true,
  "max_results_sql": 2500,
  "pyspark_dataframe_encoding": "utf-8",
  
  "heartbeat_refresh_seconds": 30,
  "livy_server_heartbeat_timeout_seconds": 0,
  "heartbeat_retry_seconds": 10,

  "server_extension_default_kernel_name": "pysparkkernel",
  "custom_headers": {},
  
  "retry_policy": "configurable",
  "retry_seconds_to_sleep_list": [0.2, 0.5, 1, 3, 5],
  "configurable_retry_policy_max_retries": 8
}
EOF

docker run --name bash -p 8888:8888 -t -i --rm -v `pwd`/config.json:/root/.sparkmagic/config.json -v $HOME:/home -v /tmp:/tmp -v /tmp:/.cache -e VAULT_ADDR=$VAULT_ADDR -e VAULT_TOKEN=$VAULT_TOKEN $TAG:$VERSION /bin/bash

rm -f config.json
