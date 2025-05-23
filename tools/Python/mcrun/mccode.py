import os
import pathlib
import sys
import re
import shutil

if not os.name == 'nt':
    import shlex as lexer
else:
    import mslex as lexer

import yaml

from os.path import isfile, dirname, basename, splitext, join
from decimal import Decimal

# import config
import numpy
import sys

sys.path.append(join(dirname(__file__), '..'))
from mccodelib import mccode_config
import mccodelib.cflags

from log import getLogger

LOG = getLogger('mcstas')


def modified(path):
    ''' Get modification time of path in seconds '''
    return os.stat(path).st_mtime


def findReusableFile(source, candidates):
    ''' Finds an existing candidate that is newer than source modification time or None '''
    min_ = modified(source)
    for path in candidates:
        if isfile(path) and modified(path) > min_:
            return path
    return None


class ProcessException(Exception):
    ''' Exception/error in external process '''

    def __init__(self, executable, args, retval):
        Exception.__init__(self)
        self.executable = executable
        self.args = args
        self.retval = retval

    def __str__(self):
        return 'Got exit status %s from "%s %s"' % (self.retval,
                                                    self.executable,
                                                    ' '.join(self.args))


class Process:
    def __init__(self, executable):
        self.executable = executable

    def run(self, args=None, pipe=False):
        """Run external process with args"""
        from subprocess import run, CalledProcessError
        if args is None:
            args = []
        # Run executable as shell
        # command = [self.executable, *args]
        command = self.executable + " " + " ".join(args)
        LOG.debug(f'CMD: {command}')
        try:
            proc = run(command, shell=True, check=True, text=True, capture_output=pipe)
            LOG.debug(f"CMD: {self.executable} finished")
        except CalledProcessError as err:
            LOG.info(f"call to {self.executable} failed with {err}")
            raise err
        return proc.stdout


