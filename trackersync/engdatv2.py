#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__       import unicode_literals
from __future__       import print_function
from rsclib.autosuper import autosuper
from datetime         import datetime

import sys

""" This implements enough EDIFACT to generate and parse ENGDAT messages
    Note that this is ENGDAT V2, V3 would use XML.
"""

# Example messages from the standard
# VDA-Empfehlung 4951 P 1 Version 2.3, Oktober 2005
msg1 = \
    ( "UNA:+.? '"

      'UNB'
      '+UNOC:1'
      '+O0013006000F2--AG:OD:F2ABT1MEIER'
      '+O0013005466F3--AG:OD:F3ABT6MÜLLER'
      '+950129:1310'
      '+444'
      "'"

      'UNH'
      '+210'
      '+ENGDAT:001::OD'
      "'"

      'MID'
      '+950129131005F2HBG'
      '+950128:1830'
      '+XYZ-GHHD'
      "'"

      'SDE'
      '+F2:Firma 2 AG:Postfach:20150 Hamburg:::195634'
      '+DE+ED0590021'
      '+Abt. ABT-1??:Herr Meier:?+49-40-123-0:38793:46355528746'
      ':?+49-40-123-34555:6667788:hemeier@f2.de'
      '+Übermittlungs GmbH:Postfach 4020:20160 Hamburg:::U2599_245'
      '+DE'
      '+Abt. UE-1:Frau Meder:?+49-40-907-0:363:463555247'
      ':?+49-40-907-400:66677999:kmeder@f2.de'
      "'"

      'RDE'
      '+F3:Firma 3 AG:Postfach:70180 Stuttgart 1:::4712'
      '+DE+He071511'
      'Abt. ABT-6:Herr Müller:0711-45-0:36554:4446578839:?+49-0711-45-36666'
      ':55566773:lmueller@f3.de'
      'Data-Transfer Gesellschaft:Münchner Straße 100:70020 Stuttgart:::222999'
      '+DE'
      '+UET-3:Herr Weller:?+49-711-6786-0:31:4446578839'
      ':?+49-711-566780:555997744:nweller@dtg.de'
      "'"

      'DAN'
      '+310:Angebot'
      '+XYZ00033'
      '+950121:1410'
      "'"

      'FTX'
      '+Angebot auf Ihre Anfrage vom:10.12. des Jahres. Zeichnungen'
      ':sind vertraulich zu behandeln.'
      "'"

      'EFC'
      '+002:EINSPRITZANLAGE.IGS'
      '+IGS:IGES:5.2'
      '+646:US ASCII 7BIT'
      '+CATIA RS6000:V4.1.3:CATIGE'
      '+TOD:Angebot'
      '+Abt. K-1'
      '+3D-Flächenmodell und Drawing'
      '+Keine'
      "'"

      'FTX'
      '+Die Toleranzvorgaben für:Flächenqualitäten sind'
      ':unbedingt einzuhalten.'
      "'"

      'FTX'
      '+Die Größe des Modells:beträgt 15 Megabyte'
      "'"

      'DSD'
      '+'
      '+1'
      '+11-38 D 000341'
      '+A0'
      '+Einspritzanlage'
      '+dispositionsfrei:5:950118'
      "'"

      'FTX'
      '+Radien unter 3 mm sind nicht:als Flächen beschrieben'
      "'"

      'LOF'
      '+003:CATIA.LAY (11-38 D)'
      '+LAY:Layer-Konventionen'
      "'"

      'SEC'
      '+38AXB10:AXX0A:XYZ-GHHD'
      "'"

      'EFC'
      '+003:CATIA.LAY (11-38 D)'
      '+:Text'
      '+646:US ASCII 7BIT'
      '+Text-Editor'
      '+TOD:Angebot'
      '+Abt. K-1'
      '+Layer-Konventionen'
      '+Keine'
      "'"

      'FTX'
      '+Layerkonventionen sind:unbedingt einzuhalten'
      "'"

      'SEC'
      '+38AXB10:AXX0A:XYZ-GHHD'
      "'"

      'TOT'
      '+3:PCE'
      "'"

      'UNT'
      '+18'
      '+210'
      "'"

      'UNZ'
      '+1'
      '+444'
      "'"
    ).encode ('latin-1')


