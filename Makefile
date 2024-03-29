# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# And point the environment variable RELEASETOOLS to the checkout
ifeq (,${RELEASETOOLS})
    RELEASETOOLS=../releasetools
endif
LASTRELEASE:=$(shell $(RELEASETOOLS)/lastrelease -n --tag-re='[0-9.]+')
TRACKERSYNC=__init__.py engdatv2.py jira_sync.py jirasync.py \
    kpmwssync.py pfiffsync.py roundup_sync.py ssh.py tracker_sync.py

VERSIONPY=trackersync/Version.py
VERSION=$(VERSIONPY)
README=README.rst
SRC=Makefile setup.py $(TRACKERSYNC:%.py=trackersync/%.py) \
    MANIFEST.in $(README) README.html

USERNAME=schlatterbeck
PROJECT=trackersync
PACKAGE=trackersync
CHANGES=changes
NOTES=notes

all: $(VERSION)

$(VERSION): $(SRC)

clean:
	rm -f MANIFEST trackersync/Version.py notes changes default.css \
	    README.html README.aux README.dvi README.log README.out     \
	    README.tex announce_pypi
	rm -rf trackersync.egg-info trackersync/__pycache__ $(CLEAN)

include $(RELEASETOOLS)/Makefile-pyrelease
