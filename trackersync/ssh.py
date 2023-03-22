#!/usr/bin/python3
# Copyright (C) 2019 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ****************************************************************************

from paramiko import SSHClient, AutoAddPolicy
from paramiko.rsakey import RSAKey
from scp import SCPClient
from rsclib.autosuper import autosuper
import os
import sys
import stat

class SSH_Client (autosuper):

    def __init__ \
        (self, host, privkey, remote_dir = '/tmp', local_dir = '/tmp'
        , password = None, port = 22, user = 'root'
        ):
        self.ssh        = SSHClient ()
        self.host       = host
        self.remote_dir = remote_dir
        self.local_dir  = local_dir
        self.key = RSAKey.from_private_key_file (privkey, password = password)
        home = os.environ.get ('HOME', '/root')
        path = os.path.join (home, '.ssh', 'known_hosts_paramiko')
        self.known_hosts = path
        self.ssh.load_host_keys (path)
        self.ssh.set_missing_host_key_policy (AutoAddPolicy ())
        self.ssh.connect \
            ( host
            , pkey          = self.key
            , port          = port
            , username      = user
            , look_for_keys = False
            , allow_agent   = False
            )
        self.sftp = self.ssh.open_sftp ()
        self.sftp.chdir (self.remote_dir)
    # end def __init__

    def get_files (self, * fn):
        for f in fn:
            dest = os.path.join (self.local_dir, os.path.basename (f))
            self.sftp.get (f, dest)
    # end def get_files

    def list_files (self):
        for f in self.sftp.listdir_attr ():
            if stat.S_ISREG (f.st_mode):
                yield (f.filename)
    # end def list_files

    def put_files (self, *fn):
        for f in fn:
            dest = os.path.join (self.remote_dir, os.path.basename (f))
            self.sftp.put (f, dest)
    # end def put_files

    def close (self):
        self.ssh.save_host_keys (self.known_hosts)
        self.ssh.close ()
    # end def close

    def __getattr__ (self, name):
        return getattr (self.sftp, name)
    # end def __getattr__

# end class SSH_Client