msg2 = \
    ( 'UNB'
      '+UNOC:1'
      '+O0013005400ABC-AG:OD'
      '+O0013005430XYZ-AG:OD:UVWMÜLLER'
      '+950227:1354'
      '+445'
      "'"

      'UNH'
      '+215'
      '+ENGDAT:001::OD'
      "'"

      'MID'
      '+950227135401ABKLN'
      '+950227'
      "'"

      'SDE'
      '+:ABC AG:Hahn Straße 10:50039 Köln'
      '+DE'
      '+ABCAG'
      '+Abt. DEF:Herr Maier:0211-88-0:3345'
      '+ABC AG'
      '+DE'
      '+Abt. UEB::3369'
      "'"

      'RDE'
      '+:XYZ AG:Postfach 888777:80277 München'
      '+DE'
      '+XYZAG '
      '+Abt. UVW:Herr Müller:089-4567:4499'
      "'"
      
      'EFC'
      '+2:992647001.exp'
      '+NAT:CATIA export WS-Format V4 ISO8859-1:4.2.2'
      '+885'
      '+CATIA RS6000:V4.2.2:CATEXP PROJECT-A '
      '+:Einbauuntersuchung'
      '+'
      '+3D-Flächenmodell'
      "'"

      'FTX'
      '+Kombi-Instrument für E-XY'
      "'"

      'TOT'
      '+2'
      "'"

      'UNT'
      '+8'
      '+215'
      "'"

      'UNZ'
      '+1'
      '+445'
      "'"
    ).encode ('latin-1')

# From wikipedia
msg3 = \
    ( "UNA:+.? '"
      "UNB+IATB:1+6XPPC:ZZ+LHPPC:ZZ+940101:0950+1'"
      "UNH+1+PAORES:93:1:IA'"
      "MSG+1:45'"
      "IFT+3+XYZCOMPANY AVAILABILITY'"
      "ERC+A7V:1:AMD'"
      "IFT+3+NO MORE FLIGHTS'"
      "ODI'"
      "TVL+240493:1000::1220+FRA+JFK+DL+400+C'"
      "PDI++C:3+Y::3+F::1'"
      "APD+74C:0:::6++++++6X'"
      "TVL+240493:1740::2030+JFK+MIA+DL+081+C'"
      "PDI++C:4'"
      "APD+EM2:0:1630::6+++++++DA'"
      "UNT+13+1'"
      "UNZ+1+1'"
    ).encode ('latin-1')

msg4 = \
    ( b"UNB+UNOC:1+O0013006000F2:OD+O0013005466F3:OD+180213:1611+ref'"
      b"UNH+ref+ENGDAT:001::OD'"
      b"MID+180213161111XYZZY+180213:1611'"
      b"SDE+:Z. ulieferer++sender-routingcode+:::::::sender@example.com'"
      b"RDE+:O. EM++receiver-routingcode+:::::::receiver@example.com'"
      b"EFC+2+ZIP+815+trackersync+:New sync file'"
      b"TOT+2'"
      b"UNT+9+ref'"
      b"UNZ+1+ref'"
    )

def brepr (bs) :
    """ For regression-testing with python2 and python3
    """
    r = repr (bs)
    if not r.startswith ('b') :
        print ('b' + r)
        return
    print (r)
# end def brepr

def btuple (bs) :
    """ For regression-testing with python2 and python3
        Print a tuple of byte values so that it looks like a python 3 repr
    """
    if sys.version_info [0] >= 3 :
        return tuple (bs)
    t = tuple (bs)
    r = []
    for k in t :
        r.append ('b' + repr (k))
    e = ')'
    if len (t) == 1 :
        e = ',)'
    print ('(' + ', '.join (r) + e)
# end def btuple

class UNA (autosuper) :
    """
        An EDIFACT message can start with an una segment.
        This defines the markup characters in use.
        The una segment contains 6 characters:
        - Component data separator (default ':')
        - Data element separator (default '+')
        - Decimal mark (default ',') later versions specify both '.' and
          ', can be used
        - release character (for quoting, similar to \ quoting)
          (default: '?')
        - reserved, must be space
        - segment terminator, (default: "'")
    """

    segment_name = 'UNA'

    def __init__ (self, bytes = b"UNA:+.? '") :
        self.from_bytes (bytes)
        self.length = 9
    # end def __init__

    @property
    def component_sep (self) :
        return self.una [0].encode ('ASCII')
    # end def component_sep

    @property
    def element_sep (self) :
        return self.una [1].encode ('ASCII')
    # end def element_sep

    @property
    def release_char (self) :
        return self.una [3].encode ('ASCII')
    # end def release_char

    @property
    def segment_terminator (self) :
        return self.una [-1].encode ('ASCII')
    # end def segment_terminator

    def check (self) :
        pass
    # end def check

    def from_bytes (self, bytes) :
        assert bytes.startswith (b'UNA')
        self.una = bytes [3:].decode ('ASCII')
    # end def from_bytes

    def to_bytes (self) :
        return ('UNA' + self.una).encode ('ASCII')
    # end def to_bytes

    def __length__ (self) :
        return self.length
    # end def __length__

    def __str__ (self) :
        return 'UNA' + self.una
    # end def __str__
    __unicode__ = __str__
    __repr__ = __str__

# end class UNA

# default una
una = UNA ()

