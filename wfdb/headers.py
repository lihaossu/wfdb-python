import numpy as np
import re
import os
import sys
import requests
from collections import OrderedDict



        
# The information contained in a WFDB header file
WFDBfields = {
        'recordname': [],
        'nseg': [],
        'nsig': [],
        'fs': [],
        'siglen': [],
        'basetime': [],
        'basedate': [],
    
        'filename': [],
        'fmt': [],
        'sampsperframe': [],
        'skew': [],
        'byteoffset': [],
        'gain': [],
        'units': [],
        'baseline': [],
        'initvalue': [],
        'signame': [],
        'nsampseg': [],
        'comments': []}

# A field of the WFDB header file
class WFDBfield():
    
    def __init__(self, speclist):
        # Name
        self.name = speclist[0] 
        # Data types the field can take
        self.allowedtypes = speclist[1]
        # The text delimiter that preceeds the field
        self.delimiter = speclist[2]
        # The required/dependent field which must also be present
        self.dependency = speclist[3]
        # Whether the field is mandatory specified by the WFDB guidelines
        self.is_req = speclist[4]
        # Whether the field is mandatory for writing (extra rules enforced by this library).
        # Being required for writing is not the same as the user having to specify. There are defaults. 
        self.write_req = speclist[5]
        # The default value to write
        self.write_default = speclist[6]
        
# The fields that may be contained in a WFDB header file. https://www.physionet.org/physiotools/wag/header-5.htm
# name, allowedtypes, delimiter, field_req, is_req, write_req
WFDBfields = [
    
    # record specification fields
    OrderedDict([('recordname', WFDBfield(['recordname', [str], '', None, True, True, None])),
                 ('nseg', WFDBfield(['nseg', [int], '/', 'recordname', False, False, None])),
                 ('nsig', WFDBfield(['nsig', [int], ' ', 'recordname', True, True, None])),
                 ('fs', WFDBfield(['fs', [int, float], ' ', 'nsig', False, True, None])),
                 ('counterfreq', WFDBfield(['counterfreq', [int, float], '/', 'fs', False, False, None])),
                 ('basecounter', WFDBfield(['basecounter', [int, float], '(', 'counterfreq', False, False, None])),
                 ('siglen', WFDBfield(['siglen', [int], ' ', 'fs', False, True, None])),
                 ('basetime', WFDBfield(['basetime', [str], ' ', 'siglen', False, False, None])),
                 ('basedate', WFDBfield(['basedate', [str], ' ', 'basetime', False, False, None]))]),
    
    # signal specification fields
    OrderedDict([('filename', WFDBfield(['filename', [str], '', None, True, True, None])),
                 ('fmt', WFDBfield(['fmt', [int, str], ' ', 'filename', True, True, None])),
                 ('sampsperframe', WFDBfield(['sampsperframe', [int], 'x', 'fmt', False, False])),
                 ('skew', WFDBfield(['skew', [int], ':', 'fmt', False, False])),
                 ('byteoffset', WFDBfield(['byteoffset', [int], '+', 'fmt', False, False])),
                 ('adcgain', WFDBfield(['adcgain', [int], ' ', 'fmt', False, False])),
                 ('baseline', WFDBfield(['baseline', [int], '(', 'adcgain', False, False])),
                 ('units', WFDBfield(['units', [str], '/', 'adcgain', False, False])),
                 ('adcres', WFDBfield(['adcres', [int], ' ', 'adcgain', False, False])),
                 ('adczero', WFDBfield(['adczero', [int], ' ', 'adcres', False, False])),
                 ('initvalue', WFDBfield(['initvalue', [int], ' ', 'adczero', False, False])),
                 ('checksum', WFDBfield(['checksum', [int], ' ', 'initvalue', False, False])),
                 ('blocksize', WFDBfield(['blocksize', [int], ' ', 'checksum', False, False])),
                 ('signame', WFDBfield(['signame', [str], ' ', 'blocksize', False, False]))]),
    
    # segment specification fields
    OrderedDict([('segname', WFDBfield(['segname', [str], '', None, True, True])),
                 ('seglen', WFDBfield(['seglen', [int], ' ', 'segname', True, True]))]),
    
    # comment fields
    OrderedDict([('comments', WFDBfield(['comments', [int], '', None, False, False]))])
]
# Should specify limits too...     


