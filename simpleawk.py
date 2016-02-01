from __future__ import print_function
import re
import string
import sys
import os
import argparse

class BasicAwk(object):
    def __init__(self, files, FS=None, OFS=None,
                 RS=None, ORS=None):
       self.FS = FS
       if OFS is None:
           self.OFS = ' '
       else:
           self.OFS = OFS
       if ORS is None:
           self.ORS = '\n'
       else:
           self.ORS = ORS
       self.FILES = files
       self.COMPILED_PATTERNS = {}
       self.IGNORE_CASE = False

    def _get_files(self):
        glob_files = self.FILES
        files = []
        if self.GLOB:
            for g in glob_files:
                for f in glob.glob(g):
                    files.append(f)
        else:
            files = glob_files
        filelist = []
        for f in files:
            if os.path.isdir(f):
                if self.RECURSIVE:
                    filelist += self.matching_files(
                        f, self.INCLUDE_PATTERN,
                        self.EXCLUDE_PATERN)
            else:
                filelist.append(f)
        return filelist


    def matching_files(
            self, directory, include_pattern=None, exclude_pattern=None):
        fnlist = []
        for dirpath, dirs, files in os.walk(directory):
            for filename in files:
                fname = os.path.join(dirpath, filename)
                to_include = True
                if exclude_pattern:
                    if fnmatch.fnmatch(fname, exclude_pattern):
                        to_include = False
                if include_pattern and to_include:
                    if not fnmatch.fnmatch(fname, include_pattern):
                        to_include = False
                if to_include:
                    fnlist.append(fname)
        return fnlist


    def convert_type(self, x, index=None):
        if self.FIELDTYPES and index:
            return self.FIELDTYPES[i](x)
        if x.isdigit():
            return int(x)
        else:
            try:
                return float(x)
            except ValueError:
                return x

    def split_record(self, rec_string):
        if self.FS:
            rec_tuple = [self.convert_type(
                field, i) for i, field in enumerate(re.split(
                self.FS, rec_string))]
        else:
            if self.FIELDWIDTHS:
                fieldwidths = [int(i) for i in self.FIELDWIDTHS.split()]
                rec_tuple = [None] * len(fieldwidths)
                cum_width = 0
                prev_cum_width = 0
                for i, width in enumerate(fieldwidths):
                    prev_cum_width = cum_width
                    cum_width += width
                    rec_tuple[i] = self.convert_type(
                        rec_tuple[prev_cum_width:cum_width], i)
            else:
                rec_tuple = [self.convert_type(
                    field, i) for i, field in enumerate(
                    rec_string.split())]
        return rec_tuple


    def printf(self, *args, **kwargs):
        if len(args) == 0:
            if kwargs:
                kwargs.update(sep=self.OFS, end=self.ORS)
                print(*self.S, **kwargs)
            else:
                print(*self.S, sep=self.OFS, end=self.ORS)
        elif len(args) == 1:
            # raise error if first arg not string
            print(args[0].format(*self.S), **kwargs)
        else:
            # raise error if first arg not string
            print(args[0].format(*args[1:]), **kwargs)

    def compile_pattern(self, pattern):
        if pattern in self.COMPILED_PATTERNS:
            cpattern = self.COMPILED_PATTERNS[pattern]
        else:
            flags = 0
            if self.IGNORE_CASE:
                    flags |= re.IGNORECASE
            cpattern = re.compile(pattern, flags=flags)
            self.COMPILED_PATTERNS[pattern] = cpattern
        return cpattern

    def match(self, pattern, text_string=None):
        cpattern = self.compile_pattern(pattern)
        if not text_string:
            text_string = self.SS
        m = re.search(cpattern, text_string)
        if m:
            sp = m.span()
            self.RSTART, self.RLENGTH = sp[0], sp[1]-sp[0]
        else:
            self.RSTART, self.RLENGTH = 0, -1
        return m

    def sub(self, pattern, repl, text_string=None, count=0):
        cpattern = self.compile_pattern(pattern)
        if not text_string:
            text_string = self.SS
        return re.sub(cpattern, repl, text_string, count)

    def subn(self, pattern, repl, text_string=None, count=0):
        cpattern = self.compile_pattern(pattern)
        if not text_string:
            text_string = self.SS
        return re.subn(cpattern, repl, text_string, count)

    def process(self):
        # BEGIN code block
        NR = 0
        for FILEINDEX, FILENAME in enumerate(self.FILES):
            FNR = 0
            fp = open(FILENAME)
            for SS in fp:
                NR += 1
                FNR += 1
                if self.FS:
                    S = SS.rstrip().split(self.FS)
                else:
                    S = SS.split()
                NF = len(S)
                # ACTION code block
                if re.search('f', SS):
                    print(SS, end='')
            fp.close()
        # END code block

    def blankline_record_iterator(self):
        blk_iterator  = BlanklineRecordIterator(
            self).multiline_record_iterator()
        for rec_tuple in blk_iterator:
            yield rec_tuple

    def multiline_rs_marker_record_iterator(self):
        mr_iterator  = MultilineRSMarkerRecordIterator(
            self).multiline_record_iterator()
        for rec_tuple in mr_iterator:
            yield rec_tuple

