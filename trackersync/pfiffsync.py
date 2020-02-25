#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Dr. Ralf Schlatterbeck Open Source Consulting.
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
import zipfile
import shutil
from argparse           import ArgumentParser
from datetime           import datetime
from xml.etree          import ElementTree
from traceback          import print_exc
from copy               import copy
from glob               import glob
from rsclib.autosuper   import autosuper
from rsclib.execute     import Lock_Mixin, Log
from rsclib.Config_File import Config_File
from rsclib.pycompat    import string_types
from bs4                import BeautifulSoup
from .ssh               import SSH_Client
from .engdatv2          import Engdat_Message, Edifact_Message

try :
    from io import BytesIO
except ImportError :
    import StringIO as BytesIO

from trackersync        import tracker_sync
from trackersync        import roundup_sync
from trackersync        import jira_sync

class Sync_Attribute_Pfiff_Messages (tracker_sync.Sync_Attribute) :
    """ Sync local messages to Pfiff. We get the messages from Pfiff and
        only append those that either don't exist or have an updated
        timestamp. The sync DB of pfiff keeps the messages and their IDs
        so we only have to look up the IDs.
        Note that we only sync messages that start with the given
        prefix.
    """

    def __init__ (self, prefix, ** kw) :
        self.__super.__init__ (local_name = None, ** kw)
        self.prefix = prefix
    # end def __init__

    def sync (self, syncer, id, remote_issue) :
        lmsg = syncer.get_messages (id)
        rmsg = remote_issue.get_messages ()
        lids = dict ((x.id, x) for x in lmsg.values ())
        rids = dict ((x.id, x) for x in rmsg.values ())

        # Remote messages at remote that are no longer existing locally
        pfx = self.prefix
        for rid in rids :
            if rid not in lids or not lids [rid].content.startswith (pfx) :
                remote_issue.delete_message (rid)
        # Loop over ids in local and create/update at remote
        for lid in lids :
            if not lids [lid].content.startswith (pfx) :
                continue
            if lid not in rids :
                rec = self._mangle_rec (lids [lid])
                remote_issue.append_message (rec)
            elif lids [lid].date != rids [lid].date :
                remote_issue.delete_message (lid)
                rec = self._mangle_rec (lids [lid])
                remote_issue.append_message (rec)
    # end def sync

    def _mangle_rec (self, oldrec) :
        rec = oldrec.copy ()
        if rec.content.startswith (self.prefix) :
            rec.content = rec.content [len (self.prefix):].lstrip ()
        return rec
    # end def _mangle_rec

# end class Sync_Attribute_Pfiff_Messages

class Config (Config_File) :

    config = 'kpm_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , LOCAL_TRACKER    = 'jira'
            , COMPANY          = 'TestPrj Zulieferer'
            , COMPANY_SHORT    = 'TPZ'
            , LOCAL_TMP        = '/tmp'
            , LOCAL_OUT_TMP    = '/tmp'
            , ENGDAT_FORMAT    = 'PKZIP-Archive'
            , ENGDAT_FILENAME  = None
            , ENGDAT_PEER_ID      = 'OXXXXXXXXXXXXXXXXX'
            , ENGDAT_PEER_ROUTING = 'peer-routing'
            , ENGDAT_PEER_NAME    = ''
            , ENGDAT_PEER_ADR1    = ''
            , ENGDAT_PEER_ADR2    = ''
            , ENGDAT_PEER_ADR3    = ''
            , ENGDAT_PEER_ADR4    = ''
            , ENGDAT_PEER_COUNTRY = 'DE'
            , ENGDAT_PEER_DEPT    = ''
            , ENGDAT_PEER_EMAIL   = ''
            , ENGDAT_OWN_ID       = 'OYYYYYYYYYYYYYY'
            , ENGDAT_OWN_ROUTING  = 'own-routing'
            , ENGDAT_OWN_NAME     = ''
            , ENGDAT_OWN_ADR1     = ''
            , ENGDAT_OWN_ADR2     = ''
            , ENGDAT_OWN_ADR3     = ''
            , ENGDAT_OWN_ADR4     = ''
            , ENGDAT_OWN_COUNTRY  = 'DE'
            , ENGDAT_OWN_DEPT     = ''
            , ENGDAT_OWN_EMAIL    = ''
            )
    # end def __init__

# end class Config

class Pfiff_File_Attachment (tracker_sync.File_Attachment) :

    def __init__ (self, issue, path, type = 'application/octet-stream', **kw) :
        self.path     = path
        self.dummy    = False
        self._content = None
        self.dirty    = False
        if 'content' in kw :
            self._content = kw ['content']
            del kw ['content']
        if 'dummy' in kw :
            self.dummy = bool (kw ['dummy'])
            del kw ['dummy']
        self.__super.__init__ (issue, type = type, **kw)
        self.log = self.issue.log
    # end def __init__

    @property
    def content (self) :
        if self.dummy :
            return None
        if self._content is None :
            # ZIP will return a key error if file not found in archive
            # We simply log the exception
            try :
                self._content = self.issue.pfiff.zf.read (self.path)
            except KeyError :
                self.issue.pfiff.log_exception ()
                self._content = None
            except AttributeError :
                # The zf is the zip file, it's None when we're syncing
                # in the opposite direction.
                if self.issue.pfiff.zf is not None :
                    raise
        return self._content
    # end def content

# end class Pfiff_File_Attachment

