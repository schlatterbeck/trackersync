#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2015-18 Dr. Ralf Schlatterbeck Open Source Consulting.
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
import sys
import requests
import csv
import xmlrpclib
import ssl
try :
    from urllib.parse   import urlencode, parse_qs
except ImportError :
    from urllib         import urlencode
    from urlparse       import parse_qs
from time               import sleep
from cStringIO          import StringIO
from argparse           import ArgumentParser
from datetime           import datetime
from csv                import DictReader
from xml.etree          import ElementTree
from traceback          import print_exc
from rsclib.autosuper   import autosuper
from rsclib.execute     import Lock_Mixin, Log
from rsclib.Config_File import Config_File
from rsclib.pycompat    import string_types

from trackersync        import tracker_sync
from trackersync        import roundup_sync
from trackersync        import jira_sync

if sys.version.startswith ('2.') :

    class UTF8Recoder:

        def __init__ (self, f) :
            self.f = f
        # end def __init__

        def __iter__ (self):
            for l in self.f :
                yield l.encode ('utf-8')
        # end def __iter__

    # end class UTF8Recoder

    class UnicodeDictReader (object) :

        def __init__ (self, f, ** kw) :
            f = UTF8Recoder (f)
            self.reader = csv.DictReader (f, ** kw)
        # end def __init__

        def decode (self, value) :
            if value is None :
                return None
            return value.decode ('utf-8')
        # end def decode

        def __iter__ (self) :
            ''' Reads and returns the next line as a Unicode string.
            '''
            for row in self.reader :
                yield dict \
                    ((self.decode (k), self.decode (v))
                     for k, v in row.iteritems ()
                    )
        # end def __iter__

    # end class UnicodeDictReader
    DictReader = UnicodeDictReader

    class CSV_Writer (object) :
        """ Special CSV Writer which uses intermediate encoding for
            using python2 csv module which can't handle unicode.
            Special feature: Since we're using a StringIO internally
            anyway, we allow f (the file handle) to be None. In that
            case all the output is left in the StringIO and can be
            obtained with getvalue. The encoding used in that case is
            the given encoding parameter.
        """

        def __init__ (self, f, encoding = 'utf-8', ** kw) :
            self.sio     = StringIO ()
            self.writer  = csv.writer (self.sio, ** kw)
            self.f       = f
            self.enc     = 'utf-8'
            if f is None :
                self.enc = encoding
            else :
                self.encoder = codecs.getincrementalencoder (encoding) ()
        # end def __init__

        def valueconv (self, val) :
            """ Allow None and other values that can be converted to a
                string representation (e.g. int)
                Replace characters not representable in the target
                encoding.
            """
            if val is None :
                return None
            return unicode (val).encode (self.enc, 'replace')
        # end def valueconv

        def writerow(self, row) :
            ''' Take a Unicode-encoded row and encode it to the output.
                Preserve semantics of csv writer for None values.
            '''
            self.writer.writerow ([self.valueconv (v) for v in row])
            if self.f is not None :
                data = self.sio.getvalue ()
                data = data.decode (self.enc)
                data = self.encoder.encode (data)
                self.f.write (data)
                self.sio.truncate (0)
        # end def writerow

        def writerows (self, rows) :
            for row in rows :
                self.writerow (row)
        # end def writerows

        def getvalue (self) :
            data = self.sio.getvalue ()
            self.sio.truncate (0)
            return data
        # end def getvalue

    # end class CSV_Writer

class Config (Config_File) :

    config = 'kpm_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , KPM_ADDRESS   = '21 KPM-TEST'
            , KPM_LANGUAGE  = 'german'
            , LOCAL_TRACKER = 'jira'
            )
    # end def __init__

# end class Config