class _Part_Iter (autosuper) :

    def iterparts (self, bytes, delimiter) :
        """ Iterate over parts delimited with delimiter taking
            una.release_char into account
            Test iterparts:
        >>> e = Edifact_Element (una = una)
        >>> btuple (e.iterparts (b'Abt. ABT-1??????:Herr Meier', b':'))
        (b'Abt. ABT-1??????', b'Herr Meier')
        >>> btuple (e.iterparts (b'Abt. ABT-1????:Herr Meier', b':'))
        (b'Abt. ABT-1????', b'Herr Meier')
        >>> btuple (e.iterparts (b'Abt. ABT-1??:Herr Meier', b':'))
        (b'Abt. ABT-1??', b'Herr Meier')
        >>> btuple (e.iterparts (b'Abt. ABT-1:Herr Meier', b':'))
        (b'Abt. ABT-1', b'Herr Meier')
        >>> btuple (e.iterparts (b'Abt. ABT-1?:Herr Meier', b':'))
        (b'Abt. ABT-1?:Herr Meier',)
        >>> btuple (e.iterparts (b'DE+ED0590021', b'+'))
        (b'DE', b'ED0590021')
        >>> btuple (e.iterparts (b':?+49-40:6667788:hemeier@f2.de+bla', b'+'))
        (b':?+49-40:6667788:hemeier@f2.de', b'bla')
        """
        l    = len (bytes)
        offs = 0
        esc  = self.una.release_char
        while offs < l :
            try :
                # Initialize to start at offs
                # Further searches start at found position +1
                eidx = offs - 2
                idx  = offs - 1
                while (idx - eidx) % 2 :
                    idx = bytes.index (delimiter, idx + 1)
                    eidx = idx
                    while eidx > 0 and bytes [eidx-1:eidx] == esc :
                        eidx -= 1
                yield bytes [offs:idx]
                offs = idx + 1
            except ValueError :
                yield bytes [offs:]
                break
    # end def iterparts

# end class _Part_Iter

class Edifact_Message (_Part_Iter) :
    """
        An EDIFACT message can start with an una segment.
        This defines the markup characters in use.
        Segments are terminated with the segment terminator
        We get the current una in effect as a parameter.
    >>> m = Edifact_Message (bytes = msg1)
    >>> m.to_bytes () == msg1
    True
    >>> m.check ()
    >>> m = Edifact_Message (bytes = msg2)
    >>> m.to_bytes () == msg2
    True
    >>> m.check ()
    >>> m = Edifact_Message (bytes = msg3)
    >>> m.to_bytes () == msg3
    True
    >>> m.check (skip_segment_check = True)
    """

    def __init__ (self, una = una, bytes = None, *segments) :
        self.una = una
        self.encoding = 'latin-1'
        self.uniq     = ('UNB', 'UNH', 'UNT', 'UNZ', 'MID', 'SDE', 'RDE')
        for u in self.uniq :
            setattr (self, u.lower (), None)
        if bytes :
            self.from_bytes (bytes)
        else :
            self.segments = list (segments)
    # end def __init__

    def append_segment (self, segment) :
        sn = segment.segment_name
        if sn in self.uniq :
            if getattr (self, sn.lower ()) is not None :
                raise ValueError ("Duplicate %s segment" % sn)
            setattr (self, sn.lower (), segment)
        self.segments.append (segment)
    # end def append_segment

    def check (self, skip_segment_check = False) :
        for s in self.segments :
            s.check ()
        uniq = self.uniq
        if skip_segment_check :
            uniq = ('UNB', 'UNH', 'UNT', 'UNZ')
        for u in uniq :
            if getattr (self, u.lower ()) is None :
                raise ValueError ("Missing %s segment" % u)
        unzcr = self.unz.control_ref.control_ref
        unbcr = self.unb.control_ref.control_ref
        if unzcr != unbcr :
            raise ValueError ("Inconsistent UNZ.control_ref vs UNB.control_ref")
        untmsg = self.unt.message_ref.message_ref
        unhmsg = self.unh.message_ref.message_ref
        if untmsg != unhmsg :
            raise ValueError ("Inconsistent UNT.message_ref vs UNH.message_ref")
    # end def check

    def from_bytes (self, bytes) :
        self.segments = []
        offs = 0
        if bytes.startswith (b'UNA') :
            self.una = UNA (bytes [:9])
            offs = 9
            self.append_segment (self.una)
        else :
            self.una = una
        t = self.una.segment_terminator
        for b in self.iterparts (bytes [offs:], t) :
            name = b [:3].decode ('ASCII')
            cls  = Edifact_Segment
            e    = self.encoding
            if name in globals () :
                cls = globals () [name]
            self.append_segment \
                (cls (bytes = b + t, una = self.una, encoding = e))
    # end def from_bytes

    def to_bytes (self) :
        s = b''.join (p.to_bytes () for p in self.segments)
        return s
    # end def to_bytes

    def __str__ (self) :
        r = []
        for s in self.segments :
            r.append (str (s))
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__
    __repr__ = __str__

# end class Edifact_Message

