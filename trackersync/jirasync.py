#!/usr/bin/python3
# Copyright (C) 2015-18 Dr. Ralf Schlatterbeck Open Source Consulting.
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

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import os
import requests
import json

from optparse           import OptionParser
from rsclib.autosuper   import autosuper
from rsclib.Config_File import Config_File
from rsclib.pycompat    import ustr
from trackersync        import roundup_sync
from trackersync        import tracker_sync
from trackersync        import jira_sync

class Config (Config_File):

    config = 'jira_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config):
        self.__super.__init__ \
            ( path, config
            , JIRA_URL     = 'http://localhost:8080/rest/api/2'
            , JIRA_TIMEOUT = 30
            )
    # end def __init__

# end class Config

class Jira_Issue (jira_sync.Jira_Backend, tracker_sync.Remote_Issue):

    multilevel = True

    def __init__ (self, jira, record):
        self.jira        = jira
        self.session     = jira.session
        self.doc_meta    = {}
        self.attachments = None
        self.__super.__init__ (record)
        # Remove these or we'll get a new ext_attributes on every sync
        del self.record ['lastViewed']
        del self.record ['updated']
    # end def __init__

    def add_message (self, local_msg):
        """ Add the given local_msg to the current jira issue.
            As indicated in base class, local_msg is a dictionary of
            all message properties with current values.
        """
        d  = dict (body = local_msg ['content'])
        u  = self.jira.url + '/issue/' + self.id + '/comment'
        h  = { 'content-type': 'application/json' }
        r  = self.session.post (u, data = json.dumps (d), headers = h)
        j  = r.json ()
        return j ['id']
    # end def add_message

    def update (self, syncer):
        if syncer.verbose:
            print ("Remote-Update: %s %s" % (self.key, self.newvalues))
        for k in self.newvalues:
            v = self.newvalues [k]
            if isinstance (v, (dict, list)):
                raise ValueError ("Update on non-atomic value")
        u = self.jira.url + '/issue/' + self.id
        h = { 'content-type': 'application/json' }
        r = self.session.put \
            (u, headers = h, data = json.dumps (dict (fields = self.newvalues)))
        r.raise_for_status ()
    # end def update

# end def Jira_Issue

class Jira (autosuper):
    """ Interaction with a Jira instance
    """

    def __init__ \
        ( self
        , url
        , username
        , password
        , timeout = 30
        , verbose = False
        , debug = False
        ):
        self.url          = url
        self.verbose      = verbose
        self.debug        = debug
        self.session      = requests.Session ()
        self.session.auth = (username, password)
        if timeout:
            self.session.timeout = timeout
    # end def __init__

    def query (self, jql):
        i = 0
        while True:
            d = dict (jql = jql, startAt = i, maxResults = 1)
            u = self.url + '/' + 'search'
            r = self.session.get (u, params = d)
            j = r.json ()
            if not j ['issues']:
                assert j ['startAt'] == j ['total']
                break
            assert len (j ['issues']) == 1
            ji = j ['issues'][0]
            # Workaround for requests.exceptions.ConnectionError:
            # ('Connection aborted.', ResponseNotReady())
            self.session.close ()
            yield Jira_Issue \
                ( self
                , dict (ji ['fields'], key = ji ['key'], id = ji ['id'])
                )
            i = i + 1
    # end def query

# end class Jira

def main ():
    import sys
    cmd = OptionParser ()
    cmd.add_option \
        ( "-a", "--assignee"
        , help    = "Query for issues with this assignee"
        )
    cmd.add_option \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/trackersync/jira_config.py'
        )
    cmd.add_option \
        ( "-D", "--debug"
        , help    = "Debugging"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_option \
        ( "-j", "--jql"
        , help    = "JQL-Query, overrides assignee option"
        )
    cmd.add_option \
        ( "-n", "--no-action"
        , help    = "Dry-run: Don't update any side of sync"
        , action  = 'store_true'
        , default = False
        , dest    = 'dry_run'
        )
    cmd.add_option \
        ( "-P", "--password"
        , help    = "KPM login password"
        )
    cmd.add_option \
        ( "-r", "--roundup-url"
        , help    = "Roundup URL for XMLRPC"
        )
    cmd.add_option \
        ( "-t", "--timeout"
        , help    = "Timeout for requests to Jira"
        )
    cmd.add_option \
        ( "-u", "--url"
        , help    = "Jira URL"
        )
    cmd.add_option \
        ( "-U", "--username"
        , help    = "KPM login user name"
        )
    cmd.add_option \
        ( "-v", "--verbose"
        , help    = "Verbose reporting"
        , action  = 'store_true'
        , default = False
        )
    opt, arg = cmd.parse_args ()
    config  = Config.config
    cfgpath = Config.path
    if opt.config:
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    url      = opt.url         or cfg.JIRA_URL
    username = opt.username    or cfg.JIRA_USERNAME
    password = opt.password    or cfg.JIRA_PASSWORD
    timeout  = opt.timeout     or cfg.get ('JIRA_TIMEOUT', None)
    rup_url  = opt.roundup_url or cfg.ROUNDUP_URL
    assignee = opt.assignee    or cfg.get ('JIRA_ASSIGNEE', None)
    jql      = opt.jql         or cfg.get ('JIRA_JQL', None)
    jira     = Jira \
        ( url
        , username
        , password
        , timeout = timeout or None
        , verbose = opt.verbose
        , debug   = opt.debug
        )
    q = jql or 'assignee=%s' % assignee
    if rup_url and cfg.get ('JIRA_ATTRIBUTES'):
        trn    = cfg.get ('TRACKER_NAME', 'JIRA')
        syncer = roundup_sync.Syncer (rup_url, trn, cfg.JIRA_ATTRIBUTES, opt)
    if syncer:
        for issue in jira.query (q):
            if opt.debug:
                print (issue)
            syncer.sync (issue.key, issue)
# end def main

if __name__ == '__main__':
    main ()