class KPM_File_Attachment (tracker_sync.File_Attachment) :

    def __init__ (self, issue, **kw) :
        self._content = self._name = self._type = None
        for k in 'content', 'name', 'type' :
            setattr (self, '_' + k, kw.get (k, None))
            if k in kw :
                del kw [k]
        self.__super.__init__ (issue, **kw)
    # end def __init__

    @property
    def content (self) :
        if self._content is None :
            self._get_file ()
        return self._content
    # end def content

    @property
    def name (self) :
        if self._name is None :
            self._get_file ()
        return self._name
    # end def name

    @property
    def type (self) :
        if self._type is None :
            self._get_file ()
        return self._type
    # end def type

    def _get_file (self) :
        result = self.issue.kpm.get \
            ( 'problem.base.dokument.download.do'
            , actionCommand = 'downloadDokumentAsAttachment'
            , dokTs         = self.id
            )
        h = result.headers
        if 'content-type' in h :
            self._type = h ['content-type'].decode ('latin1')
        else :
            self._type = 'application/octet-stream'
        if 'content-disposition' in h :
            parts = h ['content-disposition'].decode ('latin1').split (';')
            for p in parts :
                if p.startswith ('filename=') :
                    fn = p.split ('=', 1) [-1].strip ('"')
                    self._name = fn
                    break
        if self._name is None :
            self._name = self.id
        # Allow content to be None, we create an empty file in this case
        self._content = result.content or ''
    # end def _get_file

# end class KPM_File_Attachment

