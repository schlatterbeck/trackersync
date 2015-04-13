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
try :
    import urllib2
except ImportError :
    import urllib as urllib2
try:
    from http.cookiejar import LWPCookieJar
except ImportError :
    from cookielib      import LWPCookieJar
    from urlparse       import parse_qs
try :
    from urllib.parse   import urlencode, parse_qs
except ImportError :
    from urllib         import urlencode
from time               import sleep
from optparse           import OptionParser
from datetime           import datetime
from csv                import DictReader
from xml.etree          import ElementTree
from rsclib.autosuper   import autosuper
from rsclib.Config_File import Config_File

from tracker_sync       import roundup_sync

class Config (Config_File) :

    config = 'kpm_config'
    path   = '/etc/tracker_sync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , KPM_ADDRESS = '21 KPM-TEST'
            )
    # end def __init__

# end class Config

class Problem (roundup_sync.Remote_Issue) :

    def __init__ (self, kpm, record, canceled = False) :
        self.kpm      = kpm
        self.canceled = canceled
        rec = {}
        for k, v in record.iteritems () :
            if v is not None and v != str ('') :
                v = v.decode ('latin1')
                rec [k.decode ('latin1')] = v
        attributes = {}
        if self.canceled :
            attributes ['Status'] = True
        self.__super.__init__ (rec, attributes)
    # end def __init__

    def document_content (self, docid) :
        kpm = self.kpm
        url = '/'.join ((kpm.base_url, 'problem.base.dokument.download.do'))
        par = dict (actionCommand='downloadDokumentAsAttachment', dokTs = docid)
        url = '?'.join ((url, urlencode (par)))
        rq  = urllib2.Request (url, None, kpm.headers)
        f   = kpm.opener.open (rq, timeout = kpm.timeout)
        return f.read ()
    # end def document_contents

    def document_ids (self) :
        docs = self.get ('Dokumente')
        if not docs :
            return []
        ids  = []
        for doc in docs.split () :
            ids.extend (parse_qs (doc) ['dokTs'])
        return [i.decode ('latin1') for i in ids]
    # end def document_ids

# end def Problem

# Numbering is 1-based from manual, we correct this in code rather than
# trying to get it right in the following table.
# These are the attributes with duplicate column names in the CSV
# export. We fix this by adding a ' [Code]' suffix to the first
# value (which is a key into some table).
fix_kpm_attr = \
    ( ( 7, 'Land')
    , ( 9, 'E-Projekt')
    , (14, 'Funktionalit\xe4t')
    , (16, 'Reproduzierbar')
    , (18, 'Fehlerh\xe4ufigkeit')
    , (22, 'Ger\xe4tetyp')
    , (27, 'Ger\xe4tetyp 2')
    , (32, 'Ger\xe4tetyp 3')
    , (55, 'L-Status')
    , (64, 'Verifikation-Status')
    , (76, 'Modulrelevant')
    )

def fix_kpm_csv (delimiter, f) :
    first = f.next ().split (delimiter)
    for idx, header in fix_kpm_attr :
        header = header.encode ('latin1')
        assert first [idx - 1] == first [idx - 2] == header
        first [idx - 2] = first [idx - 2] + ' [Code]'.encode ('latin1')
    yield delimiter.join (first)
    for line in f :
        yield (line)
# end def fix_kpm_csv

class Export (autosuper) :

    def __init__ (self, kpm, f, canceled = False) :
        self.canceled = canceled
        self.problems = {}
        delimiter = str (';')
        c = DictReader (fix_kpm_csv (delimiter, f), delimiter = delimiter)
        for record in c :
            if record ['Aktion'] :
                continue
            p = Problem (kpm, record, canceled = self.canceled)
            self.problems [p.Nummer] = p
    # end def __init__

    def add (self, problem) :
        if problem.Nummer in self.problems :
            raise ValueError, "Duplicate Problem: %s" % problem.Nummer
        self.problems [problem.Nummer] = problem
    # end def add

    def delete (self, problem_id) :
        del self.problems [problem_id]
    # end def delete

    def get (self, problem_id, default = None) :
        return self.problems.get (problem_id, default)
    # end def get

    def sync (self, syncer) :
        for p_id, p in self.problems.iteritems () :
            syncer.sync (p_id, p)
    # end def sync

    def __repr__ (self) :
        r = []
        for p in self.problems.itervalues () :
            r.append (str ("PROBLEM"))
            r.append (repr (p))
        return str ('\n').join (r)
    # end def __repr__

