#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
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

try :
    from trackersync.Version import VERSION
except :
    VERSION = None
from distutils.core import setup, Extension

description = []
f = open ('README.rst')
logo_stripped = False
for line in f :
    if not logo_stripped and line.strip () :
        continue
    logo_stripped = True
    description.append (line)

license     = 'GNU General Public License (GPL)'
baseurl     = 'http://downloads.sourceforge.net'
download    = '/'.join ((baseurl, 'project/trackersync/trackersync'))

setup \
    ( name             = "trackersync"
    , version          = VERSION
    , description      = "Issue Tracker Synchronisation Tool"
    , long_description = ''.join (description)
    , license          = license
    , author           = "Ralf Schlatterbeck"
    , author_email     = "rsc@runtux.com"
    , packages         = ['trackersync']
    , platforms        = 'Any'
    , url              = "http://trackersync.sourceforge.net/"
    , download_url     = \
        "%(download)s/%(VERSION)s/trackersync-%(VERSION)s.tar.gz" % locals ()
    , classifiers      = \
        [ 'Development Status :: 5 - Production/Stable'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Developers'
        ]
    )