class Problem (tracker_sync.Remote_Issue) :

    File_Attachment_Class = KPM_File_Attachment

    def __init__ (self, kpm, record, lang, canceled = False) :
        self.kpm         = kpm
        self.debug       = self.kpm.debug
        self.canceled    = canceled
        self.lang        = lang
        rec = {}
        for k, v in record.iteritems () :
            if v is not None and v != str ('') :
                rec [k] = v
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        attributes = {}
        if self.canceled :
            attributes ['Status'] = True
        self.__super.__init__ (rec, attributes)
    # end def __init__

    def convert_date (self, value) :
        """ Convert date from roundup value to german date
            representation. Used only for KPM 'Datum'. Currently we
            don't care about timezone, KPM document doesn't specify the
            timezone used. Roundup XMLRPC dates come as UTC if not
            otherwise configured.
            This is automagically called by framework for each roundup
            date property.
        """
        if not value :
            return value
        dt = datetime.strptime (value, "%Y-%m-%d.%H:%M:%S.%f")
        return dt.strftime ('%d.%m.%Y')
    # end def convert_date

    def file_attachments (self, name = None) :
        if self.attachments is None :
            self.attachments = []
            docs = self.get ('Dokumente')
            if docs :
                self.kpm.log.info ("docs: %r" % docs)
                for doc in docs.split () :
                    parsed = parse_qs (doc)
                    if 'dokTs' not in parsed :
                        self.kpm.log.error ("Error parsing doc: %r" % parsed)
                    else :
                        f = KPM_File_Attachment (self, id = parsed ['dokTs'][0])
                        self.attachments.append (f)
        return self.attachments
    # end def file_attachments

    def equal (self, lv, rv) :
        """ Comparison method for remote and local value.
            Since KPM uses latin-1 and other backends use unicode we
            need to (lossyly) convert to latin-1 and compare the result.
            And KPM seems to remove whitespace at end of line.
        """
        if isinstance (lv, string_types) and isinstance (rv, string_types) :
            # Lossy-convert to latin1 and back to unicode
            lv = unicode (lv).encode ('latin1', 'replace').decode ('latin1')
            # Remove trailing whitespace at end of lines for both, the
            # local and the remote value, seems kpm make certain
            # "corrections" here. We also remove empty lines, KPM seems
            # to do the same.
            lv = '\n'.join (x.rstrip () for x in lv.split ('\n') if x.rstrip ())
            rv = '\n'.join (x.rstrip () for x in rv.split ('\n') if x.rstrip ())
            # KPM seems to sometimes convert non-breaking space \xa0 to space
            lv = lv.replace ('\xa0', ' ')
            rv = rv.replace ('\xa0', ' ')
        return self.__super.equal (lv, rv)
    # end def equal

    def __getitem__ (self, name) :
        if name in ('action', 'number') :
            name = getattr (self.lang, name)
        return self.__super.__getitem__ (name)
    # end def __getitem__

    def check_sync_callback (self, syncer, id) :
        """ Check for kpmid is a legacy lifter: Old roundup issues don't
            have a kpm attached and must therefore always sync.
            This forces a sync if we return something that evaluates to
            False in a boolean context.
        """
        if not isinstance (syncer, roundup_sync.Syncer) :
            return True
        kpmid = syncer.get (id, '/kpm/id')
        return bool (kpmid)
    # end def check_sync_callback

    def _update (self, type) :
        self.set ('Aktion', type, None)
        w    = CSV_Writer \
            (None, encoding = 'latin1', delimiter = self.lang.delimiter)
        w.writerow (self.lang.fields_v4_orig)
        w.writerow (self.get (k) for k in self.lang.fields_v4)
        v = w.getvalue ()
        if self.debug :
            print ("Lieferant: %s"      % self.get ('Lieferant'))
            print ("Auftragsart: %s"    % self.get ('Auftragsart'))
            print ("Auftragsnummer: %s" % self.get ('Auftragsnummer'))
            print \
                ( "Called remote_issue.%s: %r" \
                % (('update', 'create')[type == 'I'], v)
                )
            f = open ('sync_out-%s.csv' % self.get ('Nummer'), 'w')
            f.write (v)
            f.close ()
        issue  = self.get ('L-Fehlernummer')
        for k in range (5) :
            try :
                result = self.kpm.update ('%s.csv' % issue, v)
                break
            except requests.exceptions.ConnectionError :
                pass
        else :
            raise
        result = result.strip ()
        start  = 'Die Aktualisierung hat folgende Hinweise ergeben:'
        end    = 'erfolgreich.'
        imp    = 'erfolgreich importiert - neue Problemnummer'
        if result.startswith (start) and imp in result :
            num = result.split (':') [-1]
            return num.strip ()
        if result.startswith ('<!DOCTYPE HTML') :
            msg = "issue%s: Got HTML Response!" % issue
            print (msg)
            self.kpm.log.error (msg)
            return
        if not result.startswith (start) or not result.endswith (end) :
            result = result.replace ('\n\n', '\n')
            print ("issue%s:" % issue, result)
            self.kpm.log.error \
                ('issue %s: %s' % (issue, result.replace ('\n', ' ')))
            self.kpm.log.error ('issue %s: %r' % (issue, v))
    # end def _update

    def create (self) :
        """ Create new remote issue
            We use column format V4 which can represent all the columns
            we may ever need.
        """
        number = self._update ('I')
        return number
    # end def create

    def update (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        if self.dirty :
            self._update ('U')
    # end def update

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
        , 'Country [Code]'
        , 'Country'
        , 'E-Project [Code]'
        , 'E-Project'
        , 'Short Text'
        , 'Problem Description'
        , 'Analysis/Root Cause'
        , 'Functionality [Code]'
        , 'Functionality'
        , 'Repeatable [Code]'
        , 'Repeatable'
        , 'Fault frequency [Code]'
        , 'Fault frequency'
        , 'Project'
        , 'Veh.-no.'
        , 'Device type [Code]'
        , 'Device type'
        , 'Part-no. (causing)'
        , 'HW (causing)'
        , 'SW (causing)'
        , 'device type 2 [Code]'
        , 'device type 2'
        , 'part-no. 2'
        , 'HW 2'
        , 'SW 2'
        , 'device type 3 [Code]'
        , 'device type 3'
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
        , 'L-Status [Code]'
        , 'L-Status'
        , 'L-Fault No.'
        , 'L-System-OK'
        , 'L-Intro date'
        , 'supplier response/fixes'
        , 'Supplier info'
        , 'Tester'
        , 'Tester User'
        , 'Verification status [Code]'
        , 'Verification status'
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
        , 'module relevant [Code]'
        , 'module relevant'
        , 'Active With'
        , 'Authorised To Close'
        )

    fields_german = \
        ( 'Aktion'
        , 'Nummer'
        , 'Änderungs-TS Problem'
        , 'Datum'
        , 'Quelle'
        , 'Land [Code]'
        , 'Land'
        , 'E-Projekt [Code]'
        , 'E-Projekt'
        , 'Kurztext'
        , 'Problembeschreibung'
        , 'Analyse'
        , 'Funktionalität [Code]'
        , 'Funktionalität'
        , 'Reproduzierbar [Code]'
        , 'Reproduzierbar'
        , 'Fehlerhäufigkeit [Code]'
        , 'Fehlerhäufigkeit'
        , 'Projekt'
        , 'Fzg Nr.'
        , 'Gerätetyp [Code]'
        , 'Gerätetyp'
        , 'Teilnummer (verurs.)'
        , 'Hardwarestand (verurs.)'
        , 'Softwarestand (verurs.)'
        , 'Gerätetyp 2 [Code]'
        , 'Gerätetyp 2'
        , 'Teilnummer 2'
        , 'Hardwarestand 2'
        , 'Softwarestand 2'
        , 'Gerätetyp 3 [Code]'
        , 'Gerätetyp 3'
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
        , 'L-Status [Code]'
        , 'L-Status'
        , 'L-Fehlernummer'
        , 'L-System-IO'
        , 'L-Einsatzdatum'
        , 'Lieferantenaussage'
        , 'Lieferanteninfo'
        , 'Tester'
        , 'Tester Benutzer'
        , 'Verifikation-Status [Code]'
        , 'Verifikation-Status'
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
        , 'Modulrelevant [Code]'
        , 'Modulrelevant'
        , 'Aktiv bei'
        , 'Abschlussrecht'
        )

    cols_v4 = dict.fromkeys \
        (( 'FB-Status'
        ,  'Problemlösungsverantwortlicher'
        ,  'Problemlösungsverantwortlicher Benutzer'
        ,  'Modulrelevant [Code]'
        ,  'Modulrelevant'
        ,  'Aktiv bei'
        ,  'Abschlussrecht'
        ))

    fieldnames = dict (english = fields_english, german = fields_german)

    def __init__ (self, delimiter, language = None) :
        self.delimiter = delimiter
        self.language  = language
        self.action    = None
        self.number    = None
    # end def __init__

    def fix_kpm_csv (self, lines) :
        lines = iter (lines)
        first = lines.next ().split (self.delimiter)
        fix   = self.fix_kpm_attr_german
        lang  = "german"
        if  (  first [self.fix_kpm_attr_english [0][0] - 1]
            == self.fix_kpm_attr_english [0][1]
            ) :
            fix  = self.fix_kpm_attr_english
            lang = "english"
        if first [fix [0][0] - 1] != fix [0][1] :
            raise ValueError ("Non-implemented language detected: %s" % first)
        if self.language and lang != self.language :
            raise ValueError \
                ( "Invalid Language, detected: %s, configured: %s"
                % (lang, self.language)
                )
        self.language = lang
        self.action   = first [0]
        self.number   = first [1]
        for idx, header in fix :
            assert first [idx - 1] == first [idx - 2] == header
            first [idx - 2] = first [idx - 2] + ' [Code]'
        yield self.delimiter.join (first)
        for line in lines :
            yield line
    # end def fix_kpm_csv

    @property
    def fields_v4 (self) :
        return self.fieldnames [self.language]
    # end def fields_v4

    @property
    def fields_v4_orig (self) :
        """ Return original fields without ' [Code]' suffixes
        """
        return [(c, c [:-7])[c.endswith (' [Code]')] for c in self.fields_v4]
    # end def fields_v4_orig

    @property
    def fields_v3 (self) :
        return [f for f in self.fieldnames [self.language]
                if f not in self.cols_v4
               ]
    # end def fields_v3

