#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301 USA
# ****************************************************************************

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import

import os
import requests

from optparse           import OptionParser
from rsclib.autosuper   import autosuper
from rsclib.Config_File import Config_File
from trackersync        import roundup_sync

class Config (Config_File) :

    config = 'jira_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , JIRA_URL     = 'http://localhost:8080/rest/api/2'
            , JIRA_TIMEOUT = 30
            )
    # end def __init__

# end class Config

class Jira_Issue (roundup_sync.Remote_Issue) :

    multilevel = True

    def __init__ (self, jira, record) :
        self.jira     = jira
        self.__super.__init__ (record)
    # end def __init__

# end def Jira_Issue

class Jira (autosuper) :
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
        ) :
        self.url          = url
        self.verbose      = verbose
        self.debug        = debug
        self.session      = requests.Session ()
        self.session.auth = (username, password)
        if timeout :
            self.session.timeout = timeout
    # end def __init__

    def query (self, jql) :
        i = 0
        while True :
            d = dict (jql = jql, startAt = i, maxResults = 1)
            u = self.url + '/' + 'search'
            r = self.session.get (u, params = d)
            j = r.json
            if not j ['issues'] :
                assert j ['startAt'] == j ['total']
                break
            assert len (j ['issues']) == 1
            ji = j ['issues'][0]
            yield Jira_Issue \
                ( self
                , dict (ji ['fields'], key = ji ['key'], id = ji ['id'])
                )
            i = i + 1
    # end def query

# end class Jira

def main () :
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
    if opt.config :
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
    if rup_url and cfg.get ('JIRA_ATTRIBUTES') :
        syncer = roundup_sync.Syncer \
            ( rup_url, cfg.get ('TRACKER_NAME', 'JIRA'), cfg.JIRA_ATTRIBUTES
            , verbose = opt.verbose
            , debug   = opt.debug
            )
    if syncer :
        for issue in jira.query (q) :
            if opt.debug :
                print (issue)
            syncer.sync (issue.key, issue)
# end def main

if __name__ == '__main__' :
    main ()
