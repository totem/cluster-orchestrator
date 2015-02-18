from functools import wraps
import logging
from encryption.security import decrypt_obj
from encryption.store.s3 import S3Provider
from conf.appconfig import ENCRYPTION

logger = logging.getLogger(__name__)


def get_s3_store():
    return S3Provider(ENCRYPTION['s3']['bucket'],
                      keys_base=ENCRYPTION['s3']['base'])


def using_encryption_store(fun):
    @wraps(fun)
    def outer(*args, **kwargs):
        if ENCRYPTION['store'] == 's3':
            kwargs.setdefault('store', get_s3_store())
        else:
            logger.warn('No valid encryption store found. '
                        'Please set env. variable  ENCRYPTION_STORE to one of'
                        'supported values ["s3",]. Defaulting to in-memory '
                        'store. ')
        kwargs.setdefault('passphrase', ENCRYPTION['passphrase'])
        return fun(*args, **kwargs)
    return outer


@using_encryption_store
def decrypt_config(config, profile='default', store=None, passphrase=None):
    return decrypt_obj(config, profile=profile, store=store,
                       passphrase=passphrase)