# end class KPM_Language

class Export (autosuper) :

    def __init__ (self, kpm, content, canceled = False, debug = False) :
        self.canceled = canceled
        self.debug    = debug
        self.problems = {}
        self.kpm      = kpm
        self.lang     = KPM_Language \
            (delimiter = str (';'), language = kpm.lang)
        if content is None :
            raise ValueError ("Got empty content")
        if self.debug :
            fo = open ('%s.csv' % self.debug, 'w')
            for line in content :
                fo.write (line.encode ('latin1'))
            fo.close ()
        c = DictReader \
            ( self.lang.fix_kpm_csv (content)
            , delimiter = self.lang.delimiter
            )
        for record in c :
            if record [self.lang.action] :
                continue
            p = Problem (kpm, record, self.lang, canceled = self.canceled)
            self.problems [p.number] = p
    # end def __init__

    def add (self, problem) :
        if problem.number in self.problems :
            raise ValueError ("Duplicate Problem: %s" % problem.number)
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
            syncer.log.info ('Syncing %s' % p_id)
            try :
                syncer.sync (p_id, p)
            except (StandardError, xmlrpclib.Fault) :
                syncer.log.error ("Error syncing %s" % p_id)
                syncer.log_exception ()
                print ("Error syncing %s" % p_id)
                print_exc ()
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

    # Job deletion not yet supported by application
    # According to Dr. Dirk Licht (Author "Endbenutzerhandbuch") 2015-03-11
    #def delete (self) :
    #    return self.kpm.get ('ticket.delete.do', ticketId = self.jobid).content
    ## end def delete

    def download (self) :
        if self.state != 2 or self.type == 0 :
            return None
        c = None
        # If downloaded job exists, return it
        if self.reuse :
            try :
                f = open ('%s.csv' % self.jobid, 'r')
                c = [l.decode ('latin1') for l in f]
            except IOError :
                pass
        if not c :
            r = self.kpm.get ('ticket.download.do', ticketId = self.jobid)
            r.encoding = 'latin1'
            c = [l + '\n' for l in r.text.split ('\n')]
        return c
    # end def download

    def export (self) :
        xpp = dict (canceled = self.type == 2)
        if self.debug :
            xpp ['debug'] = self.jobid
        c  = self.download ()
        xp = Export (self.kpm, c, ** xpp)
        return xp
    # end def export

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

    def poll (self) :
        self.query ()
        count = 0
        while self.state < 2 and count < 1000 :
            sleep (10)
            try :
                self.query ()
            except ElementTree.ParseError as err :
                self.kpm.log.error ("Error parsing JOB-XML: %s" % err)
            count += 1
        if count >= 1000 :
            raise ValueError ("Too many retries accessing KPM")
    # end def poll

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
        v = self.kpm.get ('ticket.info.do', ticketId = self.jobid).content
        if self.debug :
            fn = "JOB-%s-%s" % (self.jobid, self.count)
            f  = open (fn, 'w')
            f.write (v)
            f.close ()
        self.parse (v)
    # end def query

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