class Engdat_Message (Edifact_Message) :

    """ Simple Engdat_Message with sensible defaults
    >>> dt = datetime.strptime ('2018-02-13T16:11:11', '%Y-%m-%dT%H:%M:%S')
    >>> d = {}
    >>> d ['sender_name']      = 'Z. ulieferer'
    >>> d ['sender_id']        = 'O0013006000F2'
    >>> d ['sender_routing']   = 'sender-routingcode'
    >>> d ['sender_email']     = 'sender@example.com'
    >>> d ['receiver_name']    = 'O. EM'
    >>> d ['receiver_id']      = 'O0013005466F3'
    >>> d ['receiver_routing'] = 'receiver-routingcode'
    >>> d ['receiver_email']   = 'receiver@example.com'
    >>> d ['docno']            = '180213161111XYZZY'
    >>> d ['docdt']            = dt
    >>> d ['dt']               = dt
    >>> em = Engdat_Message (** d)
    >>> em.to_bytes () == msg4
    True
    >>> em.unh.message_id.sub_function_id = ''
    >>> em.to_bytes () == msg4
    True
    """

    def __init__ \
        (self
        , sender_name
        , sender_id
        , sender_routing
        , sender_email
        , receiver_name
        , receiver_id
        , receiver_routing
        , receiver_email
        , docno
        , docdt
        , ref = 'ref'
        , msgref = 'ref'
        , dt = None
        , *args, **kw
        ) :
        self.__super.__init__ (*args, **kw)
        now = dt
        if now is None :
            now = datetime.now ()
        unb = UNB ()
        unb.interchange_sender.id = sender_id
        unb.interchange_recipient.id = receiver_id
        unb.date_and_time.date = now.strftime ('%y%m%d')
        unb.date_and_time.time = now.strftime ('%H%M')
        unb.control_ref.control_ref = ref
        self.append_segment (unb)
        unh = UNH ()
        unh.message_ref.message_ref = msgref
        # create other elements:
        unh.scenario_identification
        self.append_segment (unh)
        mid = MID ()
        mid.document_no.document_no = docno
        mid.date_and_time.date = docdt.strftime ('%y%m%d')
        mid.date_and_time.time = docdt.strftime ('%H%M')
        self.append_segment (mid)
        sde = SDE ()
        sde.sender.party_name = sender_name
        sde.routing.routing = sender_routing
        sde.contact_details_sender.email = sender_email
        self.append_segment (sde)
        rde = RDE ()
        rde.receiver.party_name = receiver_name
        rde.routing.routing = receiver_routing
        rde.contact_details_receiver.email = receiver_email
        self.append_segment (rde)
        # We add one .zip file, if something different is needed this
        # has to be change in the user of this class. Some of these
        # values should probably be in the defaults.
        efc = EFC ()
        efc.file_info.seqno = '2'
        efc.file_format.code = 'ZIP'
        efc.data_code.code = '815' # FIXME
        efc.generating_system.name = 'trackersync'
        efc.file_status.file_status = 'New sync file'
        self.append_segment (efc)
        tot = TOT ()
        tot.quantity.quantity = '2'
        self.append_segment (tot)
        unt = UNT ()
        unt.number_of_segments.segments = str (len (self.segments) + 2)
        unt.message_ref.message_ref = msgref
        self.append_segment (unt)
        unz = UNZ ()
        unz.interchange_count.interchange_count = '1'
        unz.control_ref.control_ref = ref
        self.append_segment (unz)
        self.check ()
    # end def __init__

# end class Engdat_Message

