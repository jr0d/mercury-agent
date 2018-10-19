"""
Drive erase methods for targeting os level block devices
"""

import logging
import os
import random
import time
import uuid
from datetime import timedelta

from press.helpers import parted

from mercury.common.helpers import cli
from mercury.common.exceptions import MercuryGeneralException, MercuryCritical

log = logging.getLogger(__name__)


def get_block_device_size(device):
    return parted.PartedInterface(device).get_size()


def open_target_sync(target):
    """ Get file descriptor with synchronous writes """
    return os.open(target, os.O_WRONLY | os.O_DSYNC)


def write_random_signatures(target, target_size_bytes, number):
    signature_map = [
        (uuid.uuid4().bytes, random.randint(0, int(
            (target_size_bytes-16)/16))*16)
        for _ in range(number)]

    target_fd = open_target_sync(target)
    try:
        for sig, offset in signature_map:
            os.pwrite(target_fd, sig, offset)
    finally:
        os.close(target_fd)

    return signature_map


def validate_erased(target, signature_map):
    target_fd = os.open(target, os.O_RDONLY)
    try:
        for sig, offset in signature_map:
            if os.pread(target_fd, 16, offset) == sig:
                return False
    finally:
        os.close(target_fd)
    return True


def buffered_zero_fill(target, target_size_bytes, buffer_size_bytes=4194304):
    """ Native python buffered zero fill implementation """
    # less memory efficient, but fastest
    zero_buffer = b'\x00' * buffer_size_bytes
    target_fd = open_target_sync(target)
    try:
        for _ in range(0, target_size_bytes, buffer_size_bytes):
            os.write(target_fd, zero_buffer)
    finally:
        os.close(target_fd)


def ssd_swap_discard(target):
    """ Use swapspace discard support to trigger TRIM across the entire block
    device """
    def _run(command):
        try:
            return cli.run(command, raise_exception=True)
        except cli.CLIException as e:
            raise MercuryCritical(
                'CLI error during drive erase; target: {}, error: {}'.format(
                    target, e))

    log.info('Creating swapspace on %s', target)

    _run('mkswap --force {}'.format(target))

    log.info('Activating swap space with the discard option')
    _run('swapon --discard=once {}'.format(target))

    log.info('Deactivating swap')
    _run('swapoff {}'.format(target))

    log.info('Removing gpt/mbr/file system signatures')
    _run('wipefs -o 0xff6 {}'.format(target))


def erase(target, method='zero', buffer_size_bytes=4194304,
          verification_blocks=4):
    """ Erase block device using the provided method
    :param target:
    :param method:
    :param buffer_size_bytes:
    :param verification_blocks:
    :return: statistics
    """
    start = time.time()
    target_size = get_block_device_size(target)

    log.info('Writing %s verification signatures to %s',
             verification_blocks, target)
    signature_map = write_random_signatures(
        target, target_size, verification_blocks)

    log.info('Beginning %s operation on %s [size: %s]', method, target,
             target_size)
    if method == 'zero':
        buffered_zero_fill(target, target_size, buffer_size_bytes)
    elif method == 'ssd_trim':
        ssd_swap_discard(target)
    else:
        raise MercuryGeneralException(
            f'Unsupported erase method specified: {method}')

    if not validate_erased(target, signature_map):
        raise MercuryCritical('Could not validate erase procedure, '
                              'Signatures are intact! {}'.format(signature_map))
    completed_at = time.time()
    time_taken = completed_at - start
    speed_stat = (target_size / time_taken / 2**20)  # MB/s
    log.info('Wipe operation completed in %s [%s MB/s]', timedelta(
        seconds=round(completed_at - start)), speed_stat)

    return {'start_time': start, 'completed_at': completed_at,
            'target_size': target_size, 'target': target,
            'speed': f'{speed_stat} MB/s'}
