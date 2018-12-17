from mercury.common.exceptions import MercuryGeneralException
from mercury.common.helpers import cli

HWEVENT_SEARCH_TERM = 'Hardware event. This is not a software error.'
JOURNALCTL_COMMAND = 'journalctl -a --output cat --unit=mcelog.service ' \
                     '--no-pager'


def get_mcelog_journal_stream():
    p = cli.run(JOURNALCTL_COMMAND, raw=True)
    if p.returncode:
        raise MercuryGeneralException('Error getting mcelog')

    return p.stdout


def query_mcelog_daemon(mcelog_path='mcelog'):
    """
    Used to expose memory error counts
    :param mcelog_path:
    :return:
    """
    mcelog = cli.find_in_path(mcelog_path)
    if not mcelog:
        raise MercuryGeneralException('Could not find mcelog')

    result = cli.run(f'{mcelog} --client', raise_exception=False)
    return result.stdout


def count_logged_events():
    """
    Searches data stream and returns a count of HWEVENT_SEARCH_TERM
    :param data:
    :return:
    """
    count = 0
    for line in get_mcelog_journal_stream().readlines():
        if HWEVENT_SEARCH_TERM in line.decode('utf-8'):
            count += 1
    return count


if __name__ == '__main__':
    print(count_logged_events())
