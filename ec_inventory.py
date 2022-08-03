#!/usr/bin/env python3
import argparse
from logging import warning

from boto3 import Session
from botocore.exceptions import ClientError


class Ec2Inventory(object):

    def __init__(self):
        self.inventory = {}
        self.args = self.parse_args
        self.ec2 = self._session(self.args.region)
        if self.args.list:
            self.inventory = self._build_inventory
        print(self.inventory)

    def _session(self, region):
        session = Session(
            aws_access_key_id=self.args.aws_access_key_id,
            aws_secret_access_key=self.args.aws_secret_access_key,
            region_name=region
        )
        ec2 = session.resource('ec2')
        return ec2

    @property
    def _filter(self):
        filters = []
        for tag in self.args.tags:
            k, v = tag.split('=')
            filters_dict = {'Name': k, 'Values': [v]}
            filters.append(filters_dict)
        return filters

    @property
    def _build_inventory(self):

        data = {'_meta': {'hostvars': {}},
                self.args.region: {'hosts': [],
                                   'vars': dict(ansible_host_key_checking='false')
                                   }
                }
        instances = self.ec2.instances.filter(
            Filters=self._filter)
        try:
            for instance in instances:
                name_tag = [tag['Value'] for tag in instance.tags if tag['Key'] == 'Name']
                if len(name_tag) > 0:
                    name = name_tag[0]
                else:
                    name = instance.id
                image = self.ec2.Image(instance.image_id)
                data[self.args.region]['hosts'].append(name)
                data['_meta']['hostvars'][name] = {}
                data['_meta']['hostvars'][name]['ansible_host'] = instance.private_ip_address
                if 'amzn2-ami' in image.name:
                    data['_meta']['hostvars'][name]['ansible_user'] = 'ec2-user'
                elif 'ubuntu' or 'cis-hardened' in image.name:
                    data['_meta']['hostvars'][name]['ansible_user'] = 'ubuntu'
        except (TypeError, AttributeError, ClientError) as e:
            warning(e)
        return data

    @property
    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list',
                            action='store_true')

        parser.add_argument('-k', '--access-key',

                            action='store',
                            help="AWS access key",
                            dest="aws_access_key_id",
                            required=True)

        parser.add_argument('-s', '--secret-key',
                            action='store',
                            help="AWS secret access key",
                            dest="aws_secret_access_key",
                            required=True)

        parser.add_argument('-r', '--region',
                            action='store',
                            help="AWS region to scan",
                            dest="region",
                            required=True)

        parser.add_argument('-t', '--tags',
                            metavar="KEY=VALUE",
                            nargs='+',
                            action='store',
                            help="Tags to filter by in k=v format",
                            dest="tags", required=True)
        return parser.parse_args()


if __name__ == "__main__":
    Ec2Inventory()
