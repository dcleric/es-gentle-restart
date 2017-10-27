import elasticsearch
from fabric.api import sudo
from fabric.api import settings
import time
import os
import argparse

secret_key = ""
remote_user = ""
anchor_master = ""


es = elasticsearch.Elasticsearch([{'host': anchor_master, 'port': 9200}])


def get_master_node():
    current_master = es.cat.master(format='json')[0].get('node')
    return current_master


def get_nodes_list():
    es_masters_list = list()
    es_datanodes_list = list()
    es_nodes_list = es.cat.nodes(format='json')
    for node in es_nodes_list:
        if node.get('node.role') == 'm':
            es_masters_list.append(node)
        elif node.get('node.role') == 'd':
            es_datanodes_list.append(node)
    return es_masters_list, es_datanodes_list


def get_cluster_status():
    try:
        es_health = es.cat.health(format='json')[0]
        es_cluster_status = es_health.get('status')
        es_cluster_pending_tasks = es_health.get('pending_tasks')
    except Exception as e:
        print('Error: {}'.format(e))
    return es_cluster_status, es_cluster_pending_tasks


def es_node_service_restart(es_node_hostname, service_name):
    try:
        print('Restarting ES service {} on host: {}'.format(service_name,
                                                            es_node_hostname))
        with settings(serial=True, host_string=es_node_hostname,
                      key=secret_key, user=remote_user):
            service_restart_result = sudo(
                'service {} restart'.format(service_name))
        if service_restart_result.return_code != 0:
            service_restart_status = 'Unsuccessful'
        else:
            service_restart_status = 'Successful'

        print('Restart of ES service {} on host: {}'
              ' - status:{}'.format(service_name, es_node_hostname,
                                    service_restart_status))

    except Exception as e:
        print('Error: {}'.format(e))


def restart_nodes(es_nodes_list, service):
    for node in es_nodes_list:
        node_name = node.get('name')
        if node_name != anchor_master:
            es_node_service_restart(node_name, service)
            time.sleep(10)
        poll_cluster_status()


def restart_master(current_master):
    es_node_service_restart(current_master, 'cron')
    time.sleep(10)
    poll_cluster_status()
    print('Current master - {} restarted'.format(current_master))


def poll_cluster_status():
    while True:
        cluster_status = get_cluster_status()
        print(cluster_status[0])
        if cluster_status[0] == 'green':
            print('ES cluster status: {} - done'.format(cluster_status))
            break
        else:
            print('Polling ES cluster status...{}'.format(cluster_status))
            time.sleep(5)


def print_node_list(node_list):
    for node in node_list:
        print('\n {} - {}'.format(node.get('node.role'), node.get('name')))


def get_master_back_to_anchor(es_masters_list):
    for node in es_masters_list:
        es_node_name = node.get('name')
        if get_master_node() != anchor_master:
            es_node_service_restart(es_node_name, 'master_elasticsearch')
        else:
            break
    print('Current master is moved to {}'.format(anchor_master))


def main():
    global secret_key
    global remote_user
    global anchor_master
    parser = argparse.ArgumentParser()
    parser.add_argument('--anchor-master', help="Current master in cluster",
                        action='store', required=True, dest='anchor_master')
    parser.add_argument('--user', help="User to connect servers in cluster"
                                       " (must have a passwordless sudo)",
                        action='store', required=True, dest='secret_user')
    parser.add_argument('--key', help="User key to connect servers in cluster",
                        action='store', required=False, dest='ssh_key')
    parser.add_argument('--dry-run', help='Print current ES cluster layout',
                        action='store_true', dest='dry_run')

    args = parser.parse_args()

    if args.ssh_key:
        secret_key = args.ssh_key
    else:
        secret_key = os.environ.get('DEPLOY_USER_PEM')
    if args.secret_user:
        remote_user = args.secret_user
    else:
        remote_user = 'deploy'

    es_masters_list, es_datanodes_list = get_nodes_list()
    es_cluster_status, es_cluster_pending_tasks = get_cluster_status()
    print('Current cluster layout: \n ===============\n Current master node:')
    print(get_master_node())
    print(' \n ===============\n Master nodes:')
    print_node_list(es_masters_list)
    print(' \n ===============\n Data nodes:')
    print_node_list(es_datanodes_list)
    print(' \n ===============\n Current cluster status is: {}, '
          'pending tasks: {}'.format(es_cluster_status,
                                     es_cluster_pending_tasks))
    if args.dry_run is False:
        print('Restarting ES cluster services')
        poll_cluster_status()
        restart_nodes(es_masters_list, 'master_elasticsearch')
        restart_nodes(es_datanodes_list, 'data_elasticsearch')
        es_masters_list, es_datanodes_list = get_nodes_list()
        get_master_back_to_anchor(es_masters_list)
        poll_cluster_status()
        print('\n ===============\n ES cluster restart completed.')


if __name__ == '__main__':
    main()
