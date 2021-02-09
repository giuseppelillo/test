import json
import os
import string
import subprocess
from copy import deepcopy
from random import shuffle, choice, randint

import boto3
import hvac
import requests
from airflow.utils.email import send_email

KEYCLOAK_URL = os.environ['VAULT_ADDR'] + '/auth'

NEXUS_ADDR = 'gateway.pdnd.dev'

def get_vault_client():
    client = hvac.Client(
        url=os.environ['VAULT_ADDR'],
        token=os.environ['VAULT_TOKEN'],
        verify=False
    )
    return client


def get_keycloak_token():
    client = get_vault_client()
    read_response = client.secrets.kv.read_secret_version(path='pdnd-prod/service-users/keycloak')
    keycloak_username = read_response['data']['data']['username']
    keycloak_password = read_response['data']['data']['password']
    data = {
        'username': keycloak_username,
        'password': keycloak_password,
        'grant_type': 'password',
        'client_id': 'admin-cli'
    }
    response = requests.post(KEYCLOAK_URL + '/realms/master/protocol/openid-connect/token', data=data, verify=False)
    token = response.json()['access_token']
    return token


class PasswordGenerator:
    """
    We can set properties such as
    | minlen     |   Minimum length of the password | 6\n
    | maxlen     |   Maximum length of the password | 16\n
    | minuchars  |   Minimum upper case characters required in password | 1\n
    | minlchars  |   Minimum lower case characters required in password | 1\n
    | minnumbers |   Minimum numbers required in password               | 1\n
    | minschars  |   Minimum special characters in the password         | 1\n
    Methods implemented in this class are
    generate() : Generates a password using default or custom propertiesself.
    shuffle_password(password, length) : Shuffle the given charactes and return a password from given characters.
    non_duplicate_password(length) : Generate a non duplicate key of givrn length
    """

    def __init__(self):
        self.minlen = 6
        self.maxlen = 16
        self.minuchars = 1
        self.minlchars = 1
        self.minnumbers = 1
        self.minschars = 1
        self.excludeuchars = ""
        self.excludelchars = ""
        self.excludenumbers = ""
        self.excludeschars = ""

        self.lower_chars = string.ascii_lowercase
        self.upper_chars = string.ascii_uppercase
        self.numbers_list = string.digits
        self._schars = [
            "!",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            ",",
            ".",
            "-",
            "_",
            "+",
            "=",
            "<",
            ">",
            "?",
        ]
        self._allchars = (
                list(self.lower_chars)
                + list(self.upper_chars)
                + list(self.numbers_list)
                + self._schars
        )

    def generate(self):
        """Generates a password using default or custom properties"""
        if (
                self.minlen < 0
                or self.maxlen < 0
                or self.minuchars < 0
                or self.minlchars < 0
                or self.minnumbers < 0
                or self.minschars < 0
        ):
            raise ValueError("Character length should not be negative")

        if self.minlen > self.maxlen:
            raise ValueError(
                "Minimum length cannot be greater than maximum length. The default maximum length is 16."
            )

        collectiveMinLength = (
                self.minuchars + self.minlchars + self.minnumbers + self.minschars
        )

        if collectiveMinLength > self.minlen:
            self.minlen = collectiveMinLength

        final_pass = [
            choice(list(set(self.lower_chars) - set(self.excludelchars)))
            for i in range(self.minlchars)
        ]
        final_pass += [
            choice(list(set(self.upper_chars) - set(self.excludeuchars)))
            for i in range(self.minuchars)
        ]
        final_pass += [
            choice(list(set(self.numbers_list) - set(self.excludenumbers)))
            for i in range(self.minnumbers)
        ]
        final_pass += [
            choice(list(set(self._schars) - set(self.excludeschars)))
            for i in range(self.minschars)
        ]

        currentpasslen = len(final_pass)
        all_chars = list(
            set(self._allchars)
            - set(
                list(self.excludelchars)
                + list(self.excludeuchars)
                + list(self.excludenumbers)
                + list(self.excludeschars)
            )
        )

        if len(final_pass) < self.maxlen:
            randlen = randint(self.minlen, self.maxlen)
            final_pass += [choice(all_chars) for i in range(randlen - currentpasslen)]

        shuffle(final_pass)
        return "".join(final_pass)

    def shuffle_password(self, password, maxlen):
        """Shuffle the given charactes and return a password from given characters."""
        final_pass = [choice(list(password)) for i in range(int(maxlen))]
        shuffle(final_pass)
        return "".join(final_pass)

    def non_duplicate_password(self, maxlen):
        """Generate a non duplicate key of given length"""
        allchars = deepcopy(self._allchars)
        final_pass = []
        try:
            for i in range(maxlen):
                character = choice(allchars)
                element_index = allchars.index(character)
                final_pass.append(character)
                allchars.pop(element_index)
        except IndexError as e:
            raise ValueError("Length should less than 77 characters.")

        shuffle(final_pass)
        return "".join(final_pass)