# end class Export

class Job (autosuper) :
    """ Job handling
    """

    dates  = dict \
        (( ('create', 'createdAt')
        ,  ('start',  'startedAt')
        ,  ('finish', 'finishedAt')
        ))
    states = ('Auftrag angelegt', 'in Arbeit', 'fertiggestellt', 'Fehler')
    types  = ( 'Lieferantenimport'
             , 'Lieferantenexport'
             , 'Lieferantenexport (stornierte Auftr\xe4ge)'
             )
    xmlns  = 'uri:de.volkswagen.kpm.ajax.xmlns'

    def __init__ (self, kpm, jobid) :
        self.kpm    = kpm
        self.jobid  = jobid
        self.create = None
        self.start  = None
        self.finish = None
        self.error  = None
        self.state  = None
        self.type   = None
        self.msg    = None
        self.att    = None
    # end def __init__

    @property
    def valid (self) :
        return not self.error
    # end def valid

    def parse (self, text) :
        tree = ElementTree.fromstring (text)
        assert tree.tag == self.tag ('ajaxResponse')
        ji = tree [0]
        assert ji.tag == self.tag ('jobInfo')
        assert ji.get ('id') == self.jobid
        self.error = ji.get ('error')
        if self.error :
            return
        fmt = '%Y-%m-%d %H:%M:%S.%f'
        for a, s in self.dates.iteritems () :
            x = ji.get (s)
            if x :
                setattr (self, a, datetime.strptime (x, fmt))
        for e in ji :
            if e.tag == self.tag ('state') :
                key = int (e.get ('key'), 10)
                assert key < len (self.states)
                if self.states [key] != e.get ('text') :
                    print (self.states [key], e.get ('text'))
                #assert self.states [key] == e.get ('text')
                self.state = key
            if e.tag == self.tag ('type') :
                key = int (e.get ('key'), 10)
                assert key < len (self.types)
                assert self.types [key] == e.get ('text')
                self.type = key
            if e.tag == self.tag ('result') :
                self.msg = e.get ('message')
                self.att = e.get ('hasAttachment') == 'true'
    # end def parse

    def query (self) :
        f = self.kpm.get ('ticket.info.do', ticketId = self.jobid)
        v = f.read ()
        self.parse (v)
    # end def query

    # Job deletion not yet supported by application
    # According to Dr. Dirk Licht (Author "Endbenutzerhandbuch") 2015-03-11
    #def delete (self) :
    #    f = self.kpm.get ('ticket.delete.do', ticketId = self.jobid)
    #    return f.read ()
    ## end def delete

    def download (self) :
        if self.state != 2 or self.type == 0 :
            return None
        f  = self.kpm.get ('ticket.download.do', ticketId = self.jobid)
        xp = Export (self.kpm, f, canceled = self.type == 2)
        return xp
    # end def download

    def tag (self, tag) :
        return '{%s}%s' % (self.xmlns, tag)
    # end def tag

    def __repr__ (self) :
        r = ['Job: %s' % self.jobid]
        if self.error :
            r.append ('Invalid: %r' % self.error)
        else :
            for dk in self.dates :
                d = getattr (self, dk)
                if d :
                    r.append ('%6s: %s' % (dk, d))
        if self.state :
            r.append ('State: %s (%s)' % (self.state, self.states [self.state]))
        if self.msg :
            r.append ('Message: %r' % self.msg)
        if self.att :
            r.append ('We have a job result')
        return '\n'.join (r)
    # end def __repr__
    __str__ = __repr__

# end class Job

