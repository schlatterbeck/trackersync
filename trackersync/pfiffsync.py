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
from argparse           import ArgumentParser
from datetime           import datetime
from xml.etree          import ElementTree
from traceback          import print_exc
from rsclib.autosuper   import autosuper
from rsclib.execute     import Lock_Mixin, Log
from rsclib.Config_File import Config_File
from rsclib.pycompat    import string_types
from bs4                import BeautifulSoup

try :
    from io import BytesIO
except ImportError :
    import StringIO as BytesIO

from trackersync        import tracker_sync
from trackersync        import roundup_sync
from trackersync        import jira_sync

class Config (Config_File) :

    config = 'kpm_config'
    path   = '/etc/trackersync'

    def __init__ (self, path = path, config = config) :
        self.__super.__init__ \
            ( path, config
            , LOCAL_TRACKER = 'jira'
            )
    # end def __init__

# end class Config

class Pfiff_File_Attachment (tracker_sync.File_Attachment) :

    def __init__ (self, issue, path, type = 'application/octet-stream', **kw) :
        self.path = path
        self._content = None
        if 'content' in kw :
            self._content = kw ['content']
            del kw ['content']
        self.__super.__init__ (issue, type = type, **kw)
    # end def __init__

    @property
    def content (self) :
        if self._content is None :
            self._content = self.issue.pfiff.zf.read (self.path)
        return self._content
    # end def content

# end class Pfiff_File_Attachment

class Problem (tracker_sync.Remote_Issue) :

    File_Attachment_Class = Pfiff_File_Attachment

    def __init__ (self, pfiff, record) :
        self.pfiff   = pfiff
        self.debug   = self.pfiff.debug
        self.docinfo = {}
        rec = {}
        for k, v in record.iteritems () :
            if v is not None and v != str ('') :
                rec [k] = v
        # We can restrict the attributes to be synced to an explicit
        # subset. The default is no restriction with attributes = {}
        self.__super.__init__ (rec, {})
    # end def __init__

    def file_attachments (self, name = None) :
        assert self.attachments is not None
        return self.attachments
    # end def file_attachments

    def update (self, syncer) :
        """ Update remote issue tracker with self.newvalues.
        """
        raise NotImplementedError ("TODO")
        # FIXME: Generate XML in self.pfiff.output
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
    # peer (opt.company) in from_xml and only for the supplier
    # (us) in to_xml. We don't parse the info the peer has about us.
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
        , TEST_BENCH      = 'vehicle' # Seems this is an alias name
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
    pudis_map = dict \
        ( HARDWARE   = 'pudis_hw_version_'
        , SOFTWARE   = 'pudis_sw_version_'
        , PARTNUMBER = 'pudis_part_number_'
        )
    multiline = set (('problem_description',))

    def __init__ (self, opt) :
        self.opt           = opt
        self.debug         = opt.debug
        self.company       = opt.company
        self.company_short = None
        self.date          = None
        self.issues        = []
        self.path          = []
        self.pudis_no      = 0
        self.pudis         = {}
        if opt.lock_name :
            self.lockfile = opt.lock_name

        if opt.output is None :
            zf, ext = os.path.splitext (opt.zipfile)
            opt.output = zf + '-out' + ext
        compression        = zipfile.ZIP_DEFLATED
        self.output        = zipfile.ZipFile (opt.output, "w", compression)
        self.zf            = zipfile.ZipFile (opt.zipfile, 'r')
        for n in self.zf.namelist () :
            fn = n
            if fn.startswith ('./') :
                fn = fn [2:]
            if '/' in fn :
                continue
            print (fn)
            if fn.endswith ('.xml') or fn.endswith ('.XML') :
                self.parse (self.zf.read (n))
    # end def __init__

    def as_rendered_html (self, node) :
        et = ElementTree.ElementTree (node)
        io = BytesIO ()
        et.write (io)
        bs = BeautifulSoup (io.getvalue (), "lxml", from_encoding='utf-8')
        return bs.get_text ('\n')
    # end def as_rendered_html

    def close (self) :
        self.zf.close ()
        self.output.close ()
    # end def close

    def parse (self, xml) :
        tree = ElementTree.fromstring (xml)
        if tree.tag != 'MSR-ISSUE' :
            raise ValueError ("Invalid xml start-tag: %s" % tree.tag)
        for cd in tree.findall ('.//COMPANY-DATA') :
            ln = cd.find ('LONG-NAME')
            sn = cd.find ('SHORT-NAME')
            if self.company in ln.text :
                self.company_short = sn.text.strip ()
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
            p = Problem (self, self.issue)
            p.attachments = []
            for a in att :
                path, name = a
                pa = Pfiff_File_Attachment \
                    (p, id = path, name = name, path = path)
                p.attachments.append (pa)
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
        elif len (node) :
            for n in node :
                self.parse_a_node (n)
        elif p in self.from_xml :
            name = self.from_xml [p]
            if name in self.multiline :
                txt = self.as_rendered_html (node)
                if txt :
                    self.issue [name] = txt
            elif node.text :
                self.issue [name] = node.text.strip ()
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
        url = node.find ('URL').text.strip ()
        fn  = node.find ('LONG-NAME-1').text.strip ()
        if 'attachments' not in self.issue :
            self.issue ['attachments'] = []
        self.issue ['attachments'].append ((url, fn))
    # end def parse_attachment

    def parse_company_info (self, node) :
        ref = node.find ('COMPANY-DATA-REF')
        if ref.text.strip () != self.company_short :
            return
        id  = node.find ('ISSUE-ID')
        self.parse_a_node (id)
    # end def parse_company_info

    def parse_engineering_object (self, node) :
        cat = node.find ('CATEGORY').text.strip ()
        lbl = node.find ('SHORT-LABEL').text.strip ()
        rev = node.find ('REVISION-LABEL')
        if cat in ('HARDWARE', 'SOFTWARE', 'PARTNUMBER') :
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
        if cat :
            cat = cat.text.strip ()
        else :
            cat = 'REQUESTED'
        label = node.find ('SHORT-LABEL').text.strip ()
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
        ( "-p", "--local-password"
        , help    = "Password for local tracker"
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
    if opt.zipfile :
        pfiff = Pfiff (opt)
    if url :
        syncer = local_trackers [opt.local_tracker] \
            ('PFIFF', cfg.PFIFF_ATTRIBUTES, opt)
    if opt.schema_only :
        syncer.dump_schema ()
        sys.exit (0)
    if syncer and pfiff :
        pfiff.sync (syncer)
        # Zip files need to be closed
        pfiff.close ()
# end def main

if __name__ == '__main__' :
    main ()
