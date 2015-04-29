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
import json

from optparse           import OptionParser
from datetime           import datetime, timedelta
from rsclib.autosuper   import autosuper
from rsclib.Config_File import Config_File
from rsclib.pycompat    import ustr
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

def jira_utctime (jiratime) :
    """ Time with numeric timestamp converted to UTC.
        Note that roundup strips trailing decimal places to 0.
    >>> jira_utctime ('2014-10-28T13:29:22.585+0100')
    '2014-10-28.12:29:22.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:22.385+0100')
    '2014-10-28.12:29:22.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.385+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.585+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59.0+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2014-10-28T13:29:59+0100')
    '2014-10-28.12:29:59.000+0000'
    >>> jira_utctime ('2015-04-21T08:27:46+0200')
    '2015-04-21.06:27:46.000+0000'
    """
    fmt = fmts = "%Y-%m-%dT%H:%M:%S.%f"
    fmtnos     = "%Y-%m-%dT%H:%M:%S"
    d, tz = jiratime.split ('+')
    tz = int (tz)
    h  = tz / 100
    m  = tz % 100
    if '.' not in d :
        fmt = fmtnos
    d  = datetime.strptime (d, fmt)
    d  = d + timedelta (hours = -h, minutes = -m)
    return ustr (d.strftime ("%Y-%m-%d.%H:%M:%S") + '.000+0000')
# end def jira_utctime

class Jira_Issue (roundup_sync.Remote_Issue) :

    multilevel = True

    def __init__ (self, jira, record) :
        self.jira     = jira
        self.doc_meta = {}
        self.__super.__init__ (record)
        # Remove these or we'll get a new ext_attributes on every sync
        del self.record ['lastViewed']
        del self.record ['updated']
    # end def __init__

    def attach_file (self, name, type, content) :
        u = self.jira.url + '/issue/' + self.id + '/attachments'
        h = {'X-Atlassian-Token': 'nocheck'}
        f = dict (file = (name, content, type))
        r = self.jira.session.post (u, files = f, headers = h)
        j = r.json ()
        assert len (j) == 1
        return self._docid (j [0])
    # end def attach_file

    def attachment_iter (self) :
        u = self.jira.url + '/issue/' + self.id + '?fields=attachment'
        r = self.jira.session.get (u)
        j = r.json ()
        for a in j ['fields']['attachment'] :
            yield a
    # end def attachment_iter

    def _docid (self, attachment_meta) :
        a = attachment_meta
        return ':'.join ((a ['filename'], a ['id']))
    # end def _docid

    def document_attributes (self, id) :
        return dict (type = self.doc_meta [id]['mimeType'])
    # end def document_attributes

    def document_content (self, id) :
        r = self.jira.session.get (self.doc_meta [id]['content'])
        return r.content
    # end def document_content

    def document_ids (self) :
        ids = []
        if self.doc_meta :
            for a in doc_meta.itervalues () :
                ids.append (self._docid (a))
        else :
            for a in self.attachment_iter () :
                ids.append (self._docid (a))
                self.doc_meta [self._docid (a)] = a
        return ids
    # end def document_ids

    def messages (self) :
        u = self.jira.url + '/issue/' + self.id + '/comment'
        r = self.jira.session.get (u)
        j = r.json ()
        if not j ['comments'] :
            assert j ['startAt'] == j ['total'] == 0
        for c in j ['comments'] :
            yield dict \
                ( content = c ['body']
                , date    = jira_utctime (c ['updated'])
                )
    # end def messages

    def update_remote (self, syncer) :
        if syncer.verbose :
            print ("Remote-Update: %s %s" % (self.key, self.newvalues))
        for k, v in self.newvalues.iteritems () :
            if isinstance (v, (dict, list)) :
                raise ValueError ("Update on non-atomic value")
        u = self.jira.url + '/issue/' + self.id
        h = { 'content-type' : 'application/json' }
        r = self.jira.session.put \
            (u, headers = h, data = json.dumps (dict (fields = self.newvalues)))
        r.raise_for_status ()
    # end def update_remote

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
            j = r.json ()
            if not j ['issues'] :
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