class KPM (autosuper) :
    """ Interactions with the KPM web interface aka
        "Lieferantenschnittstelle".
    """

    def __init__ \
        ( self
        , site    = 'https://sso.volkswagen.de'
        , url     = 'kpmweb'
        , timeout = None
        , verbose = False
        , debug   = False
        ) :
        self.site     = site
        self.verbose  = verbose
        self.debug    = debug
        self.base_url = '/'.join ((site, url))
        self.timeout  = timeout
        self.cookies  = LWPCookieJar ()
        self.headers  = {}
        self.jobs     = []
        self.opener   = urllib2.build_opener \
            (urllib2.HTTPCookieProcessor (self.cookies))
    # end def __init__

    def login (self, username, password) :
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm ()
        password_mgr.add_password (None, self.site, username, password)
        handler = urllib2.HTTPBasicAuthHandler (password_mgr)
        self.opener.add_handler (handler)
        url = '/'.join ((self.base_url, 'b2bLogin.do'))
        rq  = urllib2.Request (url, None, self.headers)
        f   = self.opener.open (rq, timeout = self.timeout)
        v   = f.read ()
        # Does NOT work with only the cookie, still need basic auth
        # So we don't rebuild the opener without BasicAuth.
    # end def login

    def get (self, url, ** params) :
        """ Get request """
        url = '/'.join ((self.base_url, url))
        url = '?'.join ((url, urlencode (params)))
        rq  = urllib2.Request (url, None, self.headers)
        f   = self.opener.open (rq, timeout = self.timeout)
        return f
    # end def get

    def search (self, **params) :
        p   = dict (params, columnModel = "V4".encode ('latin1'))
        f = self.get ('search.ee.exportJob.do', **p)
        v   = f.read ()
        j   = Job (self, v)
        if self.debug :
            print ("Job-ID: %s" % v)
        self.jobs.append (j)
        return j
    # end def search

# end class KPM

def main () :
    import sys
    cmd = OptionParser ()
    cmd.add_option \
        ( "-a", "--address"
        , help    = "KPM-Address of Supplier"
        )
    cmd.add_option \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/tracker_sync/kpm_config.py'
        )
    cmd.add_option \
        ( "-D", "--debug"
        , help    = "Debugging"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_option \
        ( "-j", "--job"
        , help    = "KPM job identifier (mainly used for debugging)"
        )
    cmd.add_option \
        ( "-r", "--roundup-url"
        , help    = "Roundup URL for XMLRPC"
        )
    cmd.add_option \
        ( "-P", "--password"
        , help    = "KPM login password"
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
    kpm = KPM  (verbose = opt.verbose, debug = opt.debug)
    username = opt.username    or cfg.KPM_USERNAME
    password = opt.password    or cfg.KPM_PASSWORD
    address  = opt.address     or cfg.KPM_ADDRESS
    url      = opt.roundup_url or cfg.ROUNDUP_URL
    kpm.login  (username = username, password = password)
    if (opt.job) :
        jobs = [Job (kpm, opt.job)]
    else :
        # get active and canceled issues
        jobs = [kpm.search (address = address)]
        jobs.append (kpm.search (address = address, canceled = 'true'))
    syncer = None
    if url and cfg.get ('KPM_ATTRIBUTES') :
        syncer = roundup_sync.Syncer \
            (url, 'KPM', cfg.KPM_ATTRIBUTES
            , verbose = opt.verbose
            , debug   = opt.debug
            )
    for j in jobs :
        j.query ()
    old_xp = None
    for j in jobs :
        while j.state < 2 :
            sleep (10)
            j.query ()
        xp = j.download ()
        # Remove duplicates, seems KPM sometimes returns a problem in
        # both, the normal list and the cancelled problems. In that case
        # we don't process the cancelled one (as it contains less info)
        # Note that the code below also works if we have more than two
        # jobs.
        if old_xp :
            for p in xp.problems.keys () :
                if old_xp.get (p) :
                    xp.delete (p)
                else :
                    old_xp.add (xp.problems [p])
        else :
            old_xp = xp
        if opt.debug :
            f = open (j.jobid, 'w')
            f.write (repr (xp))
            f.close ()
        if syncer :
            xp.sync (syncer)
# end def main

if __name__ == '__main__' :
    main ()