class Edifact_Element (_Part_Iter) :
    """ An edifact data element (elements are delimited by the data
        element separator, usually '+')
    """

    attrs = ( 'encoding', 'una', 'components', 'structure', 'by_name'
            , 'segment', 'parent'
            )
    def __init__ \
        ( self
        , encoding  = 'latin-1'
        , una       = una
        , bytes     = None
        , parent    = None
        , idx       = None
        ) :
        self.encoding   = encoding
        self.una        = una
        self.components = []
        self.by_name    = {}
        self.segment    = None
        self.parent     = parent
        self.structure  = None
        if parent is not None and idx is not None :
            structure = getattr (parent, 'structure', None)
            if structure :
                self.structure = structure [idx]
        if self.structure :
            for k, s in enumerate (self.structure [1]) :
                self.by_name [s [0]] = k
        if bytes :
            self.from_bytes (bytes)
        elif self.structure :
            # Set default values
            for k, s in enumerate (self.structure [1]) :
                if len (s) > 5 :
                    setattr (self, s [0], s [5])
    # end def __init__

    @property
    def name (self) :
        n = "<unnamed>"
        if self.structure :
            n = self.structure [0][0]
        if self.parent :
            return '.'.join ((self.parent.segment_name, n))
        return n
    # end def name

    def append (self, component_text) :
        """ Append component_text to self.components
        """
        self.components.append (component_text)
    # end def append

    def _check (self, idx) :
        s = self.structure [1][idx]
        (n, m, t, l, u) = s [:5]
        cl = len (self.components)
        # Don't check completely empty element
        if cl == 0 :
            return
        if m == 'm' and cl - 1 < idx :
            raise ValueError ("Component %s.%s: Missing" % (self.name, n))
        comp = None
        ccl  = 0
        if idx < cl :
            comp = self.components [idx]
            ccl  = len (comp)
        if comp and t == 'n' and not comp.isdigit () :
            raise ValueError \
                ( "Component %s.%s: got non-numeric value %s"
                % (self.name, n, comp)
                )
        if comp and t == 'a' and not comp.isalpha () :
            raise ValueError \
                ( "Component %s.%s: got non-alpha value %s"
                % (self.name, n, comp)
                )
        if m == 'm' and ccl == 0 :
            raise ValueError \
                ("Component %s.%s: Missing mandatory value" % (self.name, n))
        if (ccl > 0 or m == 'm') and (ccl > u or ccl < l) :
            raise ValueError \
                ( "Component %s.%s: Invalid length %s (expect %s-%s)"
                % (self.name, n, ccl, l, u)
                )
    # end def _check

    def check (self) :
        """ Check against structure, example structure entry:
            ('name', 'c', 'an', 0, 5)
            means we have an alphanumeric field which is optional and
            has maximum length 5.
        """

        empty = True
        if self.structure is not None :
            mandatory = self.structure [0][1] == 'm'
            cl = len (self.components)
            for k, s in enumerate (self.structure [1]) :
                self._check (k)
                if k < cl and self.components [k] :
                    empty = False
            if empty and mandatory :
                raise ValueError \
                    ("Element %s: empty mandatory element" % self.name)
    # end def check

    def from_bytes (self, bytes) :
        offs = 0
        t    = self.una.component_sep
        for b in self.iterparts (bytes [offs:], t) :
            self.append (self.unquote (b).decode (self.encoding))
    # end def from_bytes

    def to_bytes (self) :
        comps = []
        for c in self.components :
            comps.append (self.quote (c.encode (self.encoding)))
        r = self.una.component_sep.join (comps).rstrip (self.una.component_sep)
        return r
    # end def to_bytes

    def quote (self, bytes) :
        """ Add quoting (with release_char)
        >>> x = Edifact_Element (una = una)
        >>> brepr (x.quote (b"+49-40-123-0?'"))
        b"?+49-40-123-0???'"
        """
        # The release_char must be first, otherwise release chars are
        # multiplied
        special = \
            ( self.una.release_char
            , self.una.component_sep
            , self.una.element_sep
            , self.una.segment_terminator
            )
        for k in special :
            bytes = bytes.replace (k, self.una.release_char + k)
        return bytes
    # end def quote

    def unquote (self, bytes) :
        """ Remove quoting (with release_char)
        >>> x = Edifact_Element (una = una)
        >>> brepr (x.unquote (b'?+49-40-123-0'))
        b'+49-40-123-0'
        >>> brepr (x.unquote (b'Abt. ABT-1??'))
        b'Abt. ABT-1?'
        >>> brepr (x.unquote (b"?+49-40-123-0???'"))
        b"+49-40-123-0?'"
        """
        r    = []
        offs = 0
        idx = bytes.find (self.una.release_char, offs)
        while idx >= 0 :
            r.append (bytes [offs:idx])
            r.append (bytes [idx+1:idx+2])
            offs = idx + 2
            idx  = bytes.find (self.una.release_char, offs)
        r.append (bytes [offs:])
        return b''.join (r)
    # end def unquote

    def __getattr__ (self, name) :
        try :
            idx = self.by_name [name]
        except KeyError as e :
            raise AttributeError (e)
        if idx > len (self.components) - 1 :
            return ''
        return self.components [idx]
    # end def __getattr__

    def __setattr__ (self, name, value) :
        if name in self.attrs :
            self.__super.__setattr__ (name, value)
        else :
            try :
                idx = self.by_name [name]
            except KeyError as e :
                raise AttributeError (e)
            for k in range (len (self.components), idx + 1) :
                self.components.append ('')
            self.components [idx] = value
            self._check (idx)
    # end def __setattr__

    def __str__ (self) :
        r = []
        for c in self.components :
            r.append (c)
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__
    __repr__ = __str__

# end class Edifact_Element

class Edifact_Segment (_Part_Iter) :
    """ Implements an EDIFACT segment used in ENGDAT V2
        A segment is prefixed with the (3-letter) record name and
        terminated by the current segment terminator.
    """

    def __init__ (self, encoding = 'latin1', bytes = None, una = una) :
        self.encoding = encoding
        self.una      = una
        self.elements = []
        if bytes is not None :
            self.from_bytes (bytes)
        self.__super.__init__ ()
    # end def __init__

    def check (self) :
        """ Only possible with structure information
        """
        pass
    # end def check

    def to_bytes (self) :
        s = [self.segment_name.encode (self.encoding)]
        for element in self.elements :
            s.append (element.to_bytes ())
        s = self.una.element_sep.join (s)
        s = s.rstrip (self.una.element_sep)
        self.length = len (s) + 1
        return s + self.una.segment_terminator
    # end def to_bytes

    def from_bytes (self, bytes) :
        self.length = len (bytes)
        self.segment_name = bytes [:3].decode (self.encoding)
        assert self.length == 4 or bytes [3:4] == self.una.element_sep
        assert bytes [-1:] == self.una.segment_terminator
        offs = 4
        t = self.una.element_sep
        e = self.encoding
        for b in self.iterparts (bytes [offs:-1], t) :
            l  = len (self.elements)
            el = Edifact_Element \
                (encoding = e, bytes = b, parent = self, idx = l)
            self.elements.append (el)
    # end def from_bytes

    def __length__ (self) :
        return self.length
    # end def __length__

    def __str__ (self) :
        r = []
        r.append (self.segment_name)
        for e in self.elements :
            r.append (str (e))
        return '\n'.join (r)
    # end def __str__
    __unicode__ = __str__
    __repr__ = __str__

