#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# ****************************************************************************

try :
    import urllib2
except ImportError :
    import urllib as urllib2
try:
    from http.cookiejar import LWPCookieJar
except ImportError :
    from cookielib      import LWPCookieJar
try :
    from urllib.parse   import urlencode
except ImportError :
    from urllib         import urlencode
from optparse           import OptionParser
from datetime           import datetime
from csv                import DictReader
from xml.etree          import ElementTree
from rsclib.autosuper   import autosuper

class Problem (autosuper) :

    def __init__ (self, record) :
        self.record = {}
        for k, v in record.iteritems () :
            if v is not None :
                v = v.decode ('latin1')
            self.record [k.decode ('latin1')] = v
        print unicode (self)
    # end def __init__

    def __getattr__ (self, name) :
        try :
            return self.record [name]
        except KeyError as exc :
            raise AttributeError (exc)
    # end def __getattr__

    def __unicode__ (self) :
        r = []
        for k, v in self.record.iteritems () :
            #if v is None :
            #    continue
            r.append ("%(k)s: %(v)s" % locals ())
        return '\n'.join (r)
    # end def __unicode__
    __str__ = __unicode__

# end def Problem

class Export (autosuper) :

    def __init__ (self, f) :
        self.problems = []
        c = DictReader (f, delimiter = ';')
        for record in c :
            self.problems.append (Problem (record))
    # end def __init__

# end class Export

class Job (autosuper) :
    """ Job handling
    """

    dates  = dict \
        (( ('create', 'createdAt')
        ,  ('start', 'startedAt')
        ,  ('finish', 'finishedAt')
        ))
    states = ('Auftrag angelegt', 'In Arbeit', 'fertiggestellt', 'Fehler')
    types  = ( 'Lieferantenimport'
             , 'Lieferantenexport'
             , 'Lieferantenexport (stornierte Aufträge)'
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
        print "Parsing:", text
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

    # FIXME: Is this possible/necessary?
    #def delete (self) :
    #    f = self.kpm.get ('ticket.delete.do', ticketId = self.jobid)
    #    return f.read ()
    ## end def delete

    def download (self) :
        if self.state != 2 :
            return None
        f  = self.kpm.get ('ticket.download.do', ticketId = self.jobid)
        xp = Export (f)
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
        ) :
        self.site     = site
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
        # FIXME:Don't send username/pw with every request; rebuild opener
        print (self.cookies)
        #self.opener   = urllib2.build_opener \
        #    (urllib2.HTTPCookieProcessor (self.cookies))
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
        p   = dict (params, columnModel = "V4")
        f = self.get ('search.ee.exportJob.do', **p)
        v   = f.read ()
        self.jobs.append (Job (self, v))
    # end def search

# end class KPM

def main () :
    import sys
    cmd = OptionParser ()
    cmd.add_option \
        ( "-a", "--address"
        , help    = "KPM-Address of Supplier"
        , default = '21 KPM-TEST'
        )
    cmd.add_option \
        ( "-p", "--password"
        , help = "KPM login password"
        )
    cmd.add_option \
        ( "-j", "--job"
        , help = "KPM job status"
        )
    cmd.add_option \
        ( "-u", "--username"
        , help = "KPM login user name"
        )
    opt, arg = cmd.parse_args ()
    kpm = KPM  ()
    kpm.login  (username = opt.username, password = opt.password)
    if (opt.job) :
        j = Job (kpm, opt.job)
        j.query ()
        print (j)
        print (repr (j.download ()))
    else :
        kpm.search (address = opt.address)
# end def main

if __name__ == '__main__' :
    main ()