class MultilineRecordIterator(object):
    def __init__(self, pynawkobj=None):
        self.PYNAWKOBJ = pynawkobj
        self.LINE_ITERATOR = self.PYNAWKOBJ.LINE_ITERATOR
        self.IS_FIRSTLINE = self.PYNAWKOBJ.IS_FIRSTLINE
        self.FILEINDEX = self.PYNAWKOBJ.FILEINDEX
        self.PENDING_LINES = None
        self.PREV_PENDING_LINES = []
        self.PENDING_RECORDS = []

    def build_rec_tuple(self, lines):
        return self.PYNAWKOBJ.build_rec_tuple("".join(lines))

    def match_line(self, line):
        # single record iterator
        self.PENDING_RECORDS = [self.build_rec_tuple([line])]
        return True

    def append_to_pending_lines(self, line):
        self.PENDING_LINES.append(line)

    def multiline_record_iterator(self):
        for line in self.LINE_ITERATOR:
            if self.PENDING_LINES is None:
                self.PENDING_LINES = []
            if self.FILEINDEX and self.FNR == 1:
                self.PYNAWKOBJ.RT = ''
                rec_tuple = self.build_rec_tuple(self.PENDING_LINES)
                self.PENDING_LINES = []
                yield rec_tuple
            if self.match_line(line):
                for rec_tuple in self.PENDING_RECORDS:
                    self.PYNAWKOBJ.RT = rec_tuple[1]
                    yield rec_tuple[0]
            else:
                self.append_to_pending_lines(line)
        if self.PENDING_LINES is not None:
            self.PYNAWKOBJ.RT = ''
            yield self.build_rec_tuple(self.PENDING_LINES)

class RSMarkerRecordIterator(MultilineRecordIterator):
    # Assumption: RS pattern does not contain newline
    # - May match newline  at the end
    def __init__(self, pynawkobj=None):
        super(RSMarkerRecordIterator, self).__init__(pynawkobj)
        self.PATTERN = self.PYNAWKOBJ.RS

    def match_line(self, line):
        mr, reminder = self.PYNAWKOBJ.split_with_splitmatchfields(
           self.PATTERN, line)
        if len(mr) == 0:
            return False
        else:
            rec, rt = mr[0]
            self.PENDING_RECORDS = [(self.build_rec_tuple(
                 self.PENDING_LINES + [rec]), rt)]
            for rec, rt in mr[1:]:
                self.PENDING_RECORDS.append((self.build_rec_tuple([rec]), rt))
            self.PENDING_LINES = [reminder]
            return True

class BlanklineRecordIterator(MultilineRecordIterator):
    def __init__(self, pynawkobj=None, pattern=r"^[ \r\t]*\n"):
        super(BlanklineRecordIterator, self).__init__(pynawkobj)
        self.NB = 0  # number of blanklines
        self.PATTERN = pattern

    def match_line(self, line):
        if self.PYNAWKOBJ.match(self.PATTERN, line):
            if (self.NB == 0):
                self.PREV_PENDING_LINES = self.PENDING_LINES
                self.PENDING_LINES = []
            self.NB += 1
            return False
        else:
            if self.NB > 0:
                self.PENDING_RECORDS = [(self.build_rec_tuple(
                    self.PREV_PENDING_LINES),
                    "".join(self.PENDING_LINES))]
                self.PREV_PENDING_LINES = []
                self.PENDING_LINES = [line]
                self.NB = 0
                return True
            return False

