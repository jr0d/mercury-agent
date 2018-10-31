import pkg_resources

from mercury_agent.inspector.inspectors import expose


@expose('agent_info')
def agent_inspector():
    _info = {
        'agent_version':
            pkg_resources.get_distribution('mercury-agent').version,
        'mercury_version':
            pkg_resources.get_distribution('mercury-core').version
    }
    return _info


if __name__ == '__main__':
    from pprint import pprint
    pprint(agent_inspector())
