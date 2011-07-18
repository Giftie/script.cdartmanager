#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009 Clóvis Fabrício Costa

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Python smbclient wrapper.

This is a wrapper that works by running the "smbclient" subprocess and providing
an API similar to the one provided by python `os` module.

It is an ugly hack, but it is here for anyone that finds it useful.

The programmer before me was using a "bash" file with lots of smbclient calls,
so I think my solution is at least better.

Usage example:

>>> smb = smbclient.SambaClient(server="MYSERVER", share="MYSHARE",
                                username='foo', password='bar', domain='baz')
>>> print smb.listdir("/")
[u'file1.txt', u'file2.txt']
>>> f = smb.open('/file1.txt')
>>> data = f.read()
>>> f.close()
>>> smb.rename(u'/file1.txt', u'/file1.old')
"""


import subprocess
import datetime
import time
import re
import os
import collections
import weakref
import tempfile
import locale

try:
    any
except NameError:
    # python version older than 2.5
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

try:
    datetime_strptime = datetime.datetime.strptime
except AttributeError:
    # python version older than 2.5
    def datetime_strptime(date, format):
        return datetime.datetime(*(time.strptime(date, format)[:6]))

_volume_re = re.compile(r"""
Volume:\s        # label
\|([^|]*)\|\s     # the volume name
serial\snumber\s # another label
0x([a-f0-9]+)    # hex serial number
$                # end of line
""", re.VERBOSE)

_smb_header_re = re.compile(r"""
Domain=\[([^]]+)\]\s
OS=\[([^]]+)\]\s
Server=\[([^]]+)\]
$
""", re.VERBOSE)


_file_re = re.compile(r"""
\s{2}               # file lines start with 2 spaces
(.*?)\s+            # capture filename non-greedy, eating remaining spaces
([ADHSR]*)          # capture file mode
\s+                 # after the mode you can have any number of spaces
(\d+)               # file size
\s+                 # spaces after file size
(                   # begin date capturing
    \w{3}               # abbrev weekday
    \s                  # space
    \w{3}               # abbrev month
    \s{1,2}             # one or two spaces before the day
    \d{1,2}             # day
    \s                  # a space before the time
    \d{2}:\d{2}:\d{2}   # time
    \s                  # space
    \d{4}               # year
)                   # end date capturing
$                   # end of string""", re.VERBOSE)

class SambaClientError(OSError): pass

