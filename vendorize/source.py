import click
import os
import re
import urllib.request
import tarfile
from typing import List


import vendorize.git
import vendorize.util


class PartSource:
    def __init__(self, part_data: dict, project_folder: str,
                 allowed_hosts: list) -> None:
        self.project_folder = project_folder
        self.source = part_data.get('source', '.')
        self.should_vendor = vendorize.util.host_not_vendorized(
            self.source, allowed_hosts)
        self.type = self.guess_type(part_data.get('source-type'))
        if self.type == 'local':
            self.source = os.path.join(self.project_folder, self.source)
        elif self.type == 'git':
            self.branch = part_data.get('source-branch',
                                        part_data.get('source-tag'))

    def guess_type(self, source_type: str=None) -> str:
        if source_type:
            return source_type
        if os.path.isdir(os.path.join(self.project_folder, self.source)):
            return 'local'
        elif (self.source.startswith('git:') or
              self.source.startswith('git@') or
                self.source.endswith('.git')):
            return 'git'
        elif re.match(r'.*\.((tar(\.(xz|gz|bz2))?)|tgz)$', self.source):
            return 'tar'
        raise click.ClickException('Unknown source: {!r}'.format(self.source))

    def fetch(self, destination):
        if os.path.isdir(os.path.join(self.project_folder, self.source)):
            self.source = os.path.join(self.project_folder, self.source)
        if os.path.exists(destination):
            return
        if self.type == 'git':
            git = vendorize.git.Git()
            git.clone(self.source, destination, self.branch)
        elif self.type in ['deb', 'tar', 'zip']:
            if not self.should_vendor:
                return
            self.extract(self.download(), destination)
        else:
            raise click.ClickException('Unknown type: {!r}'.format(self.type))
        self.source = os.path.join(self.project_folder, destination)

    def download(self) -> str:
        if self.is_url():
            cache = os.path.join(self.project_folder, 'parts')
            os.makedirs(cache, exist_ok=True)
            filename = os.path.join(cache, os.path.basename(self.source))
            if not os.path.exists(filename):
                data = urllib.request.urlopen(self.source).read()
                with open(filename, 'wb') as f:
                    f.write(data)
            return filename
        return self.source

    def is_url(self):
        return urllib.parse.urlparse(self.source).scheme != ''

    def extract(self, archive: str, destination: str):
        try:
            with tarfile.open(archive) as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(tar, members=self.filter_members(tar.getmembers()), path=destination)
                               path=destination)
        except tarfile.TarError:
            raise click.ClickException('Cannot extract {!r}'.format(archive))

    def filter_members(self, members: List[tarfile.TarInfo]):
        prefix = os.path.commonprefix([m.name for m in members])
        for m in members:
            if not (m.name.startswith(prefix + '/') or
                    m.isdir() and m.name == prefix):
                prefix = os.path.dirname(prefix)
                break
        for m in members:
            if m.name == prefix:
                continue
            self.strip_prefix(prefix + '/', m)
            # Ensure files are writable
            m.mode = m.mode | 0o200
            yield m
        return members

    def strip_prefix(self, prefix: str, member: tarfile.TarInfo):
        member.name = self.strip_slash(prefix, member.name)
        # Strip hardlinks
        if member.islnk() and not member.issym():
            member.linkname = self.strip_slash(prefix, member.linkname)

    def strip_slash(self, prefix, name):
        # Strip leading /, ./, ../
        if name.startswith(prefix):
            name = name[len(prefix):]
        return re.sub(r'^(\.{0,2}/)*', r'', name)
