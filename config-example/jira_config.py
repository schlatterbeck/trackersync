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
from __future__ import absolute_import

""" Example configuration for Jira Sync """

from trackersync import roundup_sync

JIRA_USERNAME = 'test'
JIRA_PASSWORD = 'test'
JIRA_URL      = 'http://localhost:9090/rest/api/2'
ROUNDUP_URL   = 'http://username:password@localhost:8080/tracker/xmlrpc'
JIRA_ASSIGNEE = 'test'
TRACKER_NAME  = 'jira-test'

JIRA_ATTRIBUTES = \
    ( roundup_sync.Sync_Attribute_One_Way
        ( roundup_name = 'title'
        , remote_name  = 'summary'
        )
    , roundup_sync.Sync_Attribute_One_Way
        ( roundup_name = 'ext_status'
        , remote_name  = 'status.name'
        )
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'release'
        , remote_name  = None
        , default      = '?'
        )
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'inherit_ext'
        , remote_name  = None
        , default      = 'yes'
        )
    , roundup_sync.Sync_Attribute_Message
        ( headline     = 'Description:'
        , remote_name  = 'description'
        )
    , roundup_sync.Sync_Attribute_Messages ()
    , roundup_sync.Sync_Attribute_Default_Message
        ( message      = 'Imported from Jira without messages'
        )
    , roundup_sync.Sync_Attribute_Files ()
    )

