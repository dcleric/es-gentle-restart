import os

remote_user = os.environ.get('DEPLOY_USER_NAME', 'deploy')
secret_key = os.environ.get('DEPLOY_USER_PEM')
anchor_master = "127.0.0.1"
es_port = '9200'