# The useful summary information contained in a wfdb record.
# Note: Not a direct subset of WFDBfields. 
infofields = [['recordname',
               'nseg',
               'nsig',
               'fs',
               'siglen',
               'basetime',
               'basedate'],  
              
              ['filename',
               'maxresolution',
               'sampsperframe',
               'units',
               'signame'],
              
              ['segname',
               'seglen'],
              
              'comments']

# The required explicit fields contained in all WFDB headers. 
req_read_fields = [['recordname', 'nsig'], ['filename', 'fmt'], ['segname', 'seglen']]

# The required input fields used to write WFDB headers. This python library enforces explicit fs and siglen. 
req_write_fields = [['recordname', 'nsig', 'fs', 'siglen'], ['filename', 'fmt'], ['segname', 'seglen']]



# Return a dictionary with the essential keys + empty values for wrsamp. 
def getwritefields(base=1):
    return 0
              
# Write a wfdb header file. 
# When setsigreqs = 1, missing signal specification dependencies will be set. When it is 0, they must be explicitly set. 
def wrheader(inputfields, targetdir=os.cwd(), setsigreqs=1):
    
    # Check the header keys
    keycheckedfields = _checkheaderkeys(inputfields, setsigreqs)
    
    # Check the header values
    valuecheckedfields = checkheadervalues(keycheckedfields, setsigreqs)

    # Write the output header file
    _writeheaderfile(finalfields)
                        
              
# Check that the dictionary of fields contains valid keys according to WFDB standards.
def _checkheaderkeys(inputfields, setsigreqs):
    
    # Make sure the input field is a dictionary.
    if type(inputfields)!=dict:
        sys.exit("'fields' must be a dictionary")

    # Check for invalid dictionary keys.
    for inputfield in inputfields:
        if inputfield not in list(WFDBfields[0])+list(WFDBfields[1])+list(WFDBfields[3]):
            sys.exit('Invalid input key: '+inputfield)

    # Check for mandatory input fields
    for f in WFDBfields[0]:
        if (WFDBfields[0][f].is_req) and (f not in inputfields):
            sys.exit('Missing required input key: '+f)
    if inputfields['nsig']>0:
        for f in WFDBfields[0]:
            if (WFDBfields[0][f].is_req) and (f not in inputfields):
                sys.exit('Missing required input key: '+f)
    
    # Check that fields have their dependent fields present
    keycheckedfields = _checkfieldreqs(inputfields, setsigreqs)
    
    return keycheckedfields

    
# Check that each signal specification field's dependent field is also present.
# Helper function to _checkheaderkeys
def _checkfieldreqs(fields, setsigreqs):
   
    # The required preceding field for each header field. Must check keys in reverse order.
    rec_dependencies = OrderedDict(reversed(list(WFDBfields[0].items())))
    sig_dependencies = OrderedDict(reversed(list(WFDBfields[1].items())))
    
    # Add dependent keys if option is specified.
    if setsigreqs:
        for d in rec_dependencies:
            if (d in fields) and (rec_dependencies[d].dependency not in fields):
                fields[rec_dependencies[d].dependency]=[]
        for d in sig_dependencies:
            if (d in fields) and (sig_dependencies[d].dependency not in fields):
                fields[sig_dependencies[d].dependency]=[]
    
    # Check for missing dependent fields        
    for d in rec_dependencies:
        if (d in fields) and (rec_dependencies[d] not in fields):
            sys.exit('Missing required signal specification field: '+rec_dependencies[d]+' for field: '+d)
    for d in sig_dependencies:
        if (d in fields) and (sig_dependencies[d] not in fields):
            sys.exit('Missing required signal specification field: '+sig_dependencies[d]+' for field: '+d)
            
    return fields
    
    
    