class McStas:
    ''' McStas instrument '''

    def __init__(self, instrument_file):
        if not isfile(instrument_file):
            raise IOError('No such instrument file: "%s"' % instrument_file)
        self.path = instrument_file
        self.name = splitext(basename(self.path))[0]
        self.options = None
        self.params = {}
        self.version = '%s %s' % (mccode_config.configuration['MCCOGEN'], mccode_config.configuration['MCCODE_VERSION'])

        # Setup paths
        if os.name == 'nt':
            self.cpath = '%s.c' % self.name
        else:
            self.cpath = './%s.c' % self.name

    def set_parameter(self, key, value):
        ''' Set the value of an experiment parameter '''
        self.params[key] = value

    def prepare(self, options):
        ''' Prepare for simultation run '''
        self.options = options

        def x_path(file):
            ''' Return external path (relative to self.path) for file '''
            return '%s/%s' % (dirname(self.path), basename(file))

        # Copy instrument file to cwd if not already there (for compatibility)
        if not isfile(basename(self.path)):
            shutil.copy2(self.path, ".")  # also copies stat information

        # Create the path for the binary
        if os.name == 'nt':
            self.binpath = '%s.%s' % (self.name, mccode_config.platform['EXESUFFIX'])
        else:
            self.binpath = './%s.%s' % (self.name, mccode_config.platform['EXESUFFIX'])

        # Check if c-code should be regenerated by comparing to instr timestamp
        existingC = findReusableFile(self.path,
                                     [self.cpath, x_path(self.cpath)])
        
        if self.options.cogen is not None:
            options.force_compile = True
            # options.mccode_bin already contains cogen value

        if self.options.D1 is not None:
            options.force_compile = True

        if self.options.D2 is not None:
            options.force_compile = True

        if self.options.D3 is not None:
            options.force_compile = True

        if self.options.I is not None:
            options.force_compile = True

        if not options.force_compile and existingC is not None:
            LOG.info('Using existing c-file: %s', existingC)
            self.cpath = existingC
        else:
            # Generate C-code (implicit: prepare for --trace or --no-trace mode if not no_main / Vitess)
            LOG.info('Regenerating c-file: %s', basename(self.cpath))
            mccode_bin_abspath = str( pathlib.Path(mccode_config.directories['bindir']) / options.mccode_bin )
            if not os.path.exists(mccode_bin_abspath):
                LOG.warning('Full-path code-generator "%s" not found!!', mccode_bin_abspath)
                mccode_bin_abspath=basename(mccode_bin_abspath)
                LOG.warning('Attempting replacement by "%s"', mccode_bin_abspath)

            if not options.no_main:
                trace='-t'
                if options.no_trace:
                   trace='--no-trace'
                if self.options.I is not None:
                    Process(mccode_bin_abspath).run([trace, '-o', self.cpath, self.path, '-I', self.options.I])
                else:
                    Process(mccode_bin_abspath).run([trace, '-o', self.cpath, self.path])
            else:
                if self.options.I is not None:
                    Process(mccode_bin_abspath).run(['--no-main', '-o', self.cpath, self.path, '-I', self.options.I])
                else:
                    Process(mccode_bin_abspath).run(['--no-main', '-o', self.cpath, self.path])

        # Check if binary should be regenerated by comparing to c timestamp
        existingBin = findReusableFile(self.cpath,
                                       [self.binpath, x_path(self.binpath)])

        # Reuse binary if present and up-to-date
        if not options.force_compile and existingBin is not None:
            LOG.info('Using existing binary: %s', existingBin)
            self.binpath = existingBin
            return  # skip recompilation

        LOG.info('Recompiling: %s', self.binpath)

        # Setup cflags, use -lm anywhere else than Windows-conda with cl.exe
        cflags = ''
        if not "cl.exe" in mccode_config.compilation['CC'].lower():
            cflags += '-lm ' # math library

        # Special support for conda environment with compilers included. To be
        # conservative we (for now?) only apply this when both CONDA_PREFIX and
        # LDFLAGS/CFLAGS are set (C++/Fortran would use CXXFLAGS/FFLAGS instead
        # of CFLAGS):
        if mccode_config.configuration['ISCONDAPKG']=='1' and os.environ.get('CONDA_PREFIX'):
            if os.environ.get('LDFLAGS'):
                cflags += os.environ.get('LDFLAGS') + " "
            if os.environ.get('CFLAGS'):
                cflags += os.environ.get('CFLAGS') + " "

            # Special handling of NVIDIA's OpenACC-aware compiler inside a CONDA env,
            # remove certain unsupported flags:
            if self.options.openacc and 'nvc' in mccode_config.compilation['OACC']:
                Cflags = cflags
                Cflags=Cflags.replace('-march=nocona', '')
                Cflags=Cflags.replace('-ftree-vectorize', '')
                Cflags=Cflags.replace('-fstack-protector-strong', '')
                Cflags=Cflags.replace('-fno-plt', '')
                Cflags=Cflags.replace('-ffunction-sections', '')
                Cflags=Cflags.replace('-pipe', '')
                cflags=Cflags

        # Parse for instances of CMD() ENV() GETPATH() in the loaded CFLAG entries using fct. evaluate_dependency_str
        
        # MPI
        if self.options.mpi: 
            cflags += mccodelib.cflags.evaluate_dependency_str(mccode_config.compilation['MPIFLAGS'],
                                                                                 options.verbose) + " "
        # OpenACC
        if self.options.openacc: 
            cflags += mccodelib.cflags.evaluate_dependency_str(mccode_config.compilation['OACCFLAGS'],
                                                                              options.verbose) + " "
        # NeXus
        if self.options.format.lower() == 'nexus':
            cflags += mccodelib.cflags.evaluate_dependency_str(
            mccode_config.compilation['NEXUSFLAGS'], options.verbose)  + " "

        # Funneling
        if self.options.funnel:
            cflags += ' -DFUNNEL '                                                               
        
        # Commandline -D flags
        if self.options.D1 is not None:
            cflags += self.options.D1 + " "
        if self.options.D2 is not None:
            cflags += self.options.D2 + " "
        if self.options.D3 is not None:
            cflags += self.options.D3 + " "       

        # Add "standard CFLAGS" or "no CFLAGS" if not openacc
        if not self.options.openacc:
            cflags += options.no_cflags and ['-O0'] + " " or mccode_config.compilation['CFLAGS'] + " " # cflags

        # Look for CFLAGS in the generated C code
        ccode = open(self.cpath, 'rb')
        counter = 0

        MCCODE_LIB = self.options.mccode_lib
        # On windows, replace \ by / for safety
        if os.name == 'nt':
            MCCODE_LIB = re.sub(r'\\', '/', MCCODE_LIB)

        for line in ccode:
            line = line.decode().rstrip()
            line = re.sub(r'\\', '/', line)
            if re.search('CFLAGS=', line):
                label, flags = line.split('=', 1)

                # Insert NEXUSFLAGS if instrument/comps request this
                flags = re.sub(r'\@NEXUSFLAGS\@', mccode_config.compilation['NEXUSFLAGS'], flags)

                # Insert NCRYSTALFLAGS if instrument/comps request this
                flags = re.sub(r'\@MCPLFLAGS\@', mccode_config.compilation['MCPLFLAGS'], flags)

                # Insert NCRYSTALFLAGS if instrument/comps request this
                flags = re.sub(r'\@NCRYSTALFLAGS\@', mccode_config.compilation['NCRYSTALFLAGS'], flags)

                # Insert GSLFLAGS if instrument/comps request this
                flags = re.sub(r'\@GSLFLAGS\@', mccode_config.compilation['GSLFLAGS'], flags)

                # Insert XRLFLAGS if instrument/comps request this (McXtrace only)
                flags = re.sub(r'\@XRLFLAGS\@', mccode_config.compilation['XRLFLAGS'], flags)

                # Support for legacy @MCCODE_LIB@ symbol, with Unix-slashes
                flags = re.sub(r'\@MCCODE_LIB\@', re.sub(r'\\', '/', MCCODE_LIB), flags)

                # Support CMD(..) and ENV(..) in cflags:
                flags = mccodelib.cflags.evaluate_dependency_str(flags, options.verbose)

                cflags += flags + " "

            counter += 1
            if (counter > 20):
                break

        if any("OPENACC" in cf for cf in cflags):
            if any("NeXus" in cf for cf in cflags):
                cflags += '-D__GNUC__'+ " "

        # cl.exe on Windows needs the linking flags at the end...
        if os.name == 'nt' and "cl.exe" in mccode_config.compilation['CC'].lower():
            libflags = []
            otherflags = []
            for flag in lexer.split(cflags):
                # /link /LIBPATH or .lib file means linking flag
                if str(flag).lower().startswith("/l") or str(flag).lower().endswith(r'.lib'):
                    if not(flag.startswith("/link")):
                        libflags.append(flag)
                # Everthing else
                else:
                    if flag.startswith("-std="): # -std
                        flag.replace("-std=","/std:")
                    if flag.startswith("-D"): # -D defines
                        flag.replace("-D","/D")
                    if flag.startswith("-U"): # -U undefines
                        flag.replace("-U","/U")
                    otherflags.append(flag)

            cflags = lexer.join(otherflags) + " /link " + lexer.join(libflags)

        # A final check for presence of CONDA_PREFIX strings
        if os.environ.get('CONDA_PREFIX'):
            if "${CONDA_PREFIX}" in cflags:
                cflags=cflags.replace("${CONDA_PREFIX}",os.environ.get('CONDA_PREFIX'))

        # Final assembly of compiler commandline
        if not "cl.exe" in mccode_config.compilation['CC'].lower():
            args = ['-o', self.binpath, self.cpath] + lexer.split(cflags)
        else:
            args = [self.cpath] + lexer.split(cflags)
        Process(lexer.quote(options.cc)).run(args)

    def run(self, pipe=False, extra_opts=None, override_mpi=None):
        ''' Run simulation '''
        args = []
        extra_opts = extra_opts or {}

        options = self.options

        # Handle proxy options with values
        proxy_opts_val = ['trace', 'seed', 'ncount', 'dir', 'format', 'vecsize', 'numgangs', 'gpu_innerloop', 'bufsiz']
        proxy_opts_val.extend(('meta-defined', 'meta-type', 'meta-data'))

        for opt in proxy_opts_val:
            # try extra_opts before options
            default = getattr(options, opt.replace('-', '_'))
            val = extra_opts.get(opt, default)
            if val is not None and val != '':
                args.extend([f'--{opt}=' + str(val)])

        # Handle proxy options without values (flags)
        proxy_opts_flags = ['no-output-files', 'info', 'list-parameters', 'meta-list', 'yes']
        if mccode_config.configuration["MCCODE"] == 'mcstas':
            proxy_opts_flags.append('gravitation')

        for opt in proxy_opts_flags:
            # try extra_opts before options
            default = getattr(options, opt.replace('-', '_'))
            val = extra_opts.get(opt, default)
            if val:
                args.append('--%s' % opt)

        # Add parameters last
        args += ['%s=%s' % (key, value)
                 for key, value in self.params.items()]

        return self.runMPI(args, pipe, override_mpi)

    def runMPI(self, args, pipe=False, override_mpi=None):
        """ Run McStas, possibly via mpi """
        binpath = self.binpath
        myformat = self.options.format

        # If this is McStas, if format is NeXus and --IDF requested, call the XML-generator
        if mccode_config.configuration["MCCODE"] == 'mcstas' and not self.options.info:
            if self.options.format.lower() == 'nexus' and self.options.IDF:
                idfargs=[]
                # Strip off args not understood by the IDF generator
                for arg in args:
                    if '--trace' in arg:
                        # do nothing
                        1
                    elif '--format' in arg:
                        # do nothing
                        1
                    elif '--dir' in arg:
                        # do nothing
                        1
                    elif '--bufsiz' in arg:
                        # do nothing
                        1
                    else:
                        idfargs.append(arg)

                print("Spawning IDF generator:")
                print(mccode_config.configuration['IDFGEN'] + " " + self.path + " " + " ".join(idfargs))
                Process(mccode_config.configuration['IDFGEN'] + " " + self.path).run(idfargs, pipe=pipe)
                # Forward --IDF request to binary
                args.append('--IDF')

        mpi = self.options.use_mpi
        if override_mpi or override_mpi is None and mpi:
            LOG.debug('Running via MPI: %s', self.binpath)
            binpath = self.options.mpirun
            if self.options.mpi == "auto":
                LOG.info('Using system default number of mpirun -np processes')
                if os.name == 'nt':
                    mpi_flags = [''] # msmpi mpiexec.exe does not accept --
                else:
                    mpi_flags = ['--'] # ... whereas openmpi mpirun does.
            elif int(self.options.mpi) >= 1:
                mpi_flags = ['-np', str(self.options.mpi)]
            else:
                mpi_flags = []
            if self.options.machines:
                mpi_flags = mpi_flags + ['-machinefile', self.options.machines]
            if self.options.openacc and not os.name == 'nt':
                mpi_flags = mpi_flags + [mccode_config.directories['bindir'] + '/' + mccode_config.configuration['MCCODE'] + '-acc_gpu_bind']
            args = mpi_flags + [self.binpath] + args

        return Process(binpath).run(args, pipe=pipe)

    def get_info(self):
        return McStasInfo(self.runMPI(['--info'], pipe=True))


