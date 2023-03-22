#!/usr/bin/python
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
from __future__ import absolute_import

""" Example configuration for Jira Sync """

from trackersync import roundup_sync

JIRA_USERNAME = 'test'
JIRA_PASSWORD = 'test'
JIRA_URL      = 'http://localhost:9090/rest/api/2'
LOCAL_URL     = 'http://username:password@localhost:8080/tracker/xmlrpc'
JIRA_ASSIGNEE = 'test'
TRACKER_NAME  = 'jira-test'
LOCAL_TRACKER = 'roundup'

JIRA_ATTRIBUTES = \
    ( roundup_sync.Sync_Attribute_Two_Way
        ( local_name   = 'title'
        , remote_name  = 'summary'
        )
    , roundup_sync.Sync_Attribute_To_Local
        ( local_name   = 'ext_status'
        , remote_name  = 'status.name'
        )
    , roundup_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'release'
        , remote_name  = None
        , default      = '?'
        )
    , roundup_sync.Sync_Attribute_To_Local_Default
        ( local_name   = 'inherit_ext'
        , remote_name  = None
        , default      = 'yes'
        )
    , roundup_sync.Sync_Attribute_Message
        ( headline     = 'Description:'
        , remote_name  = 'description'
        )
    , roundup_sync.Sync_Attribute_Messages (keyword = 'External Sync')
    , roundup_sync.Sync_Attribute_Default_Message
        ( message      = 'Imported from Jira without messages'
        )
    , roundup_sync.Sync_Attribute_Files (prefix = 'jira:')
    )

