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

from trackersync        import roundup_sync

class Config (Config_File) :

    config = 'kpm_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , KPM_ADDRESS = '21 KPM-TEST'
            )
    # end def __init__

# end class Config

class Problem (roundup_sync.Remote_Issue) :

    def __init__ (self, kpm, record, lang, canceled = False) :
        self.kpm      = kpm
        self.canceled = canceled
        self.lang     = lang
        rec = {}
        for k, v in record.iteritems () :
            if v is not None and v != str ('') :
                v = v.decode ('latin1')
                rec [k.decode ('latin1')] = v
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
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
    # end def document_content

    def document_ids (self) :
        docs = self.get ('Dokumente')
        if not docs :
            return []
        ids  = []
        for doc in docs.split () :
            ids.extend (parse_qs (doc) ['dokTs'])
        return [i.decode ('latin1') for i in ids]
    # end def document_ids

    def __getitem__ (self, name) :
        if name in ('action', 'number') :
            name = getattr (self.lang, name)
        return self.__super.__getitem__ (name)
    # end def __getitem__

    def check_sync_callback (self, syncer, id) :
        """ Check for kpmid is a legacy lifter: Old issues don't have a
            kpm attached and must therefore always sync.
        """
        kpmid = syncer.get (id, '/kpm/id')
        return bool (kpmid)
    # end def check_sync_callback

    def create (self) :
        """ Create new remote issue
        """
        print ("Called remote_issue.create", self.newvalues)
    # end def create

    def update_remote (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        print ("Called update_remote")
    # end def update_remote

# end def Problem

class KPM_Language (autosuper) :
    """ Encapsulate various language features of KPM.
        Note that we keep the currently-configured language -- so in the
        config-file the user can configure the translations according to
        their native language. Currently we handle only german and
        english. In addition to determining the language we translate
        some duplicate header lines in the CSV:
    """

    # Numbering is 1-based from manual, we correct this in code rather than
    # trying to get it right in the following table.
    # These are the attributes with duplicate column names in the CSV
    # export. We fix this by adding a ' [Code]' suffix to the first
    # value (which is a key into some table).
    fix_kpm_attr_german = \
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

    fix_kpm_attr_english = \
        ( ( 7, 'Country')
        , ( 9, 'E-Project')
        , (14, 'Functionality')
        , (16, 'Repeatable')
        , (18, 'Fault frequency')
        , (22, 'Device type')
        , (27, 'device type 2')
        , (32, 'device type 3')
        , (55, 'L-Status')
        , (64, 'Verification status')
        , (76, 'module relevant')
        )

    fields_english = \
        ( 'Action'
        , 'Number'
        , 'Change-TS problem'
        , 'Date'
        , 'Origin'
        , 'Country'
        , 'Country [Code]'
        , 'E-Project'
        , 'E-Project [Code]'
        , 'Short Text'
        , 'Problem Description'
        , 'Analysis/Root Cause'
        , 'Functionality'
        , 'Functionality [Code]'
        , 'Repeatable'
        , 'Repeatable [Code]'
        , 'Fault frequency'
        , 'Fault frequency [Code]'
        , 'Project'
        , 'Veh.-no.'
        , 'Device type'
        , 'Device type [Code]'
        , 'Part-no. (causing)'
        , 'HW (causing)'
        , 'SW (causing)'
        , 'device type 2'
        , 'device type 2 [Code]'
        , 'part-no. 2'
        , 'HW 2'
        , 'SW 2'
        , 'device type 3'
        , 'device type 3 [Code]'
        , 'part-no. 3'
        , 'HW 3'
        , 'SW 3'
        , 'VBV'
        , 'Train'
        , 'Rating'
        , 'Status'
        , 'Engineering status'
        , 'Creator'
        , 'Typist User'
        , 'Coordinator'
        , 'Coordinator user'
        , 'engineering Coordinator'
        , 'engineering coordinator user'
        , 'Responsible Problem Solver'
        , 'Responsible Problem Solver User'
        , 'Implementation date'
        , 'Order type'
        , 'Contract Number'
        , 'Change-TS supplier'
        , 'supplier'
        , 'L-Status'
        , 'L-Status [Code]'
        , 'L-Fault No.'
        , 'L-System-OK'
        , 'L-Intro date'
        , 'supplier response/fixes'
        , 'Supplier info'
        , 'Tester'
        , 'Tester User'
        , 'Verification status'
        , 'Verification status [Code]'
        , 'verification software vers.'
        , 'verification hardware vers.'
        , 'verification'
        , 'Documents'
        , 'Additional Criteria 1'
        , 'Description Additional Criteria 1'
        , 'Additional Criteria 2'
        , 'Description Additional Criteria 2'
        , 'Additional Criteria 3'
        , 'Description Additional Criteria 3'
        , 'module relevant'
        , 'module relevant [Code]'
        , 'Active With'
        , 'Authorised To Close'
        )

    fields_german = \
        ( 'Aktion'
        , 'Nummer'
        , 'Änderungs-TS Problem'
        , 'Datum'
        , 'Quelle'
        , 'Land'
        , 'Land [Code]'
        , 'E-Projekt'
        , 'E-Projekt [Code]'
        , 'Kurztext'
        , 'Problembeschreibung'
        , 'Analyse'
        , 'Funktionalität'
        , 'Funktionalität [Code]'
        , 'Reproduzierbar'
        , 'Reproduzierbar [Code]'
        , 'Fehlerhäufigkeit'
        , 'Fehlerhäufigkeit [Code]'
        , 'Projekt'
        , 'Fzg Nr.'
        , 'Gerätetyp'
        , 'Gerätetyp [Code]'
        , 'Teilnummer (verurs.)'
        , 'Hardwarestand (verurs.)'
        , 'Softwarestand (verurs.)'
        , 'Gerätetyp 2'
        , 'Gerätetyp 2 [Code]'
        , 'Teilnummer 2'
        , 'Hardwarestand 2'
        , 'Softwarestand 2'
        , 'Gerätetyp 3'
        , 'Gerätetyp 3 [Code]'
        , 'Teilnummer 3'
        , 'Hardwarestand 3'
        , 'Softwarestand 3'
        , 'VBV'
        , 'Zug'
        , 'Bewertung'
        , 'Status'
        , 'FB-Status'
        , 'Erfasser'
        , 'Erfasser Benutzer'
        , 'Koordinator'
        , 'Koordinator Benutzer'
        , 'Fachkoordinator'
        , 'Fachkoordinator Benutzer'
        , 'Problemlösungsverantwortlicher'
        , 'Problemlösungsverantwortlicher Benutzer'
        , 'Einsatzdatum'
        , 'Auftragsart'
        , 'Auftragsnummer'
        , 'Änderungs-TS Lieferant'
        , 'Lieferant'
        , 'L-Status'
        , 'L-Status [Code]'
        , 'L-Fehlernummer'
        , 'L-System-IO'
        , 'L-Einsatzdatum'
        , 'Lieferantenaussage'
        , 'Lieferanteninfo'
        , 'Tester'
        , 'Tester Benutzer'
        , 'Verifikation-Status'
        , 'Verifikation-Status [Code]'
        , 'Verifikation-Softwarestand'
        , 'Verifikation-Hardwarestand'
        , 'Verifikation'
        , 'Dokumente'
        , 'Zusatzkriterium 1'
        , 'Bechreibung Zusatzkriterium 1'
        , 'Zusatzkriterium 2'
        , 'Bechreibung Zusatzkriterium 2'
        , 'Zusatzkriterium 3'
        , 'Bechreibung Zusatzkriterium 3'
        , 'Modulrelevant'
        , 'Modulrelevant [Code]'
        , 'Aktiv bei'
        , 'Abschlussrecht'
        )

    fieldnames = dict (english = fields_english, german = fields_german)

    def __init__ (self, delimiter) :
        self.delimiter = delimiter
        self.language  = None
        self.action    = None
        self.number    = None
    # end def __init__

    def fix_kpm_csv (self, f) :
        first = f.next ().split (self.delimiter)
        fix   = self.fix_kpm_attr_german
        lang  = "german"
        if  (  first [self.fix_kpm_attr_english [0][0] - 1]
            == self.fix_kpm_attr_english [0][1]
            ) :
            fix  = self.fix_kpm_attr_english
            lang = "english"
        assert first [fix [0][0] - 1] == fix [0][1]
        self.language = lang
        self.action   = first [0]
        self.number   = first [1]
        for idx, header in fix :
            header = header.encode ('latin1')
            assert first [idx - 1] == first [idx - 2] == header
            first [idx - 2] = first [idx - 2] + ' [Code]'.encode ('latin1')
        yield self.delimiter.join (first)
        for line in f :
            yield (line)
    # end def fix_kpm_csv

# end class KPM_Language

class Export (autosuper) :

    def __init__ (self, kpm, f, canceled = False, debug = False) :
        self.canceled = canceled
        self.debug    = debug
        self.problems = {}
        self.kpm      = kpm
        self.lang     = KPM_Language (delimiter = str (';'))
        if self.debug :
            fo = open ('%s.csv' % self.debug, 'w')
            lines = []
            for line in f :
                lines.append (line)
                fo.write (line)
            fo.close ()
            i = iter (lines)
            c = DictReader \
                (self.lang.fix_kpm_csv (i), delimiter = self.lang.delimiter)
        else :
            c = DictReader \
                (self.lang.fix_kpm_csv (f), delimiter = self.lang.delimiter)
        for record in c :
            if record [self.lang.action] :
                continue
            p = Problem (kpm, record, self.lang, canceled = self.canceled)
            self.problems [p.number] = p
    # end def __init__

    def add (self, problem) :
        if problem.number in self.problems :
            raise ValueError, "Duplicate Problem: %s" % problem.number
        self.problems [problem.number] = problem
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
        syncer.sync_new_local_issues \
            (lambda x: Problem (self.kpm, x, self.lang))
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

    dates = dict \
        (( ('create', 'createdAt')
        ,  ('start',  'startedAt')
        ,  ('finish', 'finishedAt')
        ))
    states_d = ('Auftrag angelegt', 'in Arbeit', 'fertiggestellt', 'Fehler')
    states_e = ('Auftrag angelegt', 'Accepted', 'Completed', 'Fehler')
    types = \
        ( 'Lieferantenimport'
        , 'Lieferantenexport'
        , 'Lieferantenexport (stornierte Auftr\xe4ge)'
        )
    xmlns = 'uri:de.volkswagen.kpm.ajax.xmlns'

    def __init__ (self, kpm, jobid, debug = False, reuse = False) :
        self.kpm    = kpm
        self.jobid  = jobid
        self.debug  = debug
        self.reuse  = reuse
        self.count  = 0
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
                assert key < len (self.states_d)
                if self.states_d [key] != e.get ('text') :
                    if self.states_e [key] != e.get ('text') :
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
        self.count += 1
        # If a download of this job-id exists, continue
        # Useful for debugging.
        if self.reuse :
            try :
                f = open ('JOB-%s-%s' % (self.jobid, self.count), 'r')
                v = f.read ()
                self.parse (v)
                return
            except IOError :
                pass
        f = self.kpm.get ('ticket.info.do', ticketId = self.jobid)
        v = f.read ()
        if self.debug :
            fn = "JOB-%s-%s" % (self.jobid, self.count)
            f  = open (fn, 'w')
            f.write (v)
            f.close ()
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
        xpp = dict (canceled = self.type == 2)
        if self.debug :
            xpp ['debug'] = self.jobid
        f = None
        # If downloaded job exists, return it
        if self.reuse :
            try :
                f = open ('%s.csv' % self.jobid, 'r')
            except IOError :
                pass
        if not f :
            f = self.kpm.get ('ticket.download.do', ticketId = self.jobid)
        xp  = Export (self.kpm, f, ** xpp)
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
        j   = Job (self, v, debug = self.debug)
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
        , default = '/etc/trackersync/kpm_config.py'
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
        ( "-n", "--no-action"
        , help    = "Dry-run: Don't update any side of sync"
        , action  = 'store_true'
        , default = False
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
    url      = opt.roundup_url or cfg.get ('ROUNDUP_URL', None)
    kpm.login  (username = username, password = password)
    if (opt.job) :
        jobs = [Job (kpm, opt.job, debug = opt.debug, reuse = True)]
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
            , dry_run = opt.no_action
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