# Check the validity of each header value. Remember that gain crap...     
def _checkheadervalues(fields, setsigreqs):
    
    # At this point, all the required keys should be present. Now need to check their values. 
    
    
    # [0, 1, 3] are record, signal, and comment lines. 
    
    # Check the mandatory explicit fields
    for i in [0, 1, 3]:
        items=WFDBfields[i]
        
        for i in items:
            if items[i].write_req:
                
        
    
    
    
    
    
   
    
    # Fill missing values to defaults if option is specified.
    # Only fill fields where write_req==0. Users must explicitly set fields where write_req==1
    if setsigreqs:
        
        rec_ = 
        sig
        
        
        for i in WFDBfields[0]:
            

        
        
    # Check the content of the fields
    nsig = fields['nsig']
    
    # MAKE SURE FILES names are consecutive and not interleaved. 
    
    
    # Check the size of signal specification fields.
    if field in WFDBfields[1]:
        if np.size(value)==1 
            # Expand 
        elif np.size(value)!=nsig:
            sys.exit("The ")
    
    
    return fields
    
    
def _writeheaderfile(fields):
    
    f=open(fields['recordname']+'.hea','w')
    
    
    
    f.close()
    
    
    
    
    
# Write a multi-segment wfdb header file. 
def wrmultiheader:
    
    # check that each signal component has the same fs and the correct number of signals. 
    
    # Write the header file
    
    return 1
    


    
    
