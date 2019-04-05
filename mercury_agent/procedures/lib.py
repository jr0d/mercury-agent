import os

import requests


# TODO: calculate hash while downloading file
def download_file(url, download_path):
    try:
        r = requests.get(url, stream=True)
    except requests.RequestException as err:
        raise err

    if os.path.isfile(download_path):
        os.remove(download_path)

    with open(download_path, 'wb') as f:
        for _chunk in r.iter_content(1024 ** 2):
            if _chunk:
                f.write(_chunk)