def synchronize_users():
    response = subprocess.run(['cdp', 'environments', 'sync-all-users', '--environment-names',
                               'crn:cdp:environments:us-west-1:9ad782ee-3322-4342-a3be-3a2348e0414e:environment:8c54812f-766c-45d0-84e9-3c531c5fd615'],
                              stdout=subprocess.PIPE, universal_newlines=True)
    operation_id = json.loads(response.stdout)['operationId']

    response = subprocess.run(['cdp', 'environments', 'sync-status', '--operation-id', operation_id],
                              stdout=subprocess.PIPE, universal_newlines=True)
    status = json.loads(response.stdout)['status']

    while status != 'COMPLETED':
        response = subprocess.run(['cdp', 'environments', 'sync-status', '--operation-id', operation_id],
                                  stdout=subprocess.PIPE, universal_newlines=True)
        status = json.loads(response.stdout)['status']


def get_username_and_password(username, **kwargs):
    client = get_vault_client()

    existent = True
    # Check if the user is alredy present
    try:
        client.secrets.kv.v2.read_secret_version(
            path='pdnd-prod/users/%s' % username
        )
    except hvac.exceptions.InvalidPath:
        existent = False

    if existent:
        user = client.secrets.kv.v2.read_secret_version(
            path='pdnd-prod/users/%s' % username
        )['data']['data']
        kwargs['ti'].xcom_push(key='username', value=user['username'])
        kwargs['ti'].xcom_push(key='password', value=user['password'])
    else:
        kwargs['ti'].xcom_push(key='username', value="null")
        kwargs['ti'].xcom_push(key='password', value="null")


def get_username_and_email(username, **kwargs):
    client = get_vault_client()

    existent = True
    # Check if the user is alredy present
    try:
        client.secrets.kv.v2.read_secret_version(
            path='pdnd-prod/users/%s' % username
        )
    except hvac.exceptions.InvalidPath:
        existent = False

    if existent:
        user = client.secrets.kv.v2.read_secret_version(
            path='pdnd-prod/users/%s' % username
        )['data']['data']
        kwargs['ti'].xcom_push(key='username', value=user['username'])
        kwargs['ti'].xcom_push(key='email', value=user['email'])
    else:
        kwargs['ti'].xcom_push(key='username', value="null")
        kwargs['ti'].xcom_push(key='email', value="email")