# For reading WFDB header files
def rdheader(recordname): 

    # To do: Allow exponential input format for some fields

    # Output dictionary
    fields=WFDBfields
    
    # filename stores file names for both multi and single segment headers.
    # nsampseg is only for multi-segment


    # RECORD LINE fields (o means optional, delimiter is space or tab unless specified):
    # record name, nsegments (o, delim=/), nsignals, fs (o), counter freq (o, delim=/, needs fs),
    # base counter (o, delim=(), needs counter freq), siglen (o, needs fs), base time (o),
    # base date (o needs base time).

    # Regexp object for record line
    rxRECORD = re.compile(
        ''.join(
            [
                "(?P<name>[\w]+)/?(?P<nseg>\d*)[ \t]+",
                "(?P<nsig>\d+)[ \t]*",
                "(?P<fs>\d*\.?\d*)/*(?P<counterfs>\d*\.?\d*)\(?(?P<basecounter>\d*\.?\d*)\)?[ \t]*",
                "(?P<siglen>\d*)[ \t]*",
                "(?P<basetime>\d*:?\d{,2}:?\d{,2}\.?\d*)[ \t]*",
                "(?P<basedate>\d{,2}/?\d{,2}/?\d{,4})"]))
    # Watch out for potential floats: fs (and also exponent notation...),
    # counterfs, basecounter

    # SIGNAL LINE fields (o means optional, delimiter is space or tab unless specified):
    # file name, format, samplesperframe(o, delim=x), skew(o, delim=:), byteoffset(o,delim=+),
    # ADCgain(o), baseline(o, delim=(), requires ADCgain), units(o, delim=/, requires baseline),
    # ADCres(o, requires ADCgain), ADCzero(o, requires ADCres), initialvalue(o, requires ADCzero),
    # checksum(o, requires initialvalue), blocksize(o, requires checksum),
    # signame(o, requires block)

    # Regexp object for signal lines. Consider flexible filenames, and also ~
    rxSIGNAL = re.compile(
        ''.join(
            [
                "(?P<filename>[\w]*\.?[\w]*~?)[ \t]+(?P<format>\d+)x?"
                "(?P<sampsperframe>\d*):?(?P<skew>\d*)\+?(?P<byteoffset>\d*)[ \t]*",
                "(?P<ADCgain>-?\d*\.?\d*e?[\+-]?\d*)\(?(?P<baseline>-?\d*)\)?/?(?P<units>[\w\^/-]*)[ \t]*",
                "(?P<ADCres>\d*)[ \t]*(?P<ADCzero>-?\d*)[ \t]*(?P<initialvalue>-?\d*)[ \t]*",
                "(?P<checksum>-?\d*)[ \t]*(?P<blocksize>\d*)[ \t]*(?P<signame>[\S]*)"]))

    # Units characters: letters, numbers, /, ^, -,
    # Watch out for potentially negative fields: baseline, ADCzero, initialvalue, checksum,
    # Watch out for potential float: ADCgain.

    # Read the header file and get the comment and non-comment lines
    headerlines, commentlines = _getheaderlines(recordname)

    # Get record line parameters
    (_, nseg, nsig, fs, counterfs, basecounter, siglen,
    basetime, basedate) = rxRECORD.findall(headerlines[0])[0]

    # These fields are either mandatory or set to defaults.
    if not nseg:
        nseg = '1'
    if not fs:
        fs = '250'

    fields['nseg'] = int(nseg)
    fields['fs'] = float(fs)
    fields['nsig'] = int(nsig)
    fields['recordname'] = name

    # These fields might by empty
    if siglen:
        fields['siglen'] = int(siglen)
    fields['basetime'] = basetime
    fields['basedate'] = basedate


    # Signal or Segment line paramters
    # Multi segment header - Process segment spec lines in current master
    # header.
    if int(nseg) > 1:
        for i in range(0, int(nseg)):
            (filename, nsampseg) = re.findall(
                '(?P<filename>\w*~?)[ \t]+(?P<nsampseg>\d+)', headerlines[i + 1])[0]
            fields["filename"].append(filename)
            fields["nsampseg"].append(int(nsampseg))
    # Single segment header - Process signal spec lines in regular header.
    else:
        for i in range(0, int(nsig)):  # will not run if nsignals=0
            # get signal line parameters
            (filename,
            fmt,
            sampsperframe,
            skew,
            byteoffset,
            adcgain,
            baseline,
            units,
            adcres,
            adczero,
            initvalue,
            checksum,
            blocksize,
            signame) = rxSIGNAL.findall(headerlines[i + 1])[0]
            
            # Setting defaults
            if not sampsperframe:
                # Setting strings here so we can always convert strings case
                # below.
                sampsperframe = '1'
            if not skew:
                skew = '0'
            if not byteoffset:
                byteoffset = '0'
            if not adcgain:
                adcgain = '200'
            if not baseline:
                if not adczero:
                    baseline = '0'
                else:
                    baseline = adczero  # missing baseline actually takes adczero value if present
            if not units:
                units = 'mV'
            if not initvalue:
                initvalue = '0'
            if not signame:
                signame = "ch" + str(i + 1)
            if not initvalue:
                initvalue = '0'

            fields["filename"].append(filename)
            fields["fmt"].append(fmt)
            fields["sampsperframe"].append(int(sampsperframe))
            fields["skew"].append(int(skew))
            fields['byteoffset'].append(int(byteoffset))
            fields["gain"].append(float(adcgain))
            fields["baseline"].append(int(baseline))
            fields["units"].append(units)
            fields["initvalue"].append(int(initvalue))
            fields["signame"].append(signame)

    for comment in commentlines:
        fields["comments"].append(comment.strip('\s#'))

    return fields


# Read header file to get comment and non-comment lines
def _getheaderlines(recordname):
    with open(recordname + ".hea", 'r') as fp:
        headerlines = []  # Store record line followed by the signal lines if any
        commentlines = []  # Comments
        for line in fp:
            line = line.strip()
            if line.startswith('#'):  # comment line
                commentlines.append(line)
            elif line:  # Non-empty non-comment line = header line.
                ci = line.find('#')
                if ci > 0:
                    headerlines.append(line[:ci])  # header line
                    # comment on same line as header line
                    commentlines.append(line[ci:])
                else:
                    headerlines.append(line)
    return headerlines, commentlines


# Create a multi-segment header file
def wrmultisegheader():
    