class Problem (tracker_sync.Remote_Issue) :

    File_Attachment_Class = Pfiff_File_Attachment

    def __init__ (self, pfiff, record, now = datetime.now ()) :
        self.pfiff   = pfiff
        self.log     = pfiff.log
        self.debug   = self.pfiff.debug
        self.docinfo = {}
        self.now     = now
        rec = {}
        for k, v in record.iteritems () :
            if v is not None and v != str ('') :
                rec [k] = v
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        self.__super.__init__ (rec, {})
    # end def __init__

    def convert_date (self, value) :
        """ Convert date from roundup date format (that's the format
            used internally by syncer) to local format.
        """
        if not value :
            return value
        value = value.split ('+') [0]
        dt = datetime.strptime (value, '%Y-%m-%d.%H:%M:%S.%f')
        return dt.strftime (self.pfiff.date_fmt)
    # end def convert_date

    def file_attachments (self, name = None) :
        assert self.attachments is not None
        return self.attachments
    # end def file_attachments

    def get_messages (self) :
        assert self.issue_comments is not None
        return self.issue_comments
    # end def get_messages

    def append_message (self, m) :
        self.issue_comments [m.id] = m
        self.dirty = True
        if 'messages' not in self.newvalues :
            self.newvalues ['messages'] = copy (self.record ['messages'])
        self.newvalues ['messages'][m.id] = dict \
            ( id          = m.id
            , author_id   = m.author_id
            , author_name = m.author_name
            , date        = m.date.strftime (self.pfiff.date_fmt)
            , content     = m.content
            )
    # end def append_message

    def delete_message (self, id) :
        del self.issue_comments [id]
        if 'messages' not in self.newvalues :
            self.newvalues ['messages'] = copy (self.record ['messages'])
            del self.newvalues ['messages'][id]
        self.dirty = True
    # end def delete_message

    def update (self, syncer) :
        """ Update remote issue tracker with self.newvalues and
            self.record. Should only be called if self.dirty.
        """
        now = self.now.strftime (self.pfiff.date_fmt)
        id  = self.get ('supplier_company_id')
        xml = ElementTree.Element ('MSR-ISSUE')
        xml.set ('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        xml.set \
            ('xsi:noNamespaceSchemaLocation', 'PAG_ASAM_ISSUE_SCHEMA_V3.0.xsd')

        cds = ElementTree.SubElement (xml, 'COMPANY-DATAS')
        cd  = ElementTree.SubElement (cds, 'COMPANY-DATA')
        ln  = ElementTree.SubElement (cd, 'LONG-NAME')
        ln.text = self.pfiff.opt.company
        sn  = ElementTree.SubElement (cd, 'SHORT-NAME')
        sn.text = self.pfiff.company_short

        cd  = ElementTree.SubElement (cds, 'COMPANY-DATA')
        ln  = ElementTree.SubElement (cd, 'LONG-NAME')
        ln.text = self.pfiff.cfg.COMPANY
        sn  = ElementTree.SubElement (cd, 'SHORT-NAME')
        sn.text = self.pfiff.cfg.COMPANY_SHORT

        sname  = self.get ('assignee_key', 'unknown')
        ts  = ElementTree.SubElement (cd, 'TEAM-MEMBERS')
        tm  = ElementTree.SubElement (ts, 'TEAM-MEMBER')
        tm.set ('ID', sname)
        ln  = ElementTree.SubElement (tm, 'LONG-NAME')
        ln.text = self.get ('assignee_name', sname)
        sn  = ElementTree.SubElement (tm, 'SHORT-NAME')
        sn.text = sname
        ElementTree.SubElement (tm, 'DEPARTMENT')
        ElementTree.SubElement (tm, 'PHONE')
        ElementTree.SubElement (tm, 'FAX')
        ElementTree.SubElement (tm, 'EMAIL')

        messages = self.get_messages ()
        authors  = {}
        for mid in messages :
            m = messages [mid]
            authors [m.author_id] = m.author_name
        for aid in authors :
            author_name = authors [aid]
            tm  = ElementTree.SubElement (ts, 'TEAM-MEMBER')
            tm.set ('ID', aid)
            ln  = ElementTree.SubElement (tm, 'LONG-NAME')
            ln.text = author_name
            sn  = ElementTree.SubElement (tm, 'SHORT-NAME')
            sn.text = aid
            ElementTree.SubElement (tm, 'DEPARTMENT')
            ElementTree.SubElement (tm, 'PHONE')
            ElementTree.SubElement (tm, 'FAX')
            ElementTree.SubElement (tm, 'EMAIL')

        ad  = ElementTree.SubElement (xml, 'ADMIN-DATA')
        ds  = ElementTree.SubElement (ad, 'DOC-REVISIONS')
        dr  = ElementTree.SubElement (ds, 'DOC-REVISION')
        tr  = ElementTree.SubElement (dr, 'TEAM-MEMBER-REF')
        tr.set ('ID-REF', sname)
        dt  = ElementTree.SubElement (dr, 'DATE')
        dt.text = self.get ('updated', now)

        issues = ElementTree.SubElement (xml, 'ISSUES')
        issue  = ElementTree.SubElement (issues, 'ISSUE')

        ln = ElementTree.SubElement (issue, 'LONG-NAME')
        ln.text = self.get ('problem_synopsis')
        sn = ElementTree.SubElement (issue, 'SHORT-NAME')
        sn.text = self.get ('problem_synopsis')
        cat = ElementTree.SubElement (issue, 'CATEGORY')
        cat.text = self.get ('bug_classification')

        desc = ElementTree.SubElement (issue, 'ISSUE-DESC')
        p = ElementTree.SubElement (desc, 'P')
        p.text = self.get ('problem_description')

        infos   = ElementTree.SubElement (issue, 'COMPANY-ISSUE-INFOS')
        info    = ElementTree.SubElement (infos, 'COMPANY-ISSUE-INFO')
        sn      = ElementTree.SubElement (info, 'COMPANY-DATA-REF')
        sn.text = self.pfiff.cfg.COMPANY_SHORT
        id_e    = ElementTree.SubElement (info, 'ISSUE-ID')
        id_e.text = id
        id_t    = ElementTree.SubElement (info, 'TRANSACTION-ID')
        id_t.text = self.pfiff.tid + '-' + id
        info    = ElementTree.SubElement (infos, 'COMPANY-ISSUE-INFO')
        sn      = ElementTree.SubElement (info, 'COMPANY-DATA-REF')
        sn.text = self.pfiff.company_short
        id_e    = ElementTree.SubElement (info, 'ISSUE-ID')
        id_e.text = self.get ('problem_number')

        props = ElementTree.SubElement (issue, 'ISSUE-PROPERTIES')
        state = ElementTree.SubElement (props, 'ISSUE-CURRENT-STATE')
        dt    = ElementTree.SubElement (state, 'DATE')
        dt.text = self.get ('updated', now)
        mb    = ElementTree.SubElement (state, 'TEAM-MEMBER-REF')
        mb.set ('ID-REF', sname)
        state = ElementTree.SubElement (state, 'ISSUE-STATE')
        state.text = self.get ('supplier_status')
        prio  = ElementTree.SubElement (props, 'ISSUE-PRIORITY')
        prio.text = self.get ('priority')
        repr  = ElementTree.SubElement (props, 'REPRODUCIBILITY')
        repr.text = self.get ('reproducibility')
        mss   = ElementTree.SubElement (props, 'DELIVERY-MILESTONES')
        lbls  = \
            ( ('resolve_until_release', 'ESTIMATED')
            , ('resolved_in_release',    'DELIVERED')
            )
        for lbl, cat in lbls :
            ms    = ElementTree.SubElement (mss,   'DELIVERY-MILESTONE')
            sl    = ElementTree.SubElement (ms,    'SHORT-LABEL')
            sl.text = self.get (lbl)
            ct    = ElementTree.SubElement (ms,    'CATEGORY')
            ct.text = cat
            sn    = ElementTree.SubElement (ms,    'COMPANY-DATA-REF')
            sn.text = self.pfiff.cfg.COMPANY_SHORT

        rds = ElementTree.SubElement (issue, 'ISSUE-RELATED-DOCUMENTS')
        for f in self.attachments :
            if f.dirty :
                rd = ElementTree.SubElement (rds, 'ISSUE-RELATED-DOCUMENT')
                xd = ElementTree.SubElement (rd,  'XDOC')
                n  = ElementTree.SubElement (xd,  'LONG-NAME')
                n.text = f.name
                u  = ElementTree.SubElement (xd,  'URL')
                fn = './' + id + '/' + f.name
                u.text = fn
                self.pfiff.output.writestr (fn, f.content)
                self.pfiff.out_dirty = True

        env = ElementTree.SubElement (issue, 'ISSUE-ENVIRONMENT')
        eng = ElementTree.SubElement (env,   'ENGINEERING-OBJECTS')

        for k in self.pfiff.rev_engineering :
            v = self.get (k)
            if not v :
                continue
            xmlkey = self.pfiff.rev_engineering [k]
            o = ElementTree.SubElement (eng, 'ENGINEERING-OBJECT')
            cat = ElementTree.SubElement (o, 'CATEGORY')
            cat.text = xmlkey
            sl  = ElementTree.SubElement (o, 'SHORT-LABEL')
            if xmlkey in ('HARDWARE', 'SOFTWARE', 'PARTNUMBER') :
                sl.text = 'ECU'
                rev = ElementTree.SubElement (o, 'REVISION-LABEL')
                rev.text = v
            else :
                sl.text = v

        ri  = ElementTree.SubElement (issue, 'RELATED-ISSUES')

        sos = ElementTree.SubElement (issue, 'ISSUE-SOLUTIONS')
        so  = ElementTree.SubElement (sos,   'ISSUE-SOLUTION')
        cat = ElementTree.SubElement (so,    'CATEGORY')
        cat.text = 'ANALYSIS'
        dsc = ElementTree.SubElement (so,    'ISSUE-SOLUTION-DESC')
        p   = ElementTree.SubElement (dsc,   'P')
        p.text = self.get ('supplier_comments')

        # Annotations should contain Jira comments
        ans = ElementTree.SubElement (issue, 'ANNOTATIONS')
        for mid in messages :
            m   = messages [mid]
            an  = ElementTree.SubElement (ans, 'ANNOTATION')
            lbl = ElementTree.SubElement (an, 'LABEL')
            lbl.text = self.pfiff.cfg.COMPANY_SHORT
            bm  = ElementTree.SubElement (an, 'TEAM-MEMBER-REF')
            bm.set ('ID-REF', m.author_id)
            dt  = ElementTree.SubElement (an, 'DATE')
            dt.text = m.date.strftime (self.pfiff.date_fmt)
            at  = ElementTree.SubElement (an, 'ANNOTATION-TEXT')
            p   = ElementTree.SubElement (at, 'P')
            p.text = m.content

        fn = './' + id + '.xml'
        self.pfiff.output.writestr \
            ( fn
            , b'<?xml version="1.0" encoding="utf-8"?>\n'
            + ElementTree.tostring (xml, encoding = 'utf-8')
            )
        self.pfiff.out_dirty = True
    # end def update

# end def Problem

class Pfiff (Log, Lock_Mixin) :
    """ Represents an export from PFIFF with multiple issues in a .zip
        file. There can be multiple .xml files in a .zip *and* multiple
        issues per .xml
    """
    date_fmt = '%Y/%m/%dT%H:%M:%S'

    # Map xml path to user-friendly (internal) name
    # The from_xml map is used when reading the file exported by the
    # partner. The to_xml is used when we compute our answer.
    # We use the xml tags delimited by '/'.
    # Note that things under COMPANY-ISSUE-INFO are only called for the
    # peer (opt.company) in from_xml and for both, the supplier (us) and
    # the peer in to_xml. We don't parse the info the peer has about us.
    # Also note that the DELIVERY-MILESTONES (several of them) are
    # mapped to the states in delivery_status below depending on the
    # contents under the CATEGORY tag.
    # The properties kept in ENGINEERING-OBJECTS are in engineering
    # below.
    from_xml = dict \
        (( ('LONG-NAME',                        'problem_synopsis')
         , ('CATEGORY',                         'bug_classification')
         , ('ISSUE-DESC',                       'problem_description')
         , ( 'COMPANY-ISSUE-INFOS/COMPANY-ISSUE-INFO/ISSUE-ID'
           , 'problem_number'
           )
         , ( 'ISSUE-PROPERTIES/ISSUE-CURRENT-STATE/ISSUE-STATE'
           , 'crstatus'
           )
         , ('ISSUE-PROPERTIES/ISSUE-PRIORITY',  'priority')
         , ('ISSUE-PROPERTIES/REPRODUCIBILITY', 'reproducibility')
        ))
    to_xml = dict \
        (( ('LONG-NAME',                        'problem_synopsis')
         , ('SHORT-NAME',                       'problem_synopsis')
         , ('CATEGORY',                         'bug_classification')
         , ('ISSUE-DESC',                       'problem_description')
         , ( 'COMPANY-ISSUE-INFOS/COMPANY-ISSUE-INFO/ISSUE-ID'
           , 'supplier_company_id'
           )
         , ( 'ISSUE-PROPERTIES/ISSUE-CURRENT-STATE/ISSUE-STATE'
           , 'supplier_status'
           )
         , ('ISSUE-PROPERTIES/ISSUE-PRIORITY',  'priority')
         , ('ISSUE-PROPERTIES/REPRODUCIBILITY', 'reproducibility')
        ))
    delivery_milestone = dict \
        ( REQUESTED = 'release_wanted'
        , ESTIMATED = 'resolve_until_release'
        , DELIVERED = 'resolved_in_release'
        )
    # TEST_BENCH is an alias for VEHICLE, EE435 states that import
    # recognizes bot, VEHICLE and TEST_BENCH while export only yields
    # VEHICLE.
    engineering = dict \
        ( COMPONENT       = 'component_name'
        , DTC             = 'DTC'
        , GROUP           = 'function_group'
        , HARDWARE        = 'component_hw_version'
        , OFFER_ID        = 'offer_number'
        , SODTC           = 'SODTC'
        , SOFTWARE        = 'component_sw_version'
        , SUB_GROUP       = 'function_component'
        , VEHICLE         = 'vehicle'
        , TEST_BENCH      = 'vehicle'
        , COMMITTEE       = 'ccb_relevant'
        , VARIANTS        = 'var_product_name'
        , PROJECT         = 'vehicle_project'
        , EXT_TEST_SYTEM  = 'ets'
        , EXT_TEST_ID     = 'ets_id'
        , EXT_TEST_STATUS = 'ets_status'
        , ISSUE_REPORTER  = 'issue_reporter'
        , TEST_CASE       = 'test_case'
        , TRIAL_UNITS     = 'trial_units'
        , V_FUNCTION      = 'v_function'
        , EE_TOP_TOPIC    = 'ee_top_topic'
        )
    engineering ['ECU-PROJECT']     = 'project_name'
    engineering ['DTC-DESCRIPTION'] = 'DTC_synopsis'
    engineering ['DTC-FREQUENCY']   = 'frequency'
    rev_engineering = dict ((v, k) for k, v in engineering.items ())
    rev_engineering ['vehicle'] = 'VEHICLE'
    pudis_map = dict \
        ( HARDWARE   = 'pudis_hw_version_'
        , SOFTWARE   = 'pudis_sw_version_'
        , PARTNUMBER = 'pudis_part_number_'
        )
    multiline = set (('problem_description',))

    def __init__ (self, opt, cfg, syncer, now = datetime.now (), tid = '') :
        self.opt           = opt
        self.cfg           = cfg
        self.debug         = opt.debug
        self.company       = opt.company
        self.company_short = opt.company_short
        self.date          = None
        self.issues        = []
        self.path          = []
        self.pudis_no      = 0
        self.pudis         = {}
        self.zf            = None
        self.out_dirty     = False
        self.now           = now
        self.tid           = tid or now.strftime ('%Y-%m-%dT%h:%m:%s')
        if opt.lock_name :
            self.lockfile = opt.lock_name
        self.__super.__init__ ()
        self.log.info ('Started')

        if opt.output is None :
            if opt.zipfile :
                zf, ext = os.path.splitext (opt.zipfile)
                opt.output = zf + '-out' + ext
            else :
                opt.output = '_out-.zip'
        compression        = zipfile.ZIP_DEFLATED
        self.output        = zipfile.ZipFile (opt.output, "w", compression)
        # First read sync db, only issues where remote is not closed are
        # put in a list
        # List of not-yet-synced remote ids
        self.unsynced = {}
        for rid in syncer.oldsync_iter () :
            id = syncer.get_oldvalues (rid)
            if id is not None :
                self.unsynced [rid] = copy (syncer.oldremote)
        if opt.zipfile :
            self.zf = zipfile.ZipFile (opt.zipfile, 'r')
            for n in self.zf.namelist () :
                fn = n
                if fn.startswith ('./') :
                    fn = fn [2:]
                if '/' in fn :
                    continue
                if fn.endswith ('.xml') or fn.endswith ('.XML') :
                    self.parse (self.zf.read (n))
        # We also need to sync the issues that didn't come in the .zip
        # file: We could have local changes to these issues.
        for rid in self.unsynced :
            v = self.unsynced [rid]
            if 'messages' not in v :
                v ['messages'] = {}
            p = Problem (self, v, now = self.now)
            p.attachments = []
            for f in v.get ('files', []) :
                pa = Pfiff_File_Attachment \
                    (p, id = f, name = f, path = f, dummy = True)
                p.attachments.append (pa)
            p.issue_comments = {}
            comments = v.get ('messages', {})
            for c in comments :
                rec = copy (comments [c])
                dt  = datetime.strptime (rec ['date'], self.date_fmt)
                del rec ['date']
                m = Problem.Message_Class (p, date = dt, ** rec)
                p.issue_comments [m.id] = m
            self.issues.append (p)
    # end def __init__

    def as_rendered_html (self, node) :
        et = ElementTree.ElementTree (node)
        io = BytesIO ()
        et.write (io)
        bs = BeautifulSoup (io.getvalue (), "lxml", from_encoding='utf-8')
        return bs.get_text ('\n')
    # end def as_rendered_html

    def close (self) :
        if self.zf is not None :
            self.zf.close ()
        self.output.close ()
        if not self.out_dirty :
            os.unlink (self.opt.output)
        # At this point we free the lock
        self.unlock ()
        self.log.info ("Pfiff: Close")
    # end def close

    def parse (self, xml) :
        self.team_members = {}
        tree = ElementTree.fromstring (xml)
        if tree.tag != 'MSR-ISSUE' :
            raise ValueError ("Invalid xml start-tag: %s" % tree.tag)
        for cd in tree.findall ('.//COMPANY-DATA') :
            ln = cd.find ('LONG-NAME')
            sn = cd.find ('SHORT-NAME')
            if self.company in ln.text :
                self.company_short = sn.text.strip ()
            ts = cd.find ('TEAM-MEMBERS')
            if ts is not None :
                for tm in ts :
                    assert tm.tag == 'TEAM-MEMBER'
                    id = tm.get ('ID')
                    ln = tm.find ('LONG-NAME').text.strip ()
                    ph = tm.find ('PHONE').text.strip ()
                    em = tm.find ('EMAIL').text.strip ()
                    self.team_members [id] = ' '.join \
                        ((ln, 'Phone:', ph, 'email:', em))
        ad = tree.find ('ADMIN-DATA')
        dt = ad.find ('.//DATE')
        self.date = datetime.strptime (dt.text.strip (), self.date_fmt)
        issues = tree.find ('ISSUES')
        for issue in issues :
            self.issue = {}
            for node in issue :
                self.parse_a_node (node)
            att = []
            if 'attachments' in self.issue :
                att = self.issue ['attachments']
                del self.issue ['attachments']
                self.issue ['files'] = {}
            number = self.issue ['problem_number']
            if 'messages' not in self.issue :
                self.issue ['messages'] = {}
            p = Problem (self, self.issue, now = self.now)
            p.attachments = []
            attold   = {}
            comments = {}
            if number in self.unsynced :
                attold   = self.unsynced [number].get ('files', {})
                comments = self.unsynced [number].get ('messages', {})
            p.issue_comments = {}
            for cid in comments :
                if cid not in p.record ['messages'] :
                    p.record ['messages'][cid] = comments [cid]
                rec = copy (comments [cid])
                dt  = datetime.strptime (rec ['date'], self.date_fmt)
                del rec ['date']
                m = Problem.Message_Class (p, date = dt, ** rec)
                p.issue_comments [m.id] = m
            for a in att :
                path, name = a
                if name in attold :
                    del attold [name]
                pa = Pfiff_File_Attachment \
                    (p, id = path, name = name, path = path)
                p.attachments.append (pa)
                p.record ['files'][name] = True
            for a in attold :
                pa = Pfiff_File_Attachment \
                    (p, id = a, name = a, path = a, dummy = True)
                p.attachments.append (pa)
                p.record ['files'][a] = True
            if number in self.unsynced :
                del self.unsynced [number]
            self.issues.append (p)
    # end def parse

    def parse_a_node (self, node) :
        self.path.append (node.tag)
        p = '/'.join (self.path)
        if node.tag == 'COMPANY-ISSUE-INFO' :
            self.parse_company_info (node)
        elif node.tag == 'DELIVERY-MILESTONE' :
            self.parse_milestone (node)
        elif node.tag == 'RELATED-ISSUES' :
            # Currently we don't parse related issues
            self.path.pop ()
            return
        elif node.tag == 'ENGINEERING-OBJECT' :
            self.parse_engineering_object (node)
        elif node.tag == 'ISSUE-SOLUTION' :
            self.parse_issue_solution (node)
        elif node.tag == 'ANNOTATION' :
            self.parse_annotation (node)
        elif node.tag == 'ISSUE-RELATED-DOCUMENT' :
            n = node.find ('XDOC')
            self.parse_attachment (n)
        elif node.tag == 'TEAM-MEMBER-REF' :
            if self.path [-2] == 'COMPANY-ISSUE-INFO' :
                id = node.get ('ID-REF')
                # Guard for Buggy implementation
                if id in self.team_members :
                    self.issue ['owner_fp'] = self.team_members [id]
                else :
                    self.issue ['owner_fp'] = id
        elif p in self.from_xml :
            name = self.from_xml [p]
            if name in self.multiline :
                txt = self.as_rendered_html (node)
                if txt :
                    self.issue [name] = txt
            elif node.text :
                self.issue [name] = node.text.strip ()
        elif len (node) :
            for n in node :
                self.parse_a_node (n)
        self.path.pop ()
    # end def parse_a_node

    def parse_annotation (self, node) :
        lbl = node.find ('LABEL')
        txt = self.as_rendered_html (node.find ('ANNOTATION-TEXT'))
        if lbl and lbl.text.strip () != self.company_short :
            return
        if 'in_analyse_comments' in self.issue :
            self.issue ['in_analyse_comments'] += '\n' + txt
        else :
            self.issue ['in_analyse_comments'] = txt
    # end def parse_annotation

    def parse_attachment (self, node) :
        url = node.find ('URL').text
        fn  = node.find ('LONG-NAME-1').text
        if url is None :
            return
        # Don't know if this can happen, both url = None and fn = None
        # were observed in the wild. So if only the fn is None we
        # reconstruct the filename from the URL.
        if fn is None :
            fn = url.rsplit ('/', 1) [-1]
        url = url.strip ()
        fn  = fn.strip ()
        if 'attachments' not in self.issue :
            self.issue ['attachments'] = []
        self.issue ['attachments'].append ((url, fn))
    # end def parse_attachment

    def parse_company_info (self, node) :
        ref = node.find ('COMPANY-DATA-REF')
        if ref.text.strip () != self.company_short :
            return
        for n in node :
            self.parse_a_node (n)
    # end def parse_company_info

    def parse_engineering_object (self, node) :
        cat = node.find ('CATEGORY').text
        lbl = node.find ('SHORT-LABEL').text
        # Looks like these tags can somtimes be empty
        if not cat or not lbl :
            return
        cat = cat.strip ()
        lbl = lbl.strip ()
        rev = node.find ('REVISION-LABEL')
        if cat in ('HARDWARE', 'SOFTWARE', 'PARTNUMBER') :
            if rev.text is None :
                rev = ''
            else :
                rev = rev.text.strip ()
            if lbl == 'ECU' :
                lbl = rev
            else :
                if lbl not in self.pudis :
                    self.pudis [lbl] = self.pudis_no
                    self.pudis_no += 1
                no = self.pudis [lbl]
                self.issue ['pudis_component_name_%s' % (no + 1)] = lbl
                self.issue [self.pudis_map [cat] + "%s" % (no + 1)] = rev
                return
        self.issue [self.engineering [cat]] = lbl
    # end def parse_engineering_object

    def parse_issue_solution (self, node) :
        cat = node.find ('CATEGORY').text.strip ()
        dsc = node.find ('ISSUE-SOLUTION-DESC')
        txt = self.as_rendered_html (dsc)
        if cat == 'PROPOSAL' :
            if 'action_points' in self.issue :
                self.issue ['action_points'] += '\n' + txt
            else :
                self.issue ['action_points'] = txt
            for doc in node.findall ('.//XDOC') :
                self.parse_attachment (doc)
    # end def parse_issue_solution

    def parse_milestone (self, node) :
        cat   = node.find ('CATEGORY')
        # Seems the category is (sometimes?) not exported
        if cat is not None :
            cat = cat.text.strip ()
        else :
            cat = 'REQUESTED'
        label = node.find ('SHORT-LABEL').text
        if label is None :
            return
        label = label.strip ()
        # Only import requested release label
        if cat != 'REQUESTED' :
            return
        self.issue [self.delivery_milestone [cat]] = label
    # end def parse_milestone

    def sync (self, syncer) :
        for issue in self.issues :
            id = issue.problem_number
            try :
                syncer.sync (id, issue)
            except (Exception) :
                syncer.log.error ("Error syncing %s" % id)
                syncer.log_exception ()
                print ("Error syncing %s" % id)
                print_exc ()
        # Todo: implement syncing new local issues
    # end def sync

    def __repr__ (self) :
        r = []
        for i in self.issues :
            r.append ("ISSUE")
            r.append (repr (i))
        return '\n'.join (r)
    # end def repr

# end class Pfiff

local_trackers = dict (jira = jira_sync.Syncer, roundup = roundup_sync.Syncer)
lastsync_fmt   = '%Y-%m-%dT%H:%M:%S'

class Engdat_Sync (autosuper) :

    def __init__ (self, cfg, opt, syncer) :
        self.cfg    = cfg
        self.opt    = opt
        self.syncer = syncer
        self.log    = self.syncer.log
        self.now    = datetime.now ()
        self.outnum = 0
        self.__super.__init__ ()
        self.log.info ("Engdat sync started")
    # end def __init__

    def engdat_name (self, outnum = None) :
        """ ENGDAT filename without 'ENG' prefix, also used inside engdat
            message.
        """
        if outnum is None :
            outnum = self.outnum
        l  = 3 # if changed, change %02d below, sum needs to be 5
        assert outnum <= 99
        en = self.cfg.get ('ENGDAT_FILENAME')
        if en is None :
            en = self.cfg.ENGDAT_PEER_ROUTING
        if not en or len (en) < l :
            raise ValueError ("Short/Missing ENGDAT_FILENAME: %s" % en)
        en = en [:l].upper ()
        return self.now.strftime ('%y%m%d%H%M%S') + "%02d" % outnum + en
    # end def engdat_name

    def rm_engdat (self, fn) :
        """ Remove all files belonging to an ENGDAT description file
            We get all files with a wildcard in position 23-26 of the given
            filename (sequence number) since this is the end of the ENGDAT
            file name we will replace the rest of the name with a wildcard.
            (OFTP will add some timestamp information to the ENGDAT file name
            which is not guaranteed to be unique for all ENGDAT files
            belonging to an ENDAT Packet).
        """
        path, rest = os.path.split (fn)
        pattern = rest [:23] + '*'
        for f in glob (os.path.join (path, pattern)) :
            self.log.debug ("Unlink: %s" % f)
            os.unlink (f)
    # end def rm_engdat

    def sync (self) :
        opt = self.opt
        cfg = self.cfg
        # Get date of last sync:
        try :
            with open (os.path.join (opt.syncdir, '__lastsync')) as f :
                dt = f.read ()
        except IOError :
            dt = '2018-01-01T00:00:00'
        lastsync = datetime.strptime (dt.strip (), lastsync_fmt)
        fnmin    = lastsync.strftime ('ENG%y%m%d%H%M%SZZZZZ9')
        if ':' in cfg.OFTP_INCOMING :
            # If we have IPv6 addresses they may contain ':', so use rsplit
            host, dir = cfg.OFTP_INCOMING.rsplit (':', 1)
            ssh = SSH_Client \
                ( host, cfg.SSH_KEY
                , password   = cfg.SSH_PASSPHRASE
                , user       = cfg.SSH_USER
                , local_dir  = cfg.LOCAL_TMP
                , remote_dir = dir
                )
            flist = []
            for f in ssh.list_files () :
                if not f.startswith ('ENG') :
                    continue
                # Get only files with timestamp > last sync
                if f <= fnmin :
                    continue
                flist.append (f)
            ssh.get_files (*flist)
            ssh.close ()
        else :
            flist = []
            for f in os.listdir (cfg.OFTP_INCOMING) :
                if not f.startswith ('ENG') :
                    continue
                # Get only files with timestamp > last sync
                if f <= fnmin :
                    continue
                flist.append (f)
                fn = os.path.join (cfg.OFTP_INCOMING, f)
                shutil.copy (fn, cfg.LOCAL_TMP)
        # Now loop over tempfiles in LOCAL_TMP, we only use files with
        # sequence number 001 (engdat descriptions) and process these
        self.outnum = 0
        for fn in sorted (flist) :
            if not fn.startswith ('ENG') or len (fn) < 26 :
                continue
            if fn [23:26] != '001' :
                continue
            self.sync_to_remote (fn)
            self.outnum += 1
        # No incoming files to sync, just export our local changes
        if not flist :
            opt.zipfile = None
            opt.output  = os.path.join \
                (cfg.LOCAL_OUT_TMP, 'ENG' + self.engdat_name () + '002002')
            self.log.debug ("Syncing: (no input) out: %s" % (opt.output))
            n     = self.engdat_name ()
            pfiff = Pfiff (opt, cfg, self.syncer, now = self.now, tid = n)
            pfiff.sync (self.syncer)
            pfiff.close () # closes .zip file!
            if pfiff.out_dirty :
                self.outname = os.path.join \
                    (cfg.LOCAL_OUT_TMP, 'ENG' + self.engdat_name ())
                self.write_output (3)
        self.log.info ('Finished Sync')
    # end def sync

    def sync_to_remote (self, fn = None) :
        cfg     = self.cfg
        opt     = self.opt
        npkg    = 2 # our first guess at the number of engdat members
        pkg     = 2 # first pkg
        self.outname = os.path.join \
            (cfg.LOCAL_OUT_TMP, 'ENG' + self.engdat_name ())
        path = os.path.join (cfg.LOCAL_TMP, fn)
        with open (path) as f :
            m = Edifact_Message (bytes = f.read ())
            m.check ()
        if m.sde.routing.routing != cfg.ENGDAT_PEER_ROUTING :
            self.log.error \
                ( "Invalid sender routing: %s expected %s"
                % (m.sde.routing.routing, cfg.ENGDAT_PEER_ROUTING)
                )
            self.rm_engdat (path)
            self.write_lastsync (fn)
            return
        if m.rde.routing.routing != cfg.ENGDAT_OWN_ROUTING :
            self.log.error \
                ( "Invalid receiver routing: %s expected %s"
                % (m.rde.routing.routing, cfg.ENGDAT_OWN_ROUTING)
                )
            self.rm_engdat (path)
            self.write_lastsync (fn)
            return
        for efc in m.segment_iter ('EFC') :
            gpat  = fn [:23] + "%03d" % int (efc.file_info.seqno) + '*'
            gpat  = os.path.join (cfg.LOCAL_TMP, gpat)
            efcfn = glob (gpat)
            if len (efcfn) != 1 :
                raise ValueError ("Sync-file not found, pattern=%s" % gpat)
            efcfn = efcfn [0]
            fmt = cfg.get ('ENGDAT_FORMAT', None)
            if fmt and fmt != efc.file_format.file_format :
                self.log.warning \
                    ( 'Invalid file format: "%s" expected "%s", trying anyway'
                    % (efc.file_format.file_format, fmt)
                    )
            self.log.debug ("Processing: %s" % efcfn)
            self.syncer.reinit ()
            opt.output  = self.outname + '%03d%03d' % (npkg, pkg)
            opt.zipfile = efcfn
            self.log.debug \
                ("Syncing: in: %s out: %s" % (opt.zipfile, opt.output))
            n     = self.engdat_name ()
            pfiff = Pfiff (opt, cfg, self.syncer, now = self.now, tid = n)
            pfiff.sync (self.syncer)
            if pfiff.out_dirty :
                npkg += 1
                pkg  += 1
            pfiff.close ()
            os.unlink (efcfn)
        os.unlink (path)
        self.write_lastsync (fn)
        self.write_output (npkg)
    # end def sync_to_remote

    def write_output (self, npkg) :
        cfg = self.cfg
        opt = self.opt
        # Did we send something? npkg is 1 greater than the number of
        # files in the resulting engdat pkg. If it's 2 we didn't produce
        # any output files and do not send anything.
        if npkg != 2 :
            # Need to rename the files
            pat = self.outname + '*'
            for fn in glob (pat) :
                d, f = os.path.split (fn)
                fnew = os.path.join \
                    (d, f [:20] + "%03d" % (npkg - 1) + f [23:])
                os.rename (fn, fnew)
            em = Engdat_Message \
                ( sender_id        = cfg.ENGDAT_OWN_ID
                , sender_name      = cfg.ENGDAT_OWN_NAME
                , sender_routing   = cfg.ENGDAT_OWN_ROUTING
                , sender_email     = cfg.ENGDAT_OWN_EMAIL
                , sender_addr1     = cfg.ENGDAT_OWN_ADR1
                , sender_addr2     = cfg.ENGDAT_OWN_ADR2
                , sender_addr3     = cfg.ENGDAT_OWN_ADR3
                , sender_addr4     = cfg.ENGDAT_OWN_ADR4
                , sender_country   = cfg.ENGDAT_OWN_COUNTRY
                , sender_dept      = cfg.ENGDAT_OWN_DEPT
                , receiver_id      = cfg.ENGDAT_PEER_ID
                , receiver_name    = cfg.ENGDAT_PEER_NAME
                , receiver_routing = cfg.ENGDAT_PEER_ROUTING
                , receiver_email   = cfg.ENGDAT_PEER_EMAIL
                , receiver_addr1   = cfg.ENGDAT_PEER_ADR1
                , receiver_addr2   = cfg.ENGDAT_PEER_ADR2
                , receiver_addr3   = cfg.ENGDAT_PEER_ADR3
                , receiver_addr4   = cfg.ENGDAT_PEER_ADR4
                , receiver_country = cfg.ENGDAT_PEER_COUNTRY
                , receiver_dept    = cfg.ENGDAT_PEER_DEPT
                , docdt            = self.now
                , dt               = self.now
                , docno            = self.engdat_name () [:17]
                , ref              = self.engdat_name () [:14]
                , msgref           = self.engdat_name () [:14]
                )
            for k in range (2, npkg) :
                em.append_efc ()
            with open (self.outname + '%03d%03d' % (npkg - 1, 1), "w") as f :
                f.write (em.to_bytes ())
            # Now copy the resulting files to the remote OFTP tmp.
            flist = glob (pat)
            if ':' in cfg.OFTP_OUTGOING :
                host1, tmp = cfg.OFTP_TMP_OUT.rsplit (':', 1)
                host, dir = cfg.OFTP_OUTGOING.rsplit (':', 1)
                assert host1 == host
                # Copy files to OFTP_TMP_OUT
                ssh = SSH_Client \
                    ( host, cfg.SSH_KEY
                    , password   = cfg.SSH_PASSPHRASE
                    , user       = cfg.SSH_USER
                    , local_dir  = cfg.LOCAL_OUT_TMP
                    , remote_dir = tmp
                    )
                ssh.put_files (* flist)
                dirperm = ssh.stat (dir)
                uid     = None
                for f in flist :
                    bn = os.path.basename (f)
                    np = os.path.join (dir, bn)
                    ssh.rename (bn, np)
                    # files need to be group-writeable for oftp server
                    # to process them
                    ssh.chmod (np, 0664)
                    # Get my own uid from created file once
                    if not uid :
                        perm = ssh.stat (np)
                        uid  = perm.st_uid
                    # We also set the group explicitly to the group of
                    # the directory, seems that sftp doesn't honor the
                    # s-bit of the group.
                    ssh.chown (np, uid, dirperm.st_gid)
                ssh.close ()
                if not opt.keep_files :
                    for f in flist :
                        os.unlink (f)
            else :
                # Directly move the files to the *local* OFTP_OUTGOING
                dirperm = os.stat (cfg.OFTP_OUTGOING)
                for f in flist :
                    fnew = os.path.join \
                        (cfg.OFTP_OUTGOING, os.path.basename (f))
                    if opt.keep_files :
                        shutil.copy (f, fnew)
                    else :
                        os.rename (f, fnew)
                    os.chmod  (fnew, 0664)
                    os.chown  (fnew, -1, dirperm.st_gid)
    # end def write_output

    def write_lastsync (self, fn) :
        """ Determine date from engdat filename and write __lastsync file
        """
        assert fn.startswith ('ENG')
        dt  = datetime.strptime (fn [3:15], '%y%m%d%H%M%S')
        # Two-digit years will wrap back at some point in the future
        if dt.year < self.now.year - 50 :
            dt = datetime \
                (dt.year + 100, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        with open (os.path.join (self.opt.syncdir, '__lastsync'), 'w') as f :
            f.write (dt.strftime (lastsync_fmt) + '\n')
    # end def write_lastsync

# end class Engdat_Sync

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "-c", "--config"
        , help    = "Configuration file"
        , default = '/etc/trackersync/pfiff_config.py'
        )
    cmd.add_argument \
        ( "-C", "--company"
        , help    = "Partner company full name, default=%(default)s"
        , default = 'Porsche AG'
        )
    cmd.add_argument \
        ( "--company-short"
        , help    = "Partner company short name, default=%(default)s"
        , default = 'PAG'
        )
    cmd.add_argument \
        ( "-D", "--debug"
        , help    = "Debugging"
        , action  = 'store_true'
        , default = False
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
        ( "-k", "--keep-files"
        , help    = "Keep outgoing engdat/zip files"
        , action  = "store_true"
        , default = False
        )
    cmd.add_argument \
        ( "-p", "--local-password"
        , help    = "Password for local tracker"
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
        ( "-o", "--output"
        , help    = "Output file (zip) (default standard output)"
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
        ( "-v", "--verbose"
        , help    = "Verbose reporting"
        , action  = 'store_true'
        , default = False
        )
    cmd.add_argument \
        ( "-z", "--zipfile"
        , help    = "ZIP file to read"
        )
    cmd.add_argument \
        ( "--lock-name"
        , help    = "Locking-filename -- note that this is "
                    "dangerous, you should not have two instances of "
                    "pfiffsync running simultaneously."
        )
    opt     = cmd.parse_args ()
    config  = Config.config
    cfgpath = Config.path
    if opt.config :
        cfgpath, config = os.path.split (opt.config)
        config = os.path.splitext (config) [0]
    cfg = Config (path = cfgpath, config = config)
    url       = opt.url or cfg.get ('LOCAL_URL', None)
    lpassword = opt.local_password or cfg.LOCAL_PASSWORD
    lusername = opt.local_username or cfg.LOCAL_USERNAME
    ltracker  = opt.local_tracker  or cfg.LOCAL_TRACKER
    opt.local_password = lpassword
    opt.local_username = lusername
    opt.url            = url
    opt.local_tracker  = ltracker
    syncer = None
    pfiff  = None
    if url :
        syncer = local_trackers [opt.local_tracker] \
            ('PFIFF', cfg.PFIFF_ATTRIBUTES, opt)
    if opt.schema_only :
        syncer.dump_schema ()
        sys.exit (0)

    if cfg.get ('OFTP_INCOMING', None) and not opt.zipfile :
        es = Engdat_Sync (cfg, opt, syncer)
        es.sync ()
    else :
        # This is used if we do sync of a single .zip file or no file at all
        if url :
            pfiff = Pfiff (opt, cfg, syncer)
        if syncer and pfiff :
            pfiff.sync (syncer)
            # Zip files need to be closed
            pfiff.close ()
# end def main

if __name__ == '__main__' :
    main ()