class KPM (Log, Lock_Mixin) :
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
        , lang    = 'german'
        , lock    = None
        , ** kw
        ) :
        self.site     = site
        self.verbose  = verbose
        self.debug    = debug
        self.base_url = '/'.join ((site, url))
        self.timeout  = timeout
        self.headers  = {}
        self.lang     = lang
        self.session  = requests.Session ()
        if timeout :
            self.session.timeout = timeout
        if lock :
            self.lockfile = lock
        self.__super.__init__ (** kw)
    # end def __init__

    def login (self, username, password) :
        self.session.auth = (username, password)
        r   = self.get ('b2bLogin.do')
        assert r.status_code == 200
    # end def login

    def get (self, url, ** params) :
        """ Get request """
        url = '/'.join ((self.base_url, url))
        r   = self.session.get (url, params = params)
        return r
    # end def get

    def search (self, **params) :
        p   = dict (params, columnModel = "V4")
        r   = self.get ('search.ee.exportJob.do', **p)
        j   = Job (self, r.content, debug = self.debug)
        if self.debug :
            print ("Job-ID: %s" % r.content)
        return j
    # end def search

    def update (self, name, csvdata) :
        url = '/'.join ((self.base_url, 'problem.ee.import.do'))
        pf  = {'theFile': (name, csvdata, 'text/plain')}
        r   = self.session.post (url, files = pf)
        r.encoding = 'latin1'
        return r.text
    # end def update

# end class KPM

