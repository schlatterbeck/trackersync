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
    ( roundup_sync.Sync_Attribute_Check
        ( roundup_name = '/kpm/ready_for_sync'
        , remote_name  = None
        , r_default    = True
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = 'title'
        , remote_name  = 'Kurztext'
        , r_default    = '?'
        )
    , roundup_sync.Sync_Attribute_One_Way
        ( roundup_name = '/ext_tracker_state/ext_status'
        , remote_name  = 'Status'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = 'release'
        , remote_name  = 'Softwarestand (verurs.)'
        , r_default    = '?'
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
    , roundup_sync.Sync_Attribute_Default
        ( roundup_name = 'inherit_ext'
        , remote_name  = None
        , default      = 'yes'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/analysis.content'
        , remote_name  = 'Analyse'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/description.content'
        , remote_name  = 'Problembeschreibung'
        , r_default    = '-'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/supplier_answer.content'
        , remote_name  = 'Lieferantenaussage'
        )
    # The following 3 have additional sync *to* remote above.
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
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = "creation"
        , remote_name  = "Datum"
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = "Quelle"
        , l_default    = "default here"
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = "E-Projekt"
        , l_default    = "project here"
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/reproduceable'
        , remote_name  = 'Reproduzierbar [Code]'
        , map = {True: 'XH', False: 'XI'}
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/fault_frequency.name'
        , remote_name  = 'Fehlerhäufigkeit [Code]'
        , map = dict (once = 'XE', repeatedly = 'XF', always = 'XG')
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/kpm_function.kpm_key'
        , remote_name  = 'Funktionalität [Code]'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = '/kpm/hardware_version'
        , remote_name  = 'Hardwarestand (verurs.)'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = 'severity.name'
        , remote_name  = 'Bewertung'
        , r_default    = 'Minor'
        , l_default    = 'DB'
        , map  = dict (Minor = 'DB', Major = 'DB', Showstopper = 'DB')
        , imap = dict
            ( A1 = 'Showstopper'
            , A  = 'Showstopper'
            , B  = 'Major'
            , C  = 'Minor'
            , D  = 'Minor'
            , DB = 'Minor'
            , DV = 'Minor'
            )
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Projekt'
        , l_default    = 'project here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Gerätetyp [Code]'
        , l_default    = 'device here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Teilnummer (verurs.)'
        , l_default    = 'part number here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Koordinator'
        , l_default    = 'coordinator here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Koordinator Benutzer'
        , l_default    = 'SOME,NAME'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Fachkoordinator'
        , l_default    = 'coordinator here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Fachkoordinator Benutzer'
        , l_default    = 'SOME,NAME'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Problemlösungsverantwortlicher'
        , l_default    = 'responsible here'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = 'category.name'
        , remote_name  = 'Problemlösungsverantwortlicher Benutzer'
        , l_default    = 'SOME,NAME'
        , map = dict (Project_name = 'SOME,OTHER_NAME')
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Lieferant'
        , l_default    = '21 KPM-TEST'
        )
    , roundup_sync.Sync_Attribute_To_Remote
        ( roundup_name = 'status.name'
        , remote_name  = 'L-Status [Code]'
        , map = dict
            ( analyzing = '0'
            , escalated = '0'
            , open      = '1'
            , feedback  = '1'
            , testing   = '4'
            , suspended = '5'
            , closed    = '5'
            )
        )
    , roundup_sync.Sync_Attribute_To_Remote
        ( roundup_name = 'id'
        , remote_name  = 'L-Fehlernummer'
        )
    , roundup_sync.Sync_Attribute_Two_Way
        ( roundup_name = 'fixed_in'
        , remote_name  = 'L-System-IO'
        )
    , roundup_sync.Sync_Attribute_To_Remote_Default
        ( roundup_name = None
        , remote_name  = 'Modulrelevant [Code]'
        , l_default    = '00'
        )
    )

