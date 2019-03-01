Tracker Sync: Tool for Synchronizing Issue Trackers
===================================================

:Author: Ralf Schlatterbeck <rsc@runtux.com>

.. |--| unicode:: U+2013   .. en dash

When running an issue tracker |--| e.g. for tracking bugs and feature
requests of a software project |--| sooner or later the requirement arises
that you want to synchronize certain issues with an external issue tracker.

External issue trackers might be run by an external open source project
where you're monitoring certain issues because bugs you're tracking
locally depend on fixes of the remote project. Or you're a company
tracking issues of their customers |--| the customer may run their own
issue tracker and certain issues in the customer's tracker are for you.

In particular this is widespread in the automotive industry: Suppliers
are expected to synchronize their bug-trackers with the bug-tracker of
the OEM they're working for. For an individual supplier usually more
than one OEM-tracker needs to be kept in sync.

This project solves this requirement. Currently the local issue tracker
(the one *you* are running) is limited to roundup_, an open source issue
tracker or jira_ a well-known commercial offering.
For the remote tracker we're currently supporting KPMweb, the
issue tracker run by VW/Audi with access for their suppliers |--| if
you're one of them you know how to access it. Another OEM from the
automotive industry is now supported: The tracker run by Porsche named
PFIFF. Other remote trackers are currently being implemented, notably
support for jira_. This is not to be confused with the local tracker 
*you* are running: Jira is well-supported as the local tracker. Jira as
the remote tracker, however, is work in progress.

.. _roundup: http://roundup.sourceforge.net
.. _jira: https://www.atlassian.com/software/jira

Extending Roundup
-----------------

This section applies only when you're running roundup.
For synchronisation with external trackers you need to add a new
``Class`` and several attributes to your roundup instance. We need a new
``ext_tracker Class``::

    ext_tracker = Class(db, "ext_tracker", name = String (indexme = 'no')
        , description = String (indexme = 'no')
        , url_template = String (indexme = 'no'))
    ext_tracker.setkey("name")

This ``Class`` tracks information about external trackers.
If two-way message synchronisation should be used an additional class is
needed for keeping track of the message-ids  in the remote system::

    ext_msg = Class(db, "ext_msg", ext_tracker = Link ("ext_tracker")
        , msg = Link ("msg")
        , ext_id = String (indexme = 'no')
        , key = String (indexme = 'no')
        )
    ext_msg.setkey("key")


Now we need to add some attributes to the ``issue`` class for keeping
information about the external tracker::

    ...
    , ext_id = String ()
    , ext_status = String ()
    , ext_attributes = Link ("msg")
    , ext_tracker = Link ("ext_tracker")
    ...

These attributes are needed for keeping track of the status of the
remote issue. In particular the ``ext_id`` tracks a unique identifier of
the remote issue. The ``ext_attributes`` track *all* attributes of the
remote issue as a json dictionary. If you want to display these
attributes in your issue, it makes sense to extend the html templates
``html/issue.item.html`` and ``html/issue.index.html`` in your tracker
directory.

Running the Sync
----------------

To configure the synchronisation you can find example configuration
files in the ``config-example`` subdirectory. Configuration files are in
python syntax and should end in ``.py``. The attributes to synchronize
need to be defined. Property definitions typically define the attribute
name on the remote side and on the local (roundup) side. For roundup,
property names can include dots (".") indicating dereferencing an item,
e.g., "prio.description" would dereference a Link property "prio" and
return the value of the property "description" of this prio. In addition
there is a syntax for Link1-properties: These are not stored in the
roundup-issue itself but link to the roundup issue with a Link property
named "issue".  The sync framework makes sure that at most one such link
exists per issue. The syntax for these properties is
"/<classname>/property" where property can again be a multilevel
property including dots. The classname is the name of the Link1 class
and the item linking to the currently-synchronized issue is determined
by searching the class for items where the "issue" property refers to
the current issue.

The following attribute definitions are possible:

- ``Sync_Attribute_One_Way`` defines a one-way sync from the remote
  tracker to your local roundup tracker. It gets two parameters, the
  name in roundup called ``roundup_name`` and the name in the remote
  issue tracker called ``remote_name``. An example is the ``title``
  attribute in roundup which is named ``Kurztext`` in KPMweb. We also
  want to synchronize the remote ``Status`` to the ``ext_status`` field
  in roundup.
- ``Sync_Attribute_Default`` defines a one-way sync from the remote
  tracker to your local roundup tracker but the attribute in the local
  roundup tracker is only set if it is still undefined.  In particular
  this happens when a new issue is created locally.  It gets three
  parameters, the same two parameters as a ``Sync_Attribute_One_Way``,
  and a third ``default`` parameter.  If a remote_name is given, the
  value |--| if it is non-empty |--| is used. If the remote value is not set
  or if the ``remote_name`` is specified as ``None``, the ``default``
  parameter will be used instead. This is useful to define suitable
  defaults for new issues created in roundup.
- ``Sync_Attribute_To_Remote`` defines a one-way sync to the remote
  tracker. A use-case is to set the local tracker issue number in the
  remote tracker (if the remote tracker supports a fields for this).
- ``Sync_Attribute_Two_Way`` defines a two-way sync to the remote
  tracker. The sync first determines if the attribute in the remote
  tracker has changed (by comparing the ext_attributes from the last
  sync to the current attributes). If the attribute *has* changed in the
  remote tracker, the attribute is updated in roundup |--| even if it also
  changed there. Only if the attribute has not changed in the remote
  tracker it is determined if the roundup attribute is different from
  the remote attribute. If it is, the remote tracker is updated.