class SambaClient(object):
    def __init__(self, server, share, username=None, password=None,
             domain=None, resolve_order=None, port=None, ip=None,
             terminal_code=None, buffer_size=None, debug_level=None,
             config_file=None, logdir=None, netbios_name=None, kerberos=False):
        self._unlink = os.unlink # keep a ref to unlink for future use
        self.path = '//%s/%s' % (server, share)
        smbclient_cmd = ['smbclient', self.path]
        if username is None:
            kerberos = True
        self._kerberos = kerberos
        if kerberos:
            smbclient_cmd.append('-k')
        if resolve_order:
            smbclient_cmd.extend(['-R', ' '.join(resolve_order)])
        if port:
            smbclient_cmd.extend(['-p', str(port)])
        if ip:
            smbclient_cmd.extend(['-I', ip])
        # -E: use stderr
        # -L: look
        if terminal_code:
            smbclient_cmd.extend(['-t', terminal_code])
        if buffer_size:
            smbclient_cmd.extend(['-b', str(buffer_size)])
        if debug_level:
            smbclient_cmd.extend(['-d', str(debug_level)])
        if config_file:
            smbclient_cmd.extend(['-s', config_file])
        if logdir:
            smbclient_cmd.extend(['-l', logdir])
        if not kerberos:
            self.auth = {'username': username}
            if domain:
                self.auth['domain'] = domain
            if password:
                self.auth['password'] = password
            else:
                smbclient_cmd.append('-N')
            fd, self.auth_filename = tempfile.mkstemp(prefix="smb.auth.")
            auth_file = os.fdopen(fd, 'w+b')
            auth_file.write('\n'.join('%s=%s' % (k, v)
                for k, v in self.auth.iteritems()))
            auth_file.close()
            smbclient_cmd.extend(['-A', self.auth_filename])
        if netbios_name:
            smbclient_cmd.extend(['-n', netbios_name])
        self._smbclient_cmd = smbclient_cmd
        self._open_files = weakref.WeakKeyDictionary()

    def _raw_runcmd(self, command):
        # run-a-new-smbclient-process-each-time implementation
        # TODO: Launch and keep one smbclient running
        cmd = self._smbclient_cmd + ['-c', command.encode('utf8')]
        p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        result = p.communicate()[0].strip()
        if p.returncode != 0:
            raise SambaClientError('Error executing %r: %r' % (command, result))
        return result


    def _runcmd(self, command, *args):
        fullcmdlist = [command]
        fullcmdlist.extend(u'"%s"' % arg for arg in args)
        fullcmd = u' '.join(fullcmdlist)
        return self._raw_runcmd(fullcmd)

    def _runcmd_error_on_data(self, cmd, *args):
        """raises SambaClientError if cmd returns any data"""
        data = self._runcmd(cmd, *args).strip()
        if data and not _smb_header_re.match(data):
            raise SambaClientError("Error on %r: %r" % (cmd, data))
        return data

    def _acl(self, path, add=None, modify=None, delete=None, define=None):
        """Reads and Writes ACLs from the server.
        TODO: Some data structure since those nested dicts are awful"""
        path = path.replace('/', '\\')
        cmd = ['smbcacls', self.path, path]
        if add:
            cmd.extend(('-a', add))
        if modify:
            cmd.extend(('-M', modify))
        if delete:
            cmd.extend(('-D', delete))
        if define:
            cmd.extend(('-S', define))
        if self._kerberos:
            cmd.append('-k')
        else:
            cmd.extend(('-U', r'%(domain)s\%(username)s%%%(password)s' % self.auth))
        p = subprocess.Popen(cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        data = p.communicate()[0].strip()
        if p.returncode != 0:
            raise SambaClientError(
                'Error dealing with access control lists: %r' % data)
        result = collections.defaultdict(dict)
        for line in data.splitlines():
            k, sep, val = line.partition(':')
            if sep:
                if k == 'ACL':
                    user, sep, acl = val.partition(':')
                    acl_type, acl_flags, acl_mode = acl.split('/')
                    if acl_flags.startswith('0x'):
                        acl_flags = int(acl_flags, 16)
                    elif acl_flags.isdigit():
                        acl_flags = int(acl_flags)
                    else:
                        acl_flags = acl_flags.split('|')
                    result[k][user] = (acl_type, acl_flags, acl_mode)
                else:
                    if val.startswith('0x'):
                        val = int(val, 16)
                    elif val.isdigit():
                        val = int(val)
                    result[k] = val
        return result

    def lsdir(self, path):
        """
        Lists a directory
        returns a list of tuples in the format:
        [(filename, modes, size, date), ...]
        """
        path = os.path.join(path, u'*')
        return self.glob(path)

    def glob(self, path):
        """
        Lists a glob (example: "/files/somefile.*")
        returns a list of tuples in the format:
        [(filename, modes, size, date), ...]
        """
        files = self._runcmd(u'ls', path).splitlines()
        for filedata in files:
            m = _file_re.match(filedata)
            if m:
                name, modes, size, date = m.groups()
                if name == '.' or name == '..':
                    continue
                name = name.decode('utf-8')
                size = int(size)
                # Resets locale to "C" to parse english date properly
                # (non thread-safe code)
                loc = locale.getlocale(locale.LC_TIME)
                locale.setlocale(locale.LC_TIME, 'C')
                date = datetime_strptime(date, '%a %b %d %H:%M:%S %Y')
                locale.setlocale(locale.LC_TIME, loc)
                yield (name, modes, size, date)

    def listdir(self, path):
        """Emulates os.listdir()"""
        result = [f[0] for f in self.lsdir(path)]
        if not result: # can mean both that the dir is empty or not found
            # disambiguation: verifies if the path doesn't exist. Let the error
            # raised by _getfile propagate in that case.
            self._getfile(path)
        return result

    def netsend(self, destination, message):
        """Sends a message, using netsend"""
        cmd = self._smbclient_cmd + ['-M', destination]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
        result = p.communicate(message)[0].strip()
        if p.returncode != 0:
            raise SambaClientError(
                'Error sending message to %r: %r' % (destination, result))
        return result

    def _getfile(self, path):
        try:
            f = self.glob(path).next()
        except StopIteration:
            raise SambaClientError('Path not found: %r' % path)
        return f

    def info(self, path):
        """Fetches information about a file"""
        path = path.replace('/', '\\')
        data = self._runcmd(u'allinfo', path)
        if data.startswith('ERRSRV'):
            raise SambaClientError(
                'Error retrieving info for %r: %r' % (path, data.strip()))
        result = {}
        for info in data.splitlines():
            k, sep, v = info.partition(':')
            if sep:
                result[k.strip()] = v.strip()
        return result

    def diskinfo(self):
        """Fetches information about a volume"""
        data = self._runcmd('volume')
        for line in data.splitlines():
            m = _volume_re.match(line)
            if m:
                name, serial = m.groups()
                return name, int(serial, 16)
        else:
            raise SambaClientError(
                'Error retrieving disk information: %r' % data)

    def volume(self):
        """Fetches the volume name"""
        return self.diskinfo()[0]

    def serial(self):
        """Fetches the volume serial"""
        return self.diskinfo()[1]

    def isdir(self, path):
        """Returns True if path is a directory/folder"""
        return 'D' in self._getfile(path)[1]

    def isfile(self, path):
        """Returns True if path is a regular file"""
        return not self.isdir(path)

    def exists(self, path):
        """Returns True if path exists in the remote host"""
        try:
            self._getfile(path)
        except SambaClientError:
            return False
        else:
            return True

    def mkdir(self, path):
        """Creates a new folder remotely"""
        path = path.replace('/', '\\')
        self._runcmd_error_on_data(u'mkdir', path)

    def rmdir(self, path):
        """Removes a remote empty folder"""
        path = path.replace('/', '\\')
        self._runcmd_error_on_data(u'rmdir', path)

    def unlink(self, path):
        """Removes/deletes/unlinks a file"""
        path = path.replace('/', '\\')
        self._runcmd_error_on_data(u'del', path)
    remove = unlink

    def chmod(self, path, *modes):
        """Set/reset file modes
        Tested with: AHS

        smbc.chmod('/file.txt', '+H')
        """
        path = path.replace('/', '\\')
        plus_modes = []
        minus_modes = []
        for mode in modes:
            if mode.startswith(u'-'):
                minus_modes.append(mode.lstrip(u'-'))
            else:
                plus_modes.append(mode.lstrip(u'+'))
        modes = []
        if plus_modes:
            modes.append(u'+%s' % u''.join(plus_modes))
        if minus_modes:
            modes.append(u'-%s' % u''.join(minus_modes))
        self._runcmd_error_on_data(u'setmode', u''.join(modes))

    def rename(self, old_name, new_name):
        old_name = old_name.replace('/', '\\')
        new_name = new_name.replace('/', '\\')
        self._runcmd_error_on_data(u'rename', old_name, new_name)

    def download(self, remote_path, local_path):
        remote_path = remote_path.replace('/', '\\')
        result = self._runcmd('get', remote_path, local_path)

    def upload(self, local_path, remote_path):
        remote_path = remote_path.replace('/', '\\')
        result = self._runcmd('put', local_path, remote_path)

    def upload_update(self, local_path, remote_path):
        remote_path = remote_path.replace('/', '\\')
        result = self._runcmd('reput', local_path, remote_path)

    def open(self, path, mode='r'):
        """
        Opens the file indicated by path and returns it as a file-like
        object
        """
        f = _SambaFile(self, path, mode)
        self._open_files[f] = (path, mode)
        return f

    # def du
    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __repr__(self):
        return '<SambaClient(%r@%r)>' % (
            '%(domain)s/%(username)s' % self.auth, self.path)

    def close(self):
        for f in self._open_files.keys():
            f.close()
        if not self._kerberos:
            self._unlink(self.auth_filename)

class _SambaFile(object):
    """
    A samba client remote file
    """
    def __init__(self, connection, remote_name, mode='r'):
        self.name = remote_name
        (fd, self._tmp_name) = tempfile.mkstemp(suffix='.smb', text=False)
        os.close(fd)
        self._mode = mode
        self._conn = weakref.ref(connection)
        self._os_unlink = os.unlink # keep a ref to unlink for future use
        if 'w' in mode: # w deletes file
            if connection.exists(remote_name):
                connection.unlink(remote_name)
        else:
            connection.download(remote_name, self._tmp_name)
        self._file = open(self._tmp_name, mode)
        self.open = True

    def _flush(self):
        if self.open and any(x in self._mode for x in 'wa+'):
            con = self._conn()
            if con is not None:
                if '+' in self._mode:
                    con.upload(self._tmp_name, self.name)
                else:
                    con.upload_update(self._tmp_name, self.name)

    def flush(self):
        self._file.flush()
        self._flush()

    def close(self):
        self._file.close()
        self._flush()
        self.open = False
        self._unlink()

    def _unlink(self):
        try:
            self._os_unlink(self._tmp_name)
        except OSError:
            pass

    def __getattr__(self, name):
        # Attribute lookups are delegated to the underlying file
        # methods are cached to avoid extra lookup
        attr = getattr(self._file, name)
        if callable(attr):
            setattr(self, name, attr)
        return attr

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def __del__(self):
        self.close()

