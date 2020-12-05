import requests
from flask import Flask, request

from utils import (
    get_healthy_server,
    healthcheck,
    load_configuration,
    process_firewall_rules_flag,
    process_rules,
    process_rewrite_rules,
    transform_backends_from_config,
)


loadbalancer = Flask(__name__)

config = load_configuration('loadbalancer.yaml')
register = transform_backends_from_config(config)


@loadbalancer.route('/')
@loadbalancer.route('/<path>')
def router(path='/'):
    updated_register = healthcheck(register)
    host_header = request.headers['Host']

    if not process_firewall_rules_flag(config, host_header, request.environ['REMOTE_ADDR'], f'/{path}'):
        return 'Forbidden', 403

    for entry in config['hosts']:
        if host_header == entry['host']:
            healthy_server = get_healthy_server(entry['host'], updated_register)
            if not healthy_server:
                return 'No backend servers available.', 503
            headers = process_rules(config, host_header, {k:v for k,v in request.headers.items()}, 'header')
            params = process_rules(config, host_header, {k:v for k,v in request.args.items()}, 'param')
            rewrite_path = ''
            if path == 'v1':
                rewrite_path = process_rewrite_rules(config, host_header, path)
            response = requests.get(f'http://{healthy_server.endpoint}/{rewrite_path}', headers=headers, params=params)
            return response.content, response.status_code

    for entry in config['paths']:
        if ('/' + path) == entry['path']:
            healthy_server = get_healthy_server(entry['path'], register)
            if not healthy_server:
                return 'No backend servers available.', 503
            healthy_server.open_connections += 1
            response = requests.get(f'http://{healthy_server.endpoint}')
            healthy_server.open_connections -= 1
            return response.content, response.status_code

    return 'Not Found', 404
