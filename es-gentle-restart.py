import argparse
import time
import settings
import elasticsearch
from fabric.api import settings as fabric_settings
from fabric.api import sudo


class ESClient():
    def __init__(self, host, port, timeout):
        self.es = elasticsearch.Elasticsearch(
            [{'host': host, 'port': port}], timeout=timeout,
            max_retries=6, retry_on_timeout=True)

    def get_master_node(self):
        current_master = self.es.cat.master(format='json')
        if len(current_master) == 0:
            raise Exception("No one master nodes found")
        return current_master[0].get('node')

    def get_nodes_list(self):
        es_masters_list = list()
        es_datanodes_list = list()
        es_nodes_list = self.es.cat.nodes(format='json')
        for node in es_nodes_list:
            if node.get('node.role') == 'm':
                es_masters_list.append(node)
            elif node.get('node.role') == 'd':
                es_datanodes_list.append(node)
        return es_masters_list, es_datanodes_list

    def get_cluster_status(self):
        try:
            es_health = self.es.cat.health(format='json')[0]
            es_cluster_status = es_health.get('status')
            es_cluster_pending_tasks = es_health.get('pending_tasks')
        except Exception as e:
            print('Error: {}'.format(e))
        return es_cluster_status, es_cluster_pending_tasks

    def poll_cluster_status(self):
        while True:
            try:
                cluster_status = self.get_cluster_status()
            except Exception as e:
                print('Error: {}'.format(e))
                time.sleep(5)
                print('Retrying connection...')
                continue
            print(cluster_status[0])
            if cluster_status[0] == 'green':
                print('ES cluster status: {} - done'.format(cluster_status))
                break
            else:
                print('Polling ES cluster status...{}'.format(cluster_status))
                time.sleep(5)


def es_node_service_restart(es_node_hostname, service_name):
    with fabric_settings(serial=True, eagerly_disconnect=True,
                         host_string=es_node_hostname,
                         key=settings.secret_key,
                         user=settings.remote_user,
                         timeout=45):
        try:
            print('Restarting ES service {} on host: {}'.format(
                service_name, es_node_hostname))
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
        if node_name != settings.anchor_master:
            es_node_service_restart(node_name, service)
            time.sleep(60)
        ESClient(settings.anchor_master, settings.es_port,
                 settings.timeout).poll_cluster_status()


def restart_master():
    current_master = ESClient(settings.anchor_master,
                              settings.es_port,
                              settings.timeout).get_master_node()
    es_node_service_restart(current_master, 'master_elasticsearch')
    time.sleep(60)
    ESClient(settings.anchor_master, settings.es_port,
             settings.timeout).poll_cluster_status()
    print('Current master - {} restarted'.format(current_master))


def print_node_list(node_list):
    for node in node_list:
        print('\n {} - {}'.format(node.get('node.role'), node.get('name')))


def get_master_back_to_anchor():
    while True:
        current_master = ESClient(settings.anchor_master,
                                  settings.es_port,
                                  settings.timeout).get_master_node()
        if current_master != settings.anchor_master:
            es_node_service_restart(current_master, 'master_elasticsearch')
            time.sleep(10)
        else:
            break
    print('Current master is moved to {}'.format(settings.anchor_master))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--anchor-master', help="Current master in cluster",
                        action='store', required=False, dest='anchor_master')
    parser.add_argument('--user', help="User to connect servers in cluster"
                                       " (must have a passwordless sudo)",
                        action='store', required=False, dest='secret_user')
    parser.add_argument('--key', help="User key to connect servers in cluster",
                        action='store', required=False, dest='ssh_key')
    parser.add_argument('--dry-run', help='Print current ES cluster layout',
                        action='store_true', dest='dry_run')

    args = parser.parse_args()

    if args.ssh_key:
        settings.secret_key = args.ssh_key
    if args.secret_user:
        settings.remote_user = args.secret_user
    if args.anchor_master:
        settings.anchor_master = args.anchor_master

    client = ESClient(settings.anchor_master, settings.es_port,
                      settings.timeout)
    es_masters_list, es_datanodes_list = client.get_nodes_list()
    es_cluster_status, es_cluster_pending_tasks = ESClient(
        settings.anchor_master, settings.es_port,
        settings.timeout).get_cluster_status()
    print('Current cluster layout: \n ===============\n Current master node:')
    print(client.get_master_node())
    print(' \n ===============\n Master nodes:')
    print_node_list(es_masters_list)
    print(' \n ===============\n Data nodes:')
    print_node_list(es_datanodes_list)
    print(' \n ===============\n Current cluster status is: {}, '
          'pending tasks: {}'.format(es_cluster_status,
                                     es_cluster_pending_tasks))
    if args.dry_run is False:
        print('Restarting ES cluster services')
        ESClient(settings.anchor_master, settings.es_port,
                 settings.timeout).poll_cluster_status()
        restart_nodes(es_masters_list, 'master_elasticsearch')
        restart_nodes(es_datanodes_list, 'data_elasticsearch')
        print ('Restarting ES cluster current master')
        restart_master()
        get_master_back_to_anchor()
        ESClient(settings.anchor_master, settings.es_port,
                 settings.timeout).poll_cluster_status()
        print('\n ===============\n ES cluster restart completed.')


if __name__ == '__main__':
    main()