class Detector(object):
    ''' A detector representation with its integrated values and statistics.'''
    # this is used in optimisation.py

    def __init__(self, name, intensity, error, count, path, statistics):
        self.name  = name
        self.intensity = float(intensity)
        self.error = float(error)
        self.count = float(count)
        self.path  = path
        self.values= numpy.array([ intensity, error, count ])
        # get statistics
        d = []
        for sub in statistics.split(';'): # separate the 'name=value;' bits:
          if '=' in sub:
            d.append(map(str.strip, sub.split('=',1)))
        
        d = dict(d)
        if not 'X0' in d:
          d['X0'] = 0
        if not 'dX' in d:
          d['dX'] = 1
        if not 'Y0' in d:
          d['Y0'] = 0
        if not 'dY' in d:
          d['dY'] = 1
        
        self.X0 = float(d['X0'])
        self.dX = float(d['dX'])
        self.Y0 = float(d['Y0'])
        self.dY = float(d['dY'])
        if not self.dX:
          self.dX = 1
        if not self.dY:
          if self.dX:
            self.dY = self.dX
          else:
            self.dY = 1


class McStasInfo:
    ''' Parsing McStas experiment information (--info) '''

    PARAMETERS_RE = re.compile(r'^\s*Parameters:(.*)', flags=re.MULTILINE)
    SEPERATOR_RE = re.compile(r'^([^:]+):\s*')
    QUOTE_RE = re.compile(r'^(\s*[^:]+):\s*([^\[\s].*)$', flags=re.MULTILINE)
    GROUP_RE = re.compile(r'begin ([^\s]+)(.+)end \1', flags=re.DOTALL)
    PARAM_RE = re.compile(r'^\s*Param:\s+"', flags=re.MULTILINE)

    def __init__(self, data):
        self.data = data
        self.info = self._parse_info()

    def _parse_info(self):
        """
        Parse the raw McStas info output
        The output resembles YAML but not quite.
        It's converted to YAML by:
          0. Ensuring a space after 'key:' -> 'key: '
          1. Adding qoutes 'key: value' -> 'key: "value"'
          2. Changing 'begin foobar\n ...\n end foobar' -> 'foobar:\n'
          3. Add unique suffix number to each param:
               Param: lambda=0.7
               Param: DM=1.8
               -->
               Param0: lambda=0.7
               Param1: DM=1.8
          4. Split up 'Parameters' to form a list
        """

        def escape(line):
            # ''' Escape \ and " '''
            return line.replace('\\', '\\\\').replace('"', r'\"')

        def quote(match):
            ''' Quote a value '''
            return '%s: "%s"' % (match.group(1), escape(match.group(2)))

        def param_number(match):
            ''' Assign unique number to each param '''
            param_number.prev_param_number += 1
            return match.group(0).replace('Param',
                                          'Param%i' % param_number.prev_param_number)

        # start count at 0 (previous is -1)
        setattr(param_number, 'prev_param_number', -1)

        def parameters_to_list(match):
            old_str = match.group(1)
            if old_str.strip():
                new_str = ' [%s]' % ','.join(match.group(1).split())
                return match.group(0).replace(old_str, new_str)
            return match.group(0).strip() + ' []'

        yaml_str = self.data
        yaml_str = self.PARAMETERS_RE.sub(parameters_to_list, yaml_str)
        yaml_str = self.SEPERATOR_RE.sub(r'\1: ', yaml_str)
        yaml_str = self.QUOTE_RE.sub(quote, yaml_str)
        yaml_str = self.GROUP_RE.sub(r'\1:\2', yaml_str)
        yaml_str = self.PARAM_RE.sub(param_number, yaml_str)

        return yaml.load(yaml_str)

    def get(self, key):
        return self.info[key]

    def get_simulation(self):
        return self.get('simulation')

    def get_instrument(self):
        return self.get('instrument')