class PynAwkOnlineGenerate(object):
    def __init__(self):
        self.class_template = string.Template('''\
class PynAwk(BasicAwk):
    def __init__(self, files, FS=None, OFS=None,
                 RS=None, ORS=None):
        self.FS = options.FS
        self.FILES = options.FILES
        super(PynAwk, self).__init__(options.FILES,
            FS=options.FS)

    def process(self):
        # BEGIN code block starts
        $BEGIN
        # BEGIN code block ends
        FS = self.FS
        OFS = ' '
        self.OFS = OFS if OFS is not None else " "
        NR = 0
        for FILEINDEX, FILENAME in enumerate(self.FILES):
            FNR = 0
            fp = open(FILENAME)
            for SS in fp:
                NR += 1
                FNR += 1
                if self.FS:
                    S = SS.rstrip().split(self.FS)
                else:
                    S = SS.split()
                NF = len(S)
                # ACTION code block
                $ACTION
            fp.close()
        # END code block
        $END
    ''')
 
    @staticmethod
    def escape_newline_tab(sc):
        return sc.decode('string-escape')

    def generate_exec_statement(self, sc):
        BEGIN, ACTION, END = ("", "", "" )
        sc_escape = PynAwkOnlineGenerate.escape_newline_tab(sc)
        script = re.split(r'\n(?:[ \t\n\r\f\v]*\n)+', sc_escape)
        if len(script) == 1:
            ACTION = script[0]
        elif len(script) == 2:
            BEGIN, ACTION = script
        else:
            BEGIN, ACTION, END = script 
        BEGIN = "\n        ".join(BEGIN.split("\n"))
        END = "\n        ".join(END.split("\n"))
        ACTION = "\n                ".join(ACTION.split("\n"))
        exec_script = self.class_template.substitute(
            BEGIN=BEGIN,
            ACTION=ACTION,
            END=END)
        return exec_script

    def process_args(self, args, doc):
        ap = argparse.ArgumentParser(description=doc)
        ap.add_argument(
            '-f', '--program-file', action='store_true',
            dest='PROGRAM_FILE', help="""\
                Read the AWK program source from the file program-file,
                instead of from the first command line argument""")
        ap.add_argument(
            'SCRIPT', action="store",
            help='the script to process line')
        ap.add_argument(
            'FILES', nargs='*',
            help='files to be processed')
        ap.add_argument(
            '-F', '--fieldseparator', action='store',
            dest="FS", help='field separator')
        options = ap.parse_args(args)
        return options

if __name__ == "__main__":
    pynawkonline = PynAwkOnlineGenerate()
    options = pynawkonline.process_args(
        sys.argv[1:],
        """\
        pynawk - awk like python utility
        """)
    if options.PROGRAM_FILE:
        sc = open(options.SCRIPT).read()
    else:
        sc = options.SCRIPT
    exec_script = pynawkonline.generate_exec_statement(sc)
    # print(exec_script)
    exec(exec_script)
    PynAwk(options).process()

'''
cat program_file1.txt
# BEGIN code block 
total_match_cnt = 0
 
# ACTION code block              
if re.search('foo', SS) or re.search('21', SS) :
    total_match_cnt += 1
    print("{}: ", NR, SS.rstrip())

# END code block
print("Total matches:", total_match_cnt)

pynawk -f program_file BBS-list.txt inventory-shipped.txt
NR: fooey 555-1234 2400/1200/300 B
NR: foot 555-6699 1200/300 B
NR: macfoo 555-6480 1200/300 A
NR: sabafoo 555-2127 1200/300 C
NR: Jan 21 36 64 620
NR: Apr 21 70 74 514
Total matches: 6

cat program_file2.txt 
# BEGIN code block 
total_match_cnt = 0
match_cnt_per_file = 0

# ACTION code block
if (FILEINDEX > 0) and FNR == 1:
    print("number of matches in {}:{}".format(
        self.FILES[FILEINDEX - 1],
        match_cnt_per_file)) 
    match_cnt_per_file = 0                
if re.search('foo', SS) or re.search('21', SS) :
    total_match_cnt += 1
    match_cnt_per_file += 1
    if len(self.FILES) == 1: 
        print("{}: ", NR, SS, end='')
    else:
        print("{}:{}:{}".format(
            FILENAME, NR, SS.rstrip()))

# END code block
if len(self.FILES) > 1:
    print("number of matches in {}:{}".format(
        FILENAME, match_cnt_per_file))
print("Total matches:", total_match_cnt)

pynawk -f program_file BBS-list.txt inventory-shipped.txt
BBS-list.txt:7:fooey 555-1234 2400/1200/300 B
BBS-list.txt:8:foot 555-6699 1200/300 B
BBS-list.txt:9:macfoo 555-6480 1200/300 A
BBS-list.txt:11:sabafoo 555-2127 1200/300 C
number of matches in BBS-list.txt:4
inventory-shipped.txt:24:Jan 21 36 64 620
inventory-shipped.txt:27:Apr 21 70 74 514
number of matches in inventory-shipped.txt:2
Total matches: 6

'''
