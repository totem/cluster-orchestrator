from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future.builtins import (  # noqa
    bytes, dict, int, list, object, range, str,
    ascii, chr, hex, input, next, oct, open,
    pow, round, super,
    filter, map, zip)
import boto
from boto.s3.key import Key
import yaml
from orchestrator.cluster_config.base import AbstractConfigProvider


class S3ConfigProvider(AbstractConfigProvider):

    def __init__(self, bucket, config_base='totem/config'):
        self.bucket = bucket
        self.config_base = config_base

    def _s3_path(self, name, *paths):
        if paths:
            return '%s/%s/%s' % (self.config_base, '/'.join(paths),
                                 name)
        else:
            return '%s/%s' % (self.config_base, name)

    @staticmethod
    def _s3_connection():
        # Use default env variable or IAM roles to connect to S3.
        return boto.connect_s3()

    def _s3_bucket(self):
        """
        Gets S3 bucket for storing totem configuration.

        :return: S3 Bucket
        :rtype: S3Bucket
        """
        return self._s3_connection().get_bucket(self.bucket)

    def _get_key(self, name, *paths):
        key_path = self._s3_path(name, *paths)
        return self._s3_bucket().get_key(key_path)

    def write(self, name, config, *paths):
        key = Key(self._s3_bucket())
        key.key = self._s3_path(name, *paths)
        key.set_contents_from_string(yaml.dump(config))

    def load(self, name, *paths):
        key = self._get_key(name, *paths)
        if key:
            raw = key.get_contents_as_string()
            return yaml.load(raw)
        else:
            return {}

    def delete(self, name, *paths):
        key = self._get_key(name, *paths)
        if key:
            key.delete()
            return True
        return False
