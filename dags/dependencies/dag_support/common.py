import os
import warnings

import hvac
import requests

warnings.filterwarnings('ignore')

def post_message_to_slack(text):
    vclient = hvac.Client(
        url=os.environ['VAULT_ADDR'],
        token=os.environ['VAULT_TOKEN'],
        verify=False
    )
    read_response = vclient.secrets.kv.read_secret_version(path='pdnd-prod/users/airflow')
    slack_url = read_response['data']['data']['slack_url']
    return requests.post(slack_url, json={
          'text': text
        }
    )

def on_failure_message_to_slack(context):
    message= """{mention}
    **Task Failed.**
    **Task**: ```{task}```  
    **Dag**: ```{dag}``` 
    **Execution Time**: ```{exec_date}```  
    """.format(
        mention=context.get('dag').owner,
        task=context.get('task_instance').task_id,
        dag=context.get('task_instance').dag_id,
        ti=context.get('task_instance'),
        exec_date=context.get('execution_date'))
    post_message_to_slack(message)