local_trackers = dict (jira = jira_sync.Syncer, roundup = roundup_sync.Syncer)

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "-a", "--address"
        , help    = "KPM-Address of Supplier"
        )
    cmd.add_argument \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/trackersync/kpm_config.py'
        )
    if hasattr (ssl, '_create_unverified_context') :
        cmd.add_argument \
            ( "-C", "--unverified-ssl-context"
            , help    = "Don't verify certificates"
            , action  = 'store_true'
            )
    cmd.add_argument \
        ( "-D", "--debug"
        , help    = "Debugging"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "-j", "--job"
        , help    = "KPM job identifier (mainly used for debugging)"
        , action  = 'append'
        )
    cmd.add_argument \
        ( "-l", "--local-username"
        , help    = "Username for local tracker"
        )
    cmd.add_argument \
        ( "-L", "--local-tracker"
        , help    = "Local tracker, one of %s, default: jira"
                  % ', '.join (local_trackers.keys ())
        )
    cmd.add_argument \
        ( "-n", "--no-action"
        , help    = "Dry-run: Don't update any side of sync"
        , action  = 'store_true'
        , default = False
        , dest    = 'dry_run'
        )
    cmd.add_argument \
        ( "-N", "--no-remote-action"
        , help    = "Remote-dry-run: Don't update remote side of sync"
        , action  = 'store_true'
        , default = False
        , dest    = 'remote_dry_run'
        )
    cmd.add_argument \
        ( "-p", "--local-password"
        , help    = "Password for local tracker"
        )
    cmd.add_argument \
        ( "-P", "--password"
        , help    = "KPM login password"
        )
    cmd.add_argument \
        ( "-R", "--remote-change"
        , help    = "Treat remote values as changed if non-empty. "
                    "Set local value to remote value for two-way sync "
                    "attributes, even if the remote doesn't seem to be "
                    "changed. The default in this case would be to "
                    "overwrite the remote with the local value. This is "
                    "useful in case the sync configuration changed and "
                    "some local values are unset or need update. "
                    "Note that this applies only if the remote value is "
                    "non-empty."
        , dest    = 'remote_change'
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "-s", "--syncdir"
        , help    = "Sync directory, not used by all local trackers, "
                    "default: %(default)s"
        , default = './syncdir'
        )
    cmd.add_argument \
        ( "--schema-only"
        , help    = "Display Jira Schema and stop"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "-u", "--url"
        , help    = "Local Tracker URL for XMLRPC/REST"
        )
    cmd.add_argument \
        ( "-U", "--username"
        , help    = "KPM login user name"
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose reporting"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "--lock-name"
        , help    = "Locking-filename -- note that this is "
                    "dangerous, you should not have two instances of "
                    "kpmsync writing to KPM."
        )
    opt     = cmd.parse_args ()
    config  = Config.config
    cfgpath = Config.path
    if opt.config :
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    kpm = KPM \
        ( verbose = opt.verbose
        , debug   = opt.debug
        , lang    = cfg.KPM_LANGUAGE
        , lock    = opt.lock_name
        )
    username  = opt.username    or cfg.KPM_USERNAME
    password  = opt.password    or cfg.KPM_PASSWORD
    address   = opt.address     or cfg.KPM_ADDRESS
    url       = opt.url         or cfg.get ('LOCAL_URL', None)
    lpassword = opt.local_password or cfg.LOCAL_PASSWORD
    lusername = opt.local_username or cfg.LOCAL_USERNAME
    ltracker  = opt.local_tracker  or cfg.LOCAL_TRACKER
    opt.local_password = lpassword
    opt.local_username = lusername
    opt.url            = url
    opt.local_tracker  = ltracker
    if not opt.schema_only :
        kpm.login  (username = username, password = password)
        jobs = []
        if (opt.job) :
            for j in opt.job :
                jobs.append (Job (kpm, j, debug = opt.debug, reuse = True))
        if not jobs :
            # get active and canceled issues
            jobs.append (kpm.search (address = address))
            jobs.append (kpm.search (address = address, canceled = True))
    syncer = None
    if url and cfg.get ('KPM_ATTRIBUTES') :
        if opt.unverified_ssl_context :
            syncargs ['unverified'] = True
        syncer = local_trackers [opt.local_tracker] \
            ('KPM', cfg.KPM_ATTRIBUTES, opt)
    if opt.schema_only :
        syncer.dump_schema ()
        sys.exit (0)
    old_xp = None
    for j in jobs :
        j.poll ()
        if j.state == 3 :
            raise ValueError ("KPM Job returned error: %s" % repr (j.msg))
        xp = j.export ()
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