# end class Edifact_Segment

class Named_Edifact_Segment (Edifact_Segment) :

    def __init__ (self, *args, **kw) :
        self.segment_name = self.segment_class_name
        self.__super.__init__ (*args, **kw)
        self.by_name = {}
        for k, (ss, se) in enumerate (self.structure) :
            self.by_name [ss [0]] = k
    # end def __init__

    @property
    def segment_class_name (self) :
        return self.__class__.__name__
    # end def segment_class_name

    def check (self) :
        for idx, (ss, se) in enumerate (self.structure) :
            name, m, n = ss
            el = len (self.elements)
            if m == 'm' and el - 1 < idx :
                raise ValueError \
                    ( "Segment %s: Missing: %s"
                    % (self.segment_class_name, name)
                    )
            if idx < el :
                self.elements [idx].check ()
    # end def check

    def __getattr__ (self, name) :
        try :
            idx = self.by_name [name]
        except KeyError as e :
            raise AttributeError (e)
        el = len (self.elements)
        e  = self.encoding
        if idx >= el :
            for i in range (el, idx + 1) :
                el = Edifact_Element \
                    (encoding = e, parent = self, idx = i)
                self.elements.append (el)
        return self.elements [idx]
    # end def __getattr__

# end class Named_Edifact_Segment

class UNB (Named_Edifact_Segment) :
    structure = \
        ( ( ('syntax_identifier', 'm', 1)
          , ( ('syntax_id',       'm', 'a',  4, 4, 'UNOC')
            , ('version',         'm', 'an', 1, 1, '1')
            , ('dir_version',     'c', 'an', 0, 6)
            , ('encoding',        'c', 'an', 0, 3)
            )
          )
        , ( ('interchange_sender', 'm', 1)
          , ( ('id',              'm', 'an', 0, 35)
            , ('code_qualifier',  'c', 'an', 0, 4, 'OD')
            , ('internal_id',     'c', 'an', 0, 35)
            , ('internal_sub_id', 'c', 'an', 0, 35)
            )
          )
        , ( ('interchange_recipient', 'm', 1)
          , ( ('id',              'm', 'an', 0, 35)
            , ('code_qualifier',  'c', 'an', 0, 4, 'OD')
            , ('internal_id',     'c', 'an', 0, 35)
            , ('internal_sub_id', 'c', 'an', 0, 35)
            )
          )
        , ( ('date_and_time', 'm', 1)
          , ( ('date',            'm', 'n',  6, 8)
            , ('time',            'm', 'n',  4, 4)
            )
          )
        , ( ('control_ref', 'm', 1)
          , ( ('control_ref',     'm', 'an', 0, 14)
            ,
            )
          )
        , ( ('reference_password', 'c', 1)
          , ( ('ref_pw',          'm', 'an', 0, 14)
            , ('qualifier',       'c', 'an', 2, 2)
            )
          )
        , ( ('app_ref', 'c', 1)
          , ( ('app_ref',         'm', 'an', 0, 14)
            ,
            )
          )
        , ( ('prio_code', 'c', 1)
          , ( ('prio_code',       'm', 'a',  1, 1)
            ,
            )
          )
        , ( ('ack_request', 'c', 1)
          , ( ('ack_request',     'm', 'n',  1, 1)
            ,
            )
          )
        , ( ('agreement_id', 'c', 1)
          , ( ('agreement_id',    'm', 'an', 0, 35)
            ,
            )
          )
        , ( ('test_indicator', 'c', 1)
          , ( ('test_indicator',  'm', 'n',  1, 1)
            ,
            )
          )
        )
# end class UNB