def add_to_identity_broker(org, suborg):
    vault_client = get_vault_client()

    read_response = vault_client.secrets.kv.read_secret_version(path='pdnd-prod/users/airflow')
    aws_access_key_id = read_response['data']['data']['aws_access_key_id']
    aws_secret_access_key = read_response['data']['data']['aws_secret_access_key']

    client = boto3.client('iam', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    response = client.get_role(
        RoleName='%s-%s' % (org, suborg)
    )

    # Get the role arn
    role_arn = response['Role']['Arn']

    try:
        # Create the group on cdp and get the group crn
        response = subprocess.run(['cdp', 'iam', 'create-group', '--group-name', '%s-%s' % (org, suborg)],
                                  stdout=subprocess.PIPE, universal_newlines=True)
        group = json.loads(response.stdout)
        crn = group['group']['crn']

        # Get the original mapping
        response = subprocess.run(['cdp', 'environments', 'get-id-broker-mappings', '--environment-name', 'pdnd-prod'],
                                  stdout=subprocess.PIPE, universal_newlines=True)

        mappings = json.loads(response.stdout)['mappings']

        # Add the new one
        mappings.append({'accessorCrn': crn, 'role': role_arn})

        subprocess.run(['cdp',
                        'environments',
                        'set-id-broker-mappings',
                        '--data-access-role', 'arn:aws:iam::688071769384:role/CDP_DATALAKE_ADMIN_ROLE',
                        '--ranger-audit-role', 'arn:aws:iam::688071769384:role/CDP_RANGER_AUDIT_ROLE',
                        '--environment-name', 'pdnd-prod',
                        '--mappings=' + json.dumps(mappings)], stdout=subprocess.PIPE, universal_newlines=True)

        subprocess.run(['cdp', 'environments', 'sync-id-broker-mappings', '--environment-name', 'pdnd-prod'])
    except:
        pass


def remove_from_identity_broker(org, suborg):
    vault_client = get_vault_client()

    read_response = vault_client.secrets.kv.read_secret_version(path='pdnd-prod/users/airflow')
    aws_access_key_id = read_response['data']['data']['aws_access_key_id']
    aws_secret_access_key = read_response['data']['data']['aws_secret_access_key']

    client = boto3.client('iam', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    try:
        response = client.get_role(
            RoleName='%s-%s' % (org, suborg)
        )

        # Get the role arn
        role_arn = response['Role']['Arn']

        # Get the group crn
        response = subprocess.run(['cdp', 'iam', 'list-groups'], stdout=subprocess.PIPE, universal_newlines=True)
        groups = json.loads(response.stdout)['groups']
        filtered_groups = list(filter(lambda group: group['groupName'] == '%s-%s' % (org, suborg), groups))
        crn = filtered_groups[0]['crn']

        # Get the original mapping
        response = subprocess.run(['cdp', 'environments', 'get-id-broker-mappings', '--environment-name', 'pdnd-prod'],
                                  stdout=subprocess.PIPE, universal_newlines=True)

        mappings = json.loads(response.stdout)['mappings']

        # Remove the mapping
        mappings.remove({'accessorCrn': crn, 'role': role_arn})

        subprocess.run(['cdp',
                        'environments',
                        'set-id-broker-mappings',
                        '--data-access-role', 'arn:aws:iam::688071769384:role/CDP_DATALAKE_ADMIN_ROLE',
                        '--ranger-audit-role', 'arn:aws:iam::688071769384:role/CDP_RANGER_AUDIT_ROLE',
                        '--environment-name', 'pdnd-prod',
                        '--mappings=' + json.dumps(mappings)], stdout=subprocess.PIPE, universal_newlines=True)

        # Sync mappings
        subprocess.run(['cdp', 'environments', 'sync-id-broker-mappings', '--environment-name', 'pdnd-prod'])

        # Remove the group
        subprocess.run(['cdp', 'iam', 'delete-group', '--group-name', '%s-%s' % (org, suborg)], stdout=subprocess.PIPE,
                       universal_newlines=True)
    except:
        pass


def recreate_user_tokens_and_policies():
    vault_client = get_vault_client()
    user_list = list(
        filter(lambda user: user != 'airflow', vault_client.secrets.kv.list_secrets('pdnd-prod/users')['data']['keys']))
    response = vault_client.sys.revoke_force(
        prefix='auth/token/create/',
    )
    for username in user_list:
        policy = '''
              path "secret/data/pdnd-prod/users/%s" {
                capabilities = ["read"]
              }
              ''' % username
        vault_client.sys.create_or_update_policy(
            name='read-user-%s' % username,
            policy=policy
        )
        token = \
            vault_client.create_token(policies=['read-user-%s' % username], ttl='48h', no_default_policy=True)['auth'][
                'client_token']
        vault_client.secrets.kv.v2.patch(
            path='pdnd-prod/users/%s' % username,
            secret=dict(token=token)
        )

        read_response = vault_client.secrets.kv.read_secret_version(path='pdnd-prod/users/%s' % username)
        email = read_response['data']['data']['email']

        notify(email, "New token notification", ("<p>"
                                                        "Hi,\n"
                                                        "This email is automatically generated to inform you that your token has been recreated.\n"
                                                        "Your new token is: {}\n\n"
                                                        "Keep it secret.</p>").format(token))

def renew_user_tokens():
    vault_client = get_vault_client()
    user_list = list(
        filter(lambda user: user != 'airflow', vault_client.secrets.kv.list_secrets('pdnd-prod/users')['data']['keys']))
    for username in user_list:
        user_token = vault_client.secrets.kv.v2.read_secret_version(
            path='pdnd-prod/users/%s' % username
        )['data']['data']['token']
        vault_client.renew_token(user_token, '48h')


def notify(addressee, subject, html_content):
    send_email(addressee, subject, html_content,
               files=None, cc=None, bcc=None,
               mime_subtype="mixed", mime_charset="iso-8859-1")


if __name__ == '__main__':
    recreate_user_tokens_and_policies()
