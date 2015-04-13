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

""" Example configuration for KPM Sync """

from trackersync import roundup_sync

KPM_USERNAME = 'user'
KPM_PASSWORD = 'secret'
KPM_ADDRESS  = '21 KPM-TEST'
ROUNDUP_URL  = 'http://username:password@localhost:8080/tracker/xmlrpc'

KPM_ATTRIBUTES = \
    ( roundup_sync.Sync_Attribute_One_Way
        ( roundup_name = 'title'
        , remote_name  = 'Kurztext'
        )
    , roundup_sync.Sync_Attribute_One_Way
        ( roundup_name = 'ext_status'
        , remote_name  = 'Status'
        )
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'release'
        , remote_name  = 'Softwarestand (verurs.)'
        , default      = '?'
        )
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'part_of'
        , remote_name  = None
        , default      = '73897'
        )
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'category'
        , remote_name  = None
        , default      = '273'
        )
    , roundup_sync.Sync_Attribute_Message
        ( headline     = 'Analyse:'
        , remote_name  = 'Analyse'
        )
    , roundup_sync.Sync_Attribute_Message
        ( headline     = 'Beschreibung:'
        , remote_name  = 'Problembeschreibung'
        )
    , roundup_sync.Sync_Attribute_Message
        ( headline     = 'Lieferantenaussage:'
        , remote_name  = 'Lieferantenaussage'
        )
    , roundup_sync.Sync_Attribute_Files ()
    )