class UNH (Named_Edifact_Segment) :
    structure = \
        ( ( ('message_ref', 'm', 1)
          , ( ('message_ref',     'm', 'an', 0, 14)
            ,
            )
          )
        , ( ('message_id', 'm', 1)
          , ( ('type',            'm', 'an', 0, 6, 'ENGDAT')
            , ('version',         'm', 'an', 0, 3, '001')
            , ('release',         'c', 'an', 0, 3)
            , ('agency',          'c', 'an', 0, 3, 'OD') # 79?
            , ('assoc_code',      'c', 'an', 0, 6)
            , ('code_version',    'c', 'an', 0, 6)
            , ('sub_function_id', 'c', 'an', 0, 6)
            )
          )
        , ( ('access_ref', 'c', 1)
          , ( ('access_ref',      'm', 'an', 0, 35)
            ,
            )
          )
        , ( ('transfer_status', 'c', 1)
          , ( ('sequence',        'm', 'n',  0, 2)
            , ('first_and_last',  'c', 'a',  1, 1)
            )
          )
        , ( ('message_subset_id', 'c', 1)
          , ( ('id',              'm', 'an', 0, 14)
            , ('version',         'c', 'an', 0, 3)
            , ('release',         'c', 'an', 0, 3)
            , ('agency',          'c', 'an', 0, 3)
            )
          )
        , ( ('message_implementation_guideline', 'c', 1)
          , ( ('id',              'm', 'an', 0, 14)
            , ('version',         'c', 'an', 0, 3)
            , ('release',         'c', 'an', 0, 3)
            , ('agency',          'c', 'an', 0, 3)
            )
          )
        , ( ('scenario_identification', 'c', 1)
          , ( ('id',              'm', 'an', 0, 14)
            , ('version',         'c', 'an', 0, 3)
            , ('release',         'c', 'an', 0, 3)
            , ('agency',          'c', 'an', 0, 3)
            )
          )
        )
# end class UNH

class UNT (Named_Edifact_Segment) :
    structure = \
        ( ( ('number_of_segments', 'm', 1)
          , ( ('segments',        'm', 'n',  0, 10)
            ,
            )
          )
        # Must be same as corresponding value in UNH
        , ( ('message_ref', 'm', 1)
          , ( ('message_ref',     'm', 'an', 0, 14)
            ,
            )
          )
        )
# end class UNT

class UNZ (Named_Edifact_Segment) :
    structure = \
        ( ( ('interchange_count', 'm', 1)
          , ( ('interchange_count', 'm', 'n',  0, 6)
            ,
            )
          )
        # Must be same as corresponding value in UNB
        , ( ('control_ref', 'm', 1)
          , ( ('control_ref',       'm', 'an', 0, 14)
            ,
            )
          )
        )
# end class UNZ

class MID (Named_Edifact_Segment) :
    structure = \
        ( ( ('document_no', 'm', 1)
          , ( ('document_no',       'm', 'an', 0, 17)
            ,
            )
          )
        , ( ('date_and_time', 'm', 1)
          , ( ('date',              'm', 'n',  6, 6)
            , ('time',              'c', 'n',  4, 4)
            )
          )
        , ( ('auth', 'c', 1)
          , ( ('control_ref',       'm', 'an', 0, 35)
            ,
            )
          )
        )
# end class MID

class SDE (Named_Edifact_Segment) :
    structure = \
        ( ( ('sender', 'm', 1)
          , ( ('sender',            'c', 'an', 0, 20)
            , ('party_name',        'c', 'an', 0, 35)
            , ('addr1',             'c', 'an', 0, 35)
            , ('addr2',             'c', 'an', 0, 35)
            , ('addr3',             'c', 'an', 0, 35)
            , ('addr4',             'c', 'an', 0, 35)
            , ('internal_id',       'c', 'an', 0, 17)
            )
          )
        , ( ('country_contact', 'c', 1)
          , ( ('country',           'm', 'a',  2, 2)
            ,
            )
          )
        , ( ('routing', 'c', 1)
          , ( ('routing',           'm', 'an', 0, 35)
            ,
            )
          )
        , ( ('contact_details_sender', 'c', 1)
          , ( ('department1',       'c', 'an', 0, 35)
            , ('department2',       'c', 'an', 0, 35)
            , ('telephone',         'c', 'an', 0, 17)
            , ('extension',         'c', 'an', 0, 17)
            , ('telex',             'c', 'an', 0, 17)
            , ('fax',               'c', 'an', 0, 17)
            , ('teletex',           'c', 'an', 0, 17)
            , ('email',             'c', 'an', 0, 70)
            )
          )
        , ( ('tech_contact', 'c', 1)
          , ( ('party_name',        'c', 'an', 0, 35)
            , ('addr1',             'c', 'an', 0, 35)
            , ('addr2',             'c', 'an', 0, 35)
            , ('addr3',             'c', 'an', 0, 35)
            , ('addr4',             'c', 'an', 0, 35)
            , ('internal_id',       'c', 'an', 0, 17)
            )
          )
        , ( ('country_tech', 'c', 1)
          , ( ('country',           'm', 'a',  2, 2)
            ,
            )
          )
        , ( ('contact_details_tech', 'c', 1)
          , ( ('department1',       'c', 'an', 0, 35)
            , ('department2',       'c', 'an', 0, 35)
            , ('telephone',         'c', 'an', 0, 17)
            , ('extension',         'c', 'an', 0, 17)
            , ('telex',             'c', 'an', 0, 17)
            , ('fax',               'c', 'an', 0, 17)
            , ('teletex',           'c', 'an', 0, 17)
            , ('email',             'c', 'an', 0, 70)
            )
          )
        )
# end class SDE