- ``Sync_Attribute_Files`` synchronizes file attachments of the remote
  issue to the local issue. If an optional ``prefix`` parameter is given
  to the constructor, all filenames starting with the given prefix are
  considered for synchronisation *to* the remote tracker. First all
  files of the remote tracker are checked against local files. Then the
  opposite direction is synchronized considering only the files with a
  relevant prefix in their filename. Note that files synchronized *to*
  the remote system are renamed to the naming convention enforced by the
  remote system *in the local tracker*. This is done because for file
  synchronisation only the *filename* is compared between the remote
  system and the local system. Each remote sync implementation must
  ensure that the filenames generated are unique for each roundup issue.
  For example for Jira the filenames consist of the filename in Jira
  plus the unique file id in Jira.
- ``Sync_Attribute_Messages`` synchronizes messages of the remote
  tracker with the messages in the local tracker. First all messages of
  the remote tracker are checked against the local messages, all
  messages not found in the local tracker are created. The
  synchronisation in the other direction is only done if a keyword
  parameter is given to the class constructor of
  ``Sync_Attribute_Messages``. All messages having the given keyword are
  synchronized to the remote tracker. This is currently only implemented
  for roundup as the local tracker.
- ``Sync_Attribute_Message`` synchronizes a field in the remote tracker
  to a new message in roundup. Whenever the field in the remote issue
  changes, a new message is created in roundup and linked to the issue.
  The sync attribute gets two parameters, the ``remote_name`` of the
  field in the remote issue tracker and a ``headline`` that should be
  put into the roundup message as the first line. This sync attribute
  type exists because some issue trackers (notably KPMweb) don't have
  the notion of a discussion thread with messages added to an issue. In
  that case communication takes place with fixed fields that can be
  filled in during the process of resolving an issue, these fields
  change of time. An example is the analysis of the problem underlying
  an issue that is specified in the ``Analyse`` field in KPMweb. We
  synchronize this field to a roundup message with the headline
  ``Analyse:``.
- ``Sync_Attribute_Default_Message`` specifies a default message that is
  added to the local issue whenever all other message synchronisation
  has not produced any message. This attribute needs to be *after* all
  other message synchronisation attributes in the list of sync
  attributes. Adding a default message is used to add at least one
  message to a new issue in roundup because at least one message is
  required.

In addition to the synchronized attributes, the URL of the local
tracker (which includes user name and password), the KPMweb user name
and password, and the address of the supplier in KPMweb (used as a
search term) can be specified in the configuration file. These options
can also be set on the command line. If they are specified in both, the
configuration file and on the command line, the command line wins.

The configuration file for the KPMweb synchronisation typically lives in
``/etc/trackersync/kpm_config.py`` but can be overridden on the command
line. The configuration file for the Jira synchronisation backend lives
in the same directory by default.

Porsche PFIFF
+++++++++++++

For Porsche PFIFF you need to set up an OFTP connection to the OEM.
The Open Source `OFTP Server from Mendelson`_ was used successfully, albeit
with a patch: The server does not support specification of a virtual
OFTP file name for each transfer, instead for each poll request a
filename can be specified. For ENGDAT specification of the file name is
necessary. The patch can be found in the file ``mendelson.diff``.
Note that the patch has no checking if the filename of the spool-file
conforms to the requirements of OFTP (which supports only uppercase
characters, numbers, and a dash plus some other less-used characters). A
better implementation would have more checking. The patch was also
posted to the `Mendelson Forum`_, you may want to check with them if
this feature will make it into a future version. They also have a
commercial version, so they may reserve such a feature for a commercial
offering as one user on the forum suggested.

.. _`OFTP Server from Mendelson`:
    https://sourceforge.net/projects/mendelson-oftp2/
.. _`Mendelson Forum`: http://mendelson-e-c.com/node/3222

The sync uses ENGDAT v2 packages as input. These consist of a description
file in EDIFACT syntax plus a ZIP file with the synchronisation data.
For output again an ENGDAT v2 package is produced. In addition for
testing a ``-z`` option exists that can specify a ZIP file as input
for the sync. An example configuration using ENGDAT can be found in
``config-examples/pfiff_jira_config.py``.

Resources
---------

Download the source at https://sourceforge.net/projects/trackersync/
and install using the standard python setup, e.g.::

 python setup.py install --prefix=/usr/local

Alternatively you may want to install using ``pip``::

 pip install trackersync

Changes
-------

Version 1.5: Pfiff Sync

Now Porsche Pfiff is supported. You need an OFTP-Server for the actual
data transfer. We transfer data from/to the OFTP server (which can be
either local or accessed via SSH/SFTP). We also create an ENGDAT v2
package.

Version 1.4: Jira as local tracker

Now we can sync between Jira as the local tracker and KPM as the remote
tracker.

Version 1.3: Two-way KPM sync

We now can sync changed attributes back to KPM

Version 1.2: KPM data structures in roundup

Now we can model some of the KPM data structures in roundup.

Version 1.1: Implemented Jira synchronisation

Jira synchronisation is implemented, this needs a recent version of the
python ``requests`` library installed. In some new sync attributes have
been implemented, in particular two-way synchronisation. Two-way
synchronisation is now also supported for messages and files.

 - Jira synchronisation
 - Two-way sync for atomic attributes
 - Two-way sync for messages and files
 - Standalone command-line tools for KPM and Jira sync

Version 1.0: Initial Release with kpmsync

Tool for Synchronisation of Issue Trackers

 - First Release version