class RDE (Named_Edifact_Segment) :
    structure = \
        ( ( ('receiver', 'm', 1)
          , ( ('receiver',          'c', 'an', 0, 20)
            , ('party_name',        'c', 'an', 0, 35)
            , ('addr1',             'c', 'an', 0, 35)
            , ('addr2',             'c', 'an', 0, 35)
            , ('addr3',             'c', 'an', 0, 35)
            , ('addr4',             'c', 'an', 0, 35)
            , ('internal_id',       'c', 'an', 0, 17)
            )
          )
        , ( ('country_contact', 'c', 1)
          , ( ('country',           'm', 'a',  2, 2)
            ,
            )
          )
        , ( ('routing', 'c', 1)
          , ( ('routing',           'm', 'an', 0, 35)
            ,
            )
          )
        , ( ('contact_details_receiver', 'c', 1)
          , ( ('department1',       'c', 'an', 0, 35)
            , ('department2',       'c', 'an', 0, 35)
            , ('telephone',         'c', 'an', 0, 17)
            , ('extension',         'c', 'an', 0, 17)
            , ('telex',             'c', 'an', 0, 17)
            , ('fax',               'c', 'an', 0, 17)
            , ('teletex',           'c', 'an', 0, 17)
            , ('email',             'c', 'an', 0, 70)
            )
          )
        , ( ('tech_contact', 'c', 1)
          , ( ('party_name',        'c', 'an', 0, 35)
            , ('addr1',             'c', 'an', 0, 35)
            , ('addr2',             'c', 'an', 0, 35)
            , ('addr3',             'c', 'an', 0, 35)
            , ('addr4',             'c', 'an', 0, 35)
            , ('internal_id',       'c', 'an', 0, 17)
            )
          )
        , ( ('country_tech', 'c', 1)
          , ( ('country',           'm', 'a',  2, 2)
            ,
            )
          )
        , ( ('contact_details_tech', 'c', 1)
          , ( ('department1',       'c', 'an', 0, 35)
            , ('department2',       'c', 'an', 0, 35)
            , ('telephone',         'c', 'an', 0, 17)
            , ('extension',         'c', 'an', 0, 17)
            , ('telex',             'c', 'an', 0, 17)
            , ('fax',               'c', 'an', 0, 17)
            , ('teletex',           'c', 'an', 0, 17)
            , ('email',             'c', 'an', 0, 70)
            )
          )
        )
# end class RDE

class EFC (Named_Edifact_Segment) :
    structure = \
        ( ( ('file_info', 'm', 1)
          , ( ('seqno',             'm', 'n',  0, 3)
            , ('filename',          'c', 'an', 0, 35)
            )
          )
        , ( ('file_format', 'm', 1)
          , ( ('code',             'c', 'an', 0, 3)
            , ('file_format',      'c', 'an', 0, 35)
            , ('version',          'c', 'an', 0, 10)
            )
          )
        , ( ('data_code', 'm', 1)
          , ( ('code',             'c', 'an', 0, 3)
            , ('data_code',        'c', 'an', 0, 35)
            )
          )
        , ( ('generating_system', 'm', 1)
          , ( ('name',             'c', 'an', 0, 35)
            , ('version',          'c', 'an', 0, 35)
            , ('command',          'c', 'an', 0, 35)
            )
          )
        , ( ('file_status', 'm', 1)
          , ( ('code',             'c', 'an', 0, 3)
            , ('file_status',      'c', 'an', 0, 35)
            )
          )
        , ( ('engineering_department', 'c', 1)
          , ( ('department',       'c', 'an', 0, 35)
            ,
            )
          )
        , ( ('data_type', 'c', 1)
          , ( ('type1',            'm', 'an', 0, 35)
            , ('type2',            'c', 'an', 0, 35)
            , ('type3',            'c', 'an', 0, 35)
            , ('type4',            'c', 'an', 0, 35)
            )
          )
        , ( ('compression', 'c', 1)
          , ( ('compression',      'c', 'an', 0, 35)
            ,
            )
          )
        )
# end class EFC

class TOT (Named_Edifact_Segment) :
    structure = \
        ( ( ('quantity', 'm', 1)
          , ( ('quantity',          'm', 'n',  0, 15)
            , ('unit',              'c', 'an', 0, 3)
            )
          )
        # Wird in ENGDAT nicht verwendet
        , ( ('amount', 'c', 1)
          , ( ('amount',            'c', 'n',  0, 0)
            , ('currency',          'c', 'an', 0, 0)
            )
          )
        )
# end class TOT

if __name__ == '__main__' :
    m = Edifact_Message (bytes = msg1)
    #print (len (m.segments))
    #print (m)
    #for k in m.segments :
    #    print (repr (k.to_bytes ()))

    #print (msg1)
    #print (m.to_bytes ())

    assert m.to_bytes () == msg1
    m.check ()
    m = Edifact_Message (bytes = msg2)
    assert m.to_bytes () == msg2
    m.check ()
    m = Edifact_Message (bytes = msg3)
    m.to_bytes () == msg3
    m.check ()
