# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2009 Hewlett-Packard Development Company, L.P.
#
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
# Author: Don Welch
#

# Std Lib
import sys
import os
import os.path
import re
import time
import cStringIO
import grp
import pwd
import tarfile
import stat
import glob

try:
    import hashlib # new in 2.5

    def get_checksum(s):
        return hashlib.sha1(s).hexdigest()

except ImportError:
    import sha # deprecated in 2.6/3.0

    def get_checksum(s):
        return sha.new(s).hexdigest()


import urllib # TODO: Replace with urllib2 (urllib is deprecated in Python 3.0)


# Local
from base.g import *
from base.codes import *
from base import utils, pexpect, tui, password, services, os_utils
from dcheck import *



DISTRO_UNKNOWN = 0
DISTRO_VER_UNKNOWN = '0.0'

MODE_INSTALLER = 0 # hplip-install/hp-setup
MODE_CHECK = 1 # hp-check
MODE_CREATE_DOCS = 2 # create_docs

TYPE_STRING = 1
TYPE_LIST = 2
TYPE_BOOL = 3
TYPE_INT = 4

DEPENDENCY_RUN_TIME = 1
DEPENDENCY_COMPILE_TIME = 2
DEPENDENCY_RUN_AND_COMPILE_TIME = 3



# Mapping from patterns to probability contribution of pattern
# Example code from David Mertz' Text Processing in Python.
# Released in the Public Domain.
err_pats = {r'(?is)<TITLE>.*?(404|403).*?ERROR.*?</TITLE>': 0.95,
            r'(?is)<TITLE>.*?ERROR.*?(404|403).*?</TITLE>': 0.95,
            r'(?is)<TITLE>ERROR</TITLE>': 0.30,
            r'(?is)<TITLE>.*?ERROR.*?</TITLE>': 0.10,
            r'(?is)<META .*?(404|403).*?ERROR.*?>': 0.80,
            r'(?is)<META .*?ERROR.*?(404|403).*?>': 0.80,
            r'(?is)<TITLE>.*?File Not Found.*?</TITLE>': 0.80,
            r'(?is)<TITLE>.*?Not Found.*?</TITLE>': 0.40,
            r'(?is)<BODY.*(404|403).*</BODY>': 0.10,
            r'(?is)<H1>.*?(404|403).*?</H1>': 0.15,
            r'(?is)<BODY.*not found.*</BODY>': 0.10,
            r'(?is)<H1>.*?not found.*?</H1>': 0.15,
            r'(?is)<BODY.*the requested URL.*</BODY>': 0.10,
            r'(?is)<BODY.*the page you requested.*</BODY>': 0.10,
            r'(?is)<BODY.*page.{1,50}unavailable.*</BODY>': 0.10,
            r'(?is)<BODY.*request.{1,50}unavailable.*</BODY>': 0.10,
            r'(?i)does not exist': 0.10,
           }
# Note:- If new utility is added, add same utility here to uninstall properly.

BINS_LIST=['hpijs','hp-align','hp-colorcal','hp-faxsetup','hp-linefeedcal','hp-pkservice','hp-printsettings','hp-sendfax','hp-timedate','hp-check','hp-devicesettings','hp-firmware','hp-makecopies','hp-plugin','hp-probe','hp-setup','hp-toolbox','hp-check-plugin','hp-diagnose_plugin','hp-info','hp-makeuri','hp-pqdiag','hp-query','hp-systray','hp-unload','hp-clean','hp-fab','hp-levels','hp-print','hp-scan','hp-testpage','hp-wificonfig', 'hp-upgrade','hplip-info','hp-check-upgrade','hp-config_usb_printer','hp-diagnose_queues', 'hp-devicesetup','hp-doctor','hp-logcapture']

LIBS_LIST=['libhpmud.*','libhpip.*','sane/libsane-hpaio.*','cups/backend/hp','cups/backend/hpfax', 'cups/filter/hpcac', 'cups/filter/hpps', 'cups/filter/pstotiff','cups/filter/hpcups', 'cups/filter/hpcupsfax', 'cups/filter/hplipjs']

HPLIP_EXT_LIST = ['cupsext.so', 'cupsext.la', 'scanext.so', 'scanext.la', 'hpmudext.so', 'hpmudext.la', 'pcardext.so', 'pcardext.la']

FILES_LIST=[ '/usr/share/cups/drv/hp/','/usr/local/share/ppd/HP/','/usr/local/share/cups/drv/hp/' ,'/usr/share/applications/hplip.desktop', '/etc/xdg/autostart/hplip-systray.desktop', '/etc/hp/hplip.conf', '/usr/share/doc/hplip-*','/usr/lib/systemd/system/hplip-printer*.service']

RULES_LIST=['56-hpmud.rules','56-hpmud_sysfs.rules', '40-hplip.rules', '56-hpmud_support.rules', '56-hpmud_support_sysfs.rules','55-hpmud.rules','55-hpmud_sysfs.rules','56-hpmud_add_printer.rules','56-hpmud_add_printer_sysfs.rules', '86-hpmud-hp_*.rules', '86-hpmud_plugin.rules', '86-hpmud_plugin_sysfs.rules']

HPLIP_LIST=['*.py','*.pyc', 'base', 'copier','data','installer','pcard','ui4','ui','fax/*.py','fax/*.pyc','fax/pstotiff.convs','fax/pstotiff.types','fax/pstotiff','prnt/*.py', 'prnt/*.pyc', 'scan/*.py','scan/*.pyc']

PLUGIN_LIST=['fax/plugins/','prnt/plugins/','scan/plugins/']

PLUGIN_STATE =['/var/lib/hp/hplip.state']


# end



OK_PROCESS_LIST = ['adept-notifier',
                   'adept_notifier',
                   'yum-updatesd',
                   ]

CONFIGURE_ERRORS = { 1 : "General/unknown error",
                     2 : "libusb not found",
                     3 : "cups-devel not found",
                     4 : "libnetsnmp not found",
                     5 : "netsnmp-devel not found",
                     6 : "python-devel not found",
                     7 : "pthread-devel not found",
                     8 : "ppdev-devel not found",
                     9 : "libcups not found",
                     10 : "libm not found",
                     11 : "libusb-devel not found",
                     12 : "sane-backends-devel not found",
                     13 : "libdbus not found",
                     14 : "dbus-devel not found",
                     15 : "fax requires dbus support",
                     102 : "libjpeg not found",
                     103 : "jpeg-devel not found",
                     104 : "libdi not found",
                   }


try:
    from functools import update_wrapper
except ImportError: # using Python version < 2.5
    def trace(f):
        def newf(*args, **kw):
           log.debug("TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw))
           return f(*args, **kw)
        newf.__name__ = f.__name__
        newf.__dict__.update(f.__dict__)
        newf.__doc__ = f.__doc__
        newf.__module__ = f.__module__
        return newf
else: # using Python 2.5+
    def trace(f):
        def newf(*args, **kw):
            log.debug("TRACE: func=%s(), args=%s, kwargs=%s" % (f.__name__, args, kw))
            return f(*args, **kw)
        return update_wrapper(newf, f)



class CoreInstall(object):
    def __init__(self, mode=MODE_INSTALLER, ui_mode=INTERACTIVE_MODE, ui_toolkit='qt4'):
        os.umask(0022)
        self.mode = mode
        self.ui_mode = ui_mode
        self.passwordObj = password.Password(ui_mode)
        self.version_description, self.version_public, self.version_internal = '', '', ''
        self.bitness = 32
        self.endian = utils.LITTLE_ENDIAN
        self.distro, self.distro_name, self.distro_version = DISTRO_UNKNOWN, '', DISTRO_VER_UNKNOWN
        self.distro_version_supported = False
        self.install_location = '/usr'
        self.hplip_present = False
        self.have_dependencies = {}
        self.native_cups = True
        self.ppd_dir = None
        self.drv_dir = None
        self.distros = {}
        self.ui_toolkit = ui_toolkit
        self.enable = None
        self.disable = None
        self.reload_dbus = False


        self.FIELD_TYPES = {
            'distros' : TYPE_LIST,
            'index' : TYPE_INT,
            'versions' : TYPE_LIST,
            'display_name' : TYPE_STRING,
            'alt_names': TYPE_LIST,
            'display': TYPE_BOOL,
            'notes': TYPE_STRING,
            'package_mgrs': TYPE_LIST,
            'package_mgr_cmd':TYPE_STRING,
            'pre_install_cmd': TYPE_LIST,
            'pre_depend_cmd': TYPE_LIST,
            'post_depend_cmd': TYPE_LIST,
            'hpoj_remove_cmd': TYPE_STRING,
            'hplip_remove_cmd': TYPE_STRING,
            'su_sudo': TYPE_STRING,
            'ppd_install': TYPE_STRING,
            'udev_mode_fix': TYPE_BOOL,
            'ppd_dir': TYPE_STRING,
            'drv_dir' : TYPE_STRING,
            'fix_ppd_symlink': TYPE_BOOL,
            'code_name': TYPE_STRING,
            'supported': TYPE_BOOL, # Supported by installer
            'release_date': TYPE_STRING,
            'packages': TYPE_LIST,
            'commands': TYPE_LIST,
            'same_as_version' : TYPE_STRING,
            'scan_supported' : TYPE_BOOL,
            'fax_supported' : TYPE_BOOL,
            'pcard_supported' : TYPE_BOOL,
            'network_supported' : TYPE_BOOL,
            'parallel_supported' : TYPE_BOOL,
            'usb_supported' : TYPE_BOOL,
            'packaged_version': TYPE_STRING, # Version of HPLIP pre-packaged in distro
            'cups_path_with_bitness' : TYPE_BOOL,
            'ui_toolkit' : TYPE_STRING,  # qt3 or qt4 [or gtk] or none
            'policykit' : TYPE_BOOL,
            'libusb01' : TYPE_BOOL,
            'udev_sysfs_rule' : TYPE_BOOL,
            'native_cups' : TYPE_BOOL,
            'package_available' : TYPE_BOOL,
            'package_arch' : TYPE_LIST,
            'open_mdns_port' : TYPE_LIST, # command to use to open mdns multicast port 5353
            'acl_rules' : TYPE_BOOL, # Use ACL uDEV rules (Ubuntu 9.10+)
            'libdir_path' : TYPE_STRING,
        }

        # components
        # 'name': ('description', [<option list>])
        self.components = {
            'hplip': ("HP Linux Imaging and Printing System", ['base', 'network', 'gui_qt4',
                                                               'fax', 'scan', 'docs']),
        }

        self.selected_component = 'hplip'

        # options
        # name: (<required>, "<display_name>", [<dependency list>]), ...
        self.options = {
            'base':     (True,  'Required HPLIP base components (including hpcups)', []), # HPLIP
            'network' : (False, 'Network/JetDirect I/O', []),
            'gui_qt4' : (False, 'Graphical User Interfaces (Qt4)', []),
            'fax' :     (False, 'PC Send Fax support', []),
            'scan':     (False, 'Scanning support', []),
            'docs':     (False, 'HPLIP documentation (HTML)', []),
            'policykit': (False, 'Administrative policy framework', []),
            'libusb01': (False, 'libusb-1.0', []),
            'udev_sysfs_rule': (False, 'udev_sysfs_rule', []),
        }


        # holds whether the user has selected (turned on each option)
        # initial values are defaults (for GUI only)
        self.selected_options = {
            'base':        True,
            'network':     True,
            'gui_qt4':     True,
            'fax':         True,
            'scan':        True,
            'docs':        True,
            'policykit':   False,
            'libusb01' :   False,
            'udev_sysfs_rule' : False,
            'native_cups': False,
        }

        # dependencies
        # 'name': (<required for option>, [<option list>], <display_name>, <check_func>, <runtime/compiletime>), ...
        # Note: any change to the list of dependencies must be reflected in base/distros.py
        self.dependencies = {
            # Required base packages
            'libjpeg':          (True,  ['base'], "libjpeg - JPEG library", self.check_libjpeg, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'libtool':          (True,  ['base'], "libtool - Library building support services", self.check_libtool, DEPENDENCY_COMPILE_TIME),
            'cups' :            (True,  ['base'], 'CUPS - Common Unix Printing System', self.check_cups, DEPENDENCY_RUN_TIME),
            'cups-devel':       (True,  ['base'], 'CUPS devel- Common Unix Printing System development files', self.check_cups_devel, DEPENDENCY_COMPILE_TIME),
            'cups-image':       (True,  ['base'], "CUPS image - CUPS image development files", self.check_cups_image, DEPENDENCY_COMPILE_TIME),
            'gcc' :             (True,  ['base'], 'gcc - GNU Project C and C++ Compiler', self.check_gcc, DEPENDENCY_COMPILE_TIME),
            'make' :            (True,  ['base'], "make - GNU make utility to maintain groups of programs", self.check_make, DEPENDENCY_COMPILE_TIME),
            'python-devel' :    (True,  ['base'], "Python devel - Python development files", self.check_python_devel, DEPENDENCY_COMPILE_TIME),
            'libpthread' :      (True,  ['base'], "libpthread - POSIX threads library", self.check_libpthread, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'python2x':         (True,  ['base'], "Python 2.2 or greater - Python programming language", self.check_python2x, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'python-xml'  :     (True,  ['base'], "Python XML libraries", self.check_python_xml, DEPENDENCY_RUN_TIME),
            'gs':               (True,  ['base'], "GhostScript - PostScript and PDF language interpreter and previewer", self.check_gs, DEPENDENCY_RUN_TIME),
            'libusb':           (True,  ['base'], "libusb - USB library", self.check_libusb, DEPENDENCY_RUN_AND_COMPILE_TIME),

            # Optional base packages
            'cups-ddk':          (False, ['base'], "CUPS DDK - CUPS driver development kit", self.check_cupsddk, DEPENDENCY_RUN_TIME), # req. for .drv PPD installs


            # Required scan packages
            'sane':             (True,  ['scan'], "SANE - Scanning library", self.check_sane, DEPENDENCY_RUN_TIME),
            'sane-devel' :      (True,  ['scan'], "SANE - Scanning library development files", self.check_sane_devel, DEPENDENCY_COMPILE_TIME),

            # Optional scan packages
            'xsane':            (False, ['scan'], "xsane - Graphical scanner frontend for SANE", self.check_xsane, DEPENDENCY_RUN_TIME),
            'scanimage':        (False, ['scan'], "scanimage - Shell scanning program", self.check_scanimage, DEPENDENCY_RUN_TIME),
            'pil':              (False, ['scan'], "PIL - Python Imaging Library (required for commandline scanning with hp-scan)", self.check_pil, DEPENDENCY_RUN_TIME),

            # Required fax packages
            'python23':         (True,  ['fax'], "Python 2.3 or greater - Required for fax functionality", self.check_python23, DEPENDENCY_RUN_TIME),
            'dbus':             (True,  ['fax'], "DBus - Message bus system", self.check_dbus, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'python-dbus':      (True,  ['fax'], "Python DBus - Python bindings for DBus", self.check_python_dbus, DEPENDENCY_RUN_TIME),

            # Optional fax packages
            'reportlab':        (False, ['fax'], "Reportlab - PDF library for Python", self.check_reportlab, DEPENDENCY_RUN_TIME),

            # Required and optional qt4 GUI packages
            'pyqt4':            (True,  ['gui_qt4'], "PyQt 4- Qt interface for Python (for Qt version 4.x)", self.check_pyqt4, DEPENDENCY_RUN_TIME), # PyQt 4.x )
            'pyqt4-dbus' :      (True,  ['gui_qt4'], "PyQt 4 DBus - DBus Support for PyQt4", self.check_pyqt4_dbus, DEPENDENCY_RUN_TIME),
            'policykit':        (False, ['gui_qt4'], "PolicyKit - Administrative policy framework", self.check_policykit, DEPENDENCY_RUN_TIME), # optional for non-sudo behavior of plugins (only optional for Qt4 option)
            'python-notify' :   (False, ['gui_qt4'], "Python libnotify - Python bindings for the libnotify Desktop notifications", self.check_pynotify, DEPENDENCY_RUN_TIME), # Optional for libnotify style popups from hp-systray

            # Required network I/O packages
            'libnetsnmp-devel': (True,  ['network'], "libnetsnmp-devel - SNMP networking library development files", self.check_libnetsnmp, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'libcrypto':        (True,  ['network'], "libcrypto - OpenSSL cryptographic library", self.check_libcrypto, DEPENDENCY_RUN_AND_COMPILE_TIME),
            'network':        (False, ['network'], "network -wget", self.check_wget, DEPENDENCY_RUN_TIME),
            'avahi-utils':        (False, ['network'], "avahi-utils", self.check_avahi_utils, DEPENDENCY_RUN_TIME),
#            'passwd_util':        (False, ['gui_qt4'], "GUI Password utility (gksu/kdesu)", self.check_passwd_util, DEPENDENCY_RUN_TIME),
        }

        for opt in self.options:
            update_spinner()
            for d in self.dependencies:
                if opt in self.dependencies[d][1]:
                    self.options[opt][2].append(d)

        self.load_distros()

        self.distros_index = {}
        for d in self.distros:
            self.distros_index[self.distros[d]['index']] = d


    def init(self, callback=None):
        if callback is not None:
            callback("Init...\n")

        update_spinner()

        # Package manager names
        self.package_mgrs = []
        for d in self.distros:
            update_spinner()

            for a in self.distros[d].get('package_mgrs', []):
                if a and a not in self.package_mgrs:
                    self.package_mgrs.append(a)

        self.version_description, self.version_public, self.version_internal = self.get_hplip_version()
        log.debug("HPLIP Description=%s Public version=%s Internal version = %s"  %
            (self.version_description, self.version_public, self.version_internal))

        # have_dependencies
        # is each dependency satisfied?
        # start with each one 'No'
        for d in self.dependencies:
            update_spinner()
            self.have_dependencies[d] = False

        self.get_distro()
        self.distro_name = self.distros_index[self.distro]
        self.distro_changed()

        if callback is not None:
            callback("Distro: %s\n" % self.distro)

        self.check_dependencies(callback)

        for d in self.dependencies:
            update_spinner()

            log.debug("have %s = %s" % (d, self.have_dependencies[d]))

            if callback is not None:
                callback("Result: %s = %s\n" % (d, self.have_dependencies[d]))

        pid, cmdline = utils.check_pkg_mgr(self.package_mgrs)
        if pid:
            log.debug("Running package manager: %s (%s)" % (cmdline, pid) )

        self.bitness = utils.getBitness()
        log.debug("Bitness = %d" % self.bitness)

        update_spinner()

        self.endian = utils.getEndian()
        log.debug("Endian = %d" % self.endian)

        update_spinner()


        self.distro_version_supported = self.get_distro_ver_data('supported', False)

        log.debug("Distro = %s Distro Name = %s Display Name= %s Version = %s Supported = %s" %
            (self.distro, self.distro_name, self.distros[self.distro_name]['display_name'],
             self.distro_version, self.distro_version_supported))

        update_spinner()

        self.hplip_present = self.check_hplip()
        log.debug("HPLIP (prev install) = %s" % self.hplip_present)

        status, output = utils.run('cups-config --version', self.passwordObj)
        self.cups_ver = output.strip()
        log.debug("CUPS version = %s" % self.cups_ver)

        if self.distro_name == "ubuntu":
            self.reload_dbus = True

        log.debug("DBUS configuration reload possible? %s" % self.reload_dbus)

        status, self.sys_uname_info = utils.run('uname -a', self.passwordObj)
        self.sys_uname_info = self.sys_uname_info.replace('\n', '')
        log.debug(self.sys_uname_info)

        # Record the installation time/date and version.
        # Also has the effect of making the .hplip.conf file user r/w
        # on the 1st run so that running hp-setup as root doesn't lock
        # the user out of owning the file
        user_conf.set('installation', 'date_time', time.strftime("%x %H:%M:%S", time.localtime()))
        user_conf.set('installation', 'version', self.version_public)

        if callback is not None:
            callback("Done")


    def init_for_docs(self, distro_name, version, bitness=32):
        self.distro_name = distro_name
        self.distro_version = version

        try:
            self.distro = self.distros[distro_name]['index']
        except KeyError:
            log.error("Invalid distro name: %s" % distro_name)
            sys.exit(1)

        self.bitness = bitness

        for d in self.dependencies:
            self.have_dependencies[d] = True

        self.enable_ppds = self.get_distro_ver_data('ppd_install', 'ppd') == 'ppd'
        self.ppd_dir = self.get_distro_ver_data('ppd_dir')
        self.drv_dir = self.get_distro_ver_data('drv_dir')

        self.distro_version_supported = True # for manual installs


    def check_dependencies(self, callback=None):
        update_ld_output()

        for d in self.dependencies:
            update_spinner()

            log.debug("Checking for dependency '%s'...\n" % d)

            if callback is not None:
                callback("Checking: %s\n" % d)

            self.have_dependencies[d] = self.dependencies[d][3]()
            log.debug("have %s = %s" % (d, self.have_dependencies[d]))

        cleanup_spinner()


    def password_func(self):
        if self.password:
            return self.password
        elif self.ui_mode == INTERACTIVE_MODE:
            import getpass
            return getpass.getpass("Enter password: ")
        else:
            return ''


    def get_distro(self):
        log.debug("Determining distro...")
        name, ver = '','0.0'
        found = False

        try:
            import platform
            name = platform.dist()[0].lower()
            ver = platform.dist()[1]
            found = True
        except:
            found = False

        # Getting distro information using lsb_release command
        # platform retrurn 'redhat' even for 'RHEL' so re-reading using lsb_release.

        if not found:
            lsb_release = utils.which("lsb_release")
            if lsb_release:
                log.debug("Using 'lsb_release -is/-rs'")
                cmd = os.path.join(lsb_release, "lsb_release")
                status, name = utils.run(cmd + ' -is', self.passwordObj)
                if not status and name:
                    status, ver = utils.run(cmd + ' -rs', self.passwordObj)
                    found = True

        if not found:
            try:
                name = file('/etc/issue', 'r').read().lower().strip()
            except IOError:
                # Some O/Ss don't have /etc/issue (Mac)
                found = False
            else:
                found = True
                for n in name.split():
                    m = n
                    if '.' in n:
                        m = '.'.join(n.split('.')[:2])

                    try:
                        ver = float(m)
                    except ValueError:
                        try:
                           ver =  int(m)
                        except ValueError:
                            ver = '0.0'
                        else:
                            ver = m
                            break
                    else:
                        ver = m
                        break

                    log.debug("/etc/issue: %s %s" % (name, ver))


        if found:
            name = name.lower().strip()
            if name in ("redhatenterprise","redhat"):
                name="rhel"

            log.debug("Distro name=%s" % name)

            ver = ver.lower().strip()

            if name == "rhel" and ver[0] in ("5","6","7"):
                ver = ver[0] + ".0"

            log.debug("Distro version=%s" % ver)

            found_in_list = False
            for d in self.distros:
                if name.find(d) > -1:
                    self.distro = self.distros[d]['index']
                    found_in_list = True
                else:
                    for x in self.distros[d].get('alt_names', ''):
                        if x and name.find(x) > -1:
                            self.distro = self.distros[d]['index']
                            found_in_list = True
                            break

                if found_in_list:
                    break
            self.distro_version = ver

        else:
            self.distro, self.distro_version = DISTRO_UNKNOWN, '0.0'

        log.debug("distro=%d, distro_version=%s" % (self.distro, self.distro_version))


    def distro_changed(self):
        ppd_install = self.get_distro_ver_data('ppd_install', 'ppd')

        if ppd_install not in ('ppd', 'drv'):
            log.warning("Invalid ppd_install value: %s" % ppd_install)

        self.enable_ppds = (ppd_install == 'ppd')

        log.debug("Enable PPD install: %s (False=drv)" % self.enable_ppds)

        self.ppd_dir = self.get_distro_ver_data('ppd_dir')

        self.drv_dir = self.get_distro_ver_data('drv_dir')
        if not self.enable_ppds and not self.drv_dir:
            log.warning("Invalid drv_dir value: %s" % self.drv_dir)

        self.distro_version_supported = self.get_distro_ver_data('supported', False)
        self.selected_options['fax'] = self.get_distro_ver_data('fax_supported', True)
        self.selected_options['network'] = self.get_distro_ver_data('network_supported', True)
        self.selected_options['scan'] = self.get_distro_ver_data('scan_supported', True)
        self.selected_options['policykit'] = self.get_distro_ver_data('policykit', False)
        self.selected_options['libusb01'] = self.get_distro_ver_data('libusb01', False)
        self.selected_options['udev_sysfs_rule'] = self.get_distro_ver_data('udev_sysfs_rule', False)
        self.native_cups = self.get_distro_ver_data('native_cups', False)

        # Adjust required flag based on the distro ver ui_toolkit value
        ui_toolkit = self.get_distro_ver_data('ui_toolkit',  'qt4').lower()

        if ui_toolkit == 'qt4':
            log.debug("Default UI toolkit: Qt4")
            self.ui_toolkit = 'qt4'
            self.selected_options['gui_qt4'] = True

        # todo: gtk
        else:
            self.selected_options['gui_qt4'] = False

        # Override with --qt4 command args
        if self.enable is not None:
            if 'qt4' in self.enable:
                log.debug("User selected UI toolkit: Qt4")
                self.ui_toolkit = 'qt4'
                self.selected_options['gui_qt4'] = True

        if self.disable is not None:
            if 'qt4' in self.disable:
                log.debug("User deselected UI toolkit: Qt4")
                self.selected_options['gui_qt4'] = False


    def __fixup_data(self, key, data):
        field_type = self.FIELD_TYPES.get(key, TYPE_STRING)
        #log.debug("%s (%s) %d" % (key, data, field_type))

        if field_type == TYPE_BOOL:
            return utils.to_bool(data)

        elif field_type == TYPE_STRING:
            if type('') == type(data):
                return data.strip()
            else:
                return data

        elif field_type == TYPE_INT:
            try:
                return int(data)
            except ValueError:
                return 0

        elif field_type == TYPE_LIST:
            return [x for x in data.split(',') if x]


    def load_distros(self):
        if self.mode  == MODE_INSTALLER:
            distros_dat_file = os.path.join('installer', 'distros.dat')

        elif self.mode == MODE_CREATE_DOCS:
            distros_dat_file = os.path.join('..', '..', 'installer', 'distros.dat')

        else: # MODE_CHECK
            distros_dat_file = os.path.join(prop.home_dir, 'installer', 'distros.dat')

            if not os.path.exists(distros_dat_file):
                log.debug("DAT file not found at %s. Using local relative path..." % distros_dat_file)
                distros_dat_file = os.path.join('installer', 'distros.dat')

        distros_dat = ConfigBase(distros_dat_file)
        distros_list = self.__fixup_data('distros', distros_dat.get('distros', 'distros'))
        log.debug(distros_list)

        for distro in distros_list:
            update_spinner()
            d = {}

            if not distros_dat.has_section(distro):
                log.debug("Missing distro section in distros.dat: [%s]" % distro)
                continue

            for key in distros_dat.keys(distro):
                d[key] = self.__fixup_data(key, distros_dat.get(distro, key))

            self.distros[distro] = d
            versions = self.__fixup_data("versions", distros_dat.get(distro, 'versions'))
            self.distros[distro]['versions'] = {}
            self.distros[distro]['versions_list'] = versions

            for ver in versions:
                same_as_version, supported = False, True
                v = {}
                ver_section = "%s:%s" % (distro, ver)

                if not distros_dat.has_section(ver_section):
                    log.error("Missing version section in distros.dat: [%s:%s]" % (distro, ver))
                    continue

                if 'same_as_version' in distros_dat.keys(ver_section):
                    same_as_version = True

                supported = self.__fixup_data('supported', distros_dat.get(ver_section, 'supported'))

                for key in distros_dat.keys(ver_section):
                    v[key] = self.__fixup_data(key, distros_dat.get(ver_section, key))

                self.distros[distro]['versions'][ver] = v
                self.distros[distro]['versions'][ver]['dependency_cmds'] = {}

                if same_as_version: # or not supported:
                    continue

                for dep in self.dependencies:
                    dd = {}
                    dep_section = "%s:%s:%s" % (distro, ver, dep)

                    if not distros_dat.has_section(dep_section) and not same_as_version:
                        continue

                    #if same_as_version:
                    #    continue

                    for key in distros_dat.keys(dep_section):
                        dd[key] = self.__fixup_data(key, distros_dat.get(dep_section, key))

                    self.distros[distro]['versions'][ver]['dependency_cmds'][dep] = dd

            versions = self.distros[distro]['versions']
            for ver in versions:
                ver_section = "%s:%s" % (distro, ver)

                if 'same_as_version' in distros_dat.keys(ver_section):
                    v = self.__fixup_data("same_as_version", distros_dat.get(ver_section, 'same_as_version'))

                    try:
                        vv = self.distros[distro]['versions'][v].copy()
                        vv['same_as_version'] = v
                        self.distros[distro]['versions'][ver] = vv

                        for key in distros_dat.keys(ver_section):
                           vv[key] = self.__fixup_data(key, distros_dat.get(ver_section, key))

                    except KeyError:
                        log.debug("Missing 'same_as_version=' version in distros.dat for section [%s:%s]." % (distro, v))
                        continue

    def pre_install(self):
        pass


    def pre_depend(self):
        pass


    def check_python2x(self):
        py_ver = sys.version_info
        py_major_ver, py_minor_ver = py_ver[:2]
        log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
        return py_major_ver >= 2


    def check_gcc(self):
        return check_tool('gcc --version', 0) and check_tool('g++ --version', 0)


    def check_make(self):
        return check_tool('make --version', 3.0)


    def check_libusb(self):
        Is_libusb01_enabled = self.get_distro_ver_data('libusb01',False)
        if Is_libusb01_enabled == True:
            if not check_lib('libusb'):
                return False
            if self.distro_name != "rhel":
                return len(locate_file_contains("usb.h", '/usr/include', 'usb_init'))
            else:
                return True
        else:
            if not check_lib('libusb-1.0'):
                return False
            if self.distro_name != "rhel":
                return len(locate_file_contains("libusb.h", '/usr/include/libusb-1.0', 'libusb_init'))
            else:
                return True


    def check_libjpeg(self):
        return check_lib("libjpeg") and check_file("jpeglib.h")


    def check_libcrypto(self):
        return check_lib("libcrypto") and check_file("crypto.h")


    def check_libpthread(self):
        return check_lib("libpthread") and check_file("pthread.h")


    def check_libnetsnmp(self):
        return check_lib("libnetsnmp") and check_file("net-snmp-config.h")


    def check_reportlab(self):
        try:
            log.debug("Trying to import 'reportlab'...")
            import reportlab

            ver = reportlab.Version
            try:
                ver_f = float(ver)
            except ValueError:
                log.debug("Can't determine version.")
                return False
            else:
                log.debug("Version: %.1f" % ver_f)
                if ver_f >= 2.0:
                    log.debug("Success.")
                    return True
                else:
                    return False

        except ImportError:
            log.debug("Failed.")
            return False


    def check_python23(self):
        py_ver = sys.version_info
        py_major_ver, py_minor_ver = py_ver[:2]
        log.debug("Python ver=%d.%d" % (py_major_ver, py_minor_ver))
        return py_major_ver >= 2 and py_minor_ver >= 3


    def check_python_xml(self):
        try:
            import xml.parsers.expat
        except ImportError:
            return False
        else:
            return True


    def check_sane(self):
        return check_lib('libsane')


    def check_sane_devel(self):
        return len(locate_file_contains("sane.h", '/usr/include', 'extern SANE_Status sane_init'))


    def check_xsane(self):
        if os.getenv('DISPLAY'):
            return check_version(get_xsane_version(), '0.9') # will fail if X not running...
#            return check_tool('xsane --version', 0.9) # will fail if X not running...
        else:
            return bool(utils.which("xsane")) # ...so just see if it installed somewhere


    def check_scanimage(self):
        return check_tool('scanimage --version', 1.0)


    def check_gs(self):
        return check_tool('gs -v', 7.05)


    def check_pyqt4(self):
        if self.ui_toolkit == 'qt4':
            try:
                import PyQt4
            except ImportError:
                return False
            else:
                return True

        else:
            return False


    def check_pyqt4_dbus(self):
        if self.ui_toolkit == 'qt4':
            try:
                from dbus.mainloop.qt import DBusQtMainLoop
            except ImportError:
                return False
            else:
                return True
        else:
            return False

    def check_pyqt(self):
        if self.ui_toolkit == 'qt3':
            try:
                import qt
            except ImportError:
                return False
            else:
                return True

        else:
            return False


    def check_python_devel(self):
        return check_file('Python.h')


    def check_pynotify(self):
        try:
            import pynotify
        except ImportError, RuntimeError:
            return False
        return True


    def check_python_dbus(self):
        log.debug("Checking for python-dbus (>= 0.80)...")
        try:
            import dbus
            try:
                ver = dbus.version
                log.debug("Version: %s" % '.'.join([str(x) for x in dbus.version]))
                return ver >= (0,80,0)

            except AttributeError:
                try:
                    ver = dbus.__version__
                    log.debug("Version: %s" % dbus.__version__)
                    log.debug("HPLIP requires dbus version > 0.80.")
                    return False

                except AttributeError:
                    log.debug("Unknown version. HPLIP requires dbus version > 0.80.")
                    return False

        except ImportError:
            return False


    def check_python_ctypes(self):
        try:
            import ctypes
            return True
        except ImportError:
            return False


    def check_dbus(self):
        log.debug("Checking for dbus running and header files present (dbus-devel)...")
        return check_ps(['dbus-daemon'])  and \
            len(locate_file_contains("dbus-message.h", '/usr/include', 'dbus_message_new_signal'))


    def check_cups_devel(self):
        return check_file('cups.h') and bool(utils.which('lpr'))


    def check_cups(self):
        status, output = utils.run('lpstat -r', self.passwordObj)
        if status > 0 or 'not running' in output:
            log.debug("CUPS is not running. %s"%output)
            return False
        else:
            log.debug("CUPS is running. %s "%output)
            return True


    def check_cups_image(self):
      return check_file("raster.h", "/usr/include/cups")


    def check_hplip(self):
        log.debug("Checking for HPLIP...")
        return locate_files('hplip.conf', '/etc/hp')


    def check_libtool(self):
        log.debug("Checking for libtool...")
        return check_tool('libtool --version')


    def check_pil(self):
        log.debug("Checking for PIL...")
        try:
            from PIL import Image
            return True
        except ImportError:
            return False


    def check_cupsddk(self):
        log.debug("Checking for cups-ddk...")
        # TODO: Compute these paths some way or another...
        #return check_tool("/usr/lib/cups/driver/drv list") and os.path.exists("/usr/share/cupsddk/include/media.defs")
        return (check_file('drv', "/usr/lib/cups/driver") or check_file('drv', "/usr/lib64/cups/driver")) and \
            check_file('media.defs', "/usr/share/cupsddk/include")


    def check_policykit(self):
        log.debug("Checking for PolicyKit...")
        if check_file('PolicyKit.conf', "/etc/PolicyKit") and check_file('org.gnome.PolicyKit.AuthorizationManager.service', "/usr/share/dbus-1/services"):
            return True
        elif check_file('50-localauthority.conf', "/etc/polkit-1/localauthority.conf.d") and check_file('org.freedesktop.PolicyKit1.service', "/usr/share/dbus-1/system-services"):
            return True
        elif check_file('org.freedesktop.PolicyKit1.conf','/etc/dbus-1/system.d'):
            return True
        else:
            return False


    def check_cupsext(self):
        log.debug("Checking 'cupsext' CUPS extension...")
        try:
            import cupsext
        except ImportError:
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of cupsext.")
            return False
        else:
            return True


    def check_hpmudext(self):
        log.debug("Checking 'hpmudext' I/O extension...")
        try:
            import hpmudext
        except ImportError:
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of hpmudext.")
            return False
        else:
            return True


    def check_pcardext(self):
        log.debug("Checking 'pcardext' Photocard extension...")
        try:
            import pcardext
        except ImportError:
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of pcardext.")
            return False
        else:
            return True


    def check_hpaio(self):
        found = False
        for path in ['/etc/sane.d/dll.conf','/etc/sane.d/dll.d/hpaio', '/etc/sane.d/dll.d/hplip']:
            log.debug("'Checking for hpaio' in '%s'..." % path)
            try:
                f = file(path, 'r')
            except IOError:
                log.info("'%s' not found." % path)
            else:
                for line in f:
                    lineNoSpace = re.sub(r'\s', '', line) 
                    hpaiomatched=re.match('hpaio',lineNoSpace)
                    if hpaiomatched:
                        found = True
                        break            
            if found:
                break

        if not found:
            log.error("'hpaio' not found in SANE conf files. Is SANE installed?")

        return found

    def update_hpaio(self):
        found = False
        home_dir = sys_conf.get('dirs', 'home')
        pat=re.compile(r"""(\S.*)share\/hplip""")
        usrbin_dir=None
        if pat.match(home_dir) is not None:
            usrlib_dir= pat.match(home_dir).group(1) + "lib/"
            if os.path.exists(usrlib_dir+'sane/libsane-hpaio.so.1'):
                log.debug("'Updating hpaio' in '/etc/sane.d/dll.conf'...")
                try:
                    f = file('/etc/sane.d/dll.conf', 'r')
                except IOError:
                    log.error("'/etc/sane.d/dll.conf' not found. Creating dll.conf file")
#                    f = file('/etc/sane.d/dll.conf', 'a+')
                    cmd = self.passwordObj.getAuthCmd()%'touch /etc/sane.d/dll.conf'
                    log.debug("cmd=%s"%cmd)
                    utils.run(cmd, self.passwordObj)
                else:
                    for line in f:
                        lineNoSpace = re.sub(r'\s', '', line)
                        hpaiomatched=re.match('hpaio',lineNoSpace)
                        if hpaiomatched:
                            found = True
                            break
                    f.close()

                if not found:
                    st = os.stat('/etc/sane.d/dll.conf')
                    cmd= self.passwordObj.getAuthCmd()%'chmod 777 /etc/sane.d/dll.conf'
                    log.debug("cmd=%s"%cmd)
                    utils.run(cmd, self.passwordObj)
                    try:
                        f = file('/etc/sane.d/dll.conf', 'a+')
                    except IOError:
                        log.error("'/etc/sane.d/dll.conf' not found. Creating dll.conf file")
                    else:
                        f.write('hpaio')
                        f.close()
                    actv_permissions = st.st_mode &0777
                    cmd = 'chmod %o /etc/sane.d/dll.conf'%actv_permissions
                    cmd= self.passwordObj.getAuthCmd()%cmd
                    log.debug("cmd=%s"%cmd)
                    utils.run(cmd, self.passwordObj)
        return found

    def check_scanext(self):
        log.debug("Checking 'scanext' SANE scanning extension...")
        found = False
        try:
            import scanext
        except ImportError:
            log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of scanext.")
        else:
            found = True
        return found


    def get_hplip_version(self):
        self.version_description, self.version_public, self.version_internal = '', '', ''

        if self.mode == MODE_INSTALLER:
            ac_init_pat = re.compile(r"""AC_INIT\(\[(.*?)\], *\[(.*?)\], *\[(.*?)\], *\[(.*?)\] *\)""", re.IGNORECASE)

            try:
                config_in = open('./configure.in', 'r')
            except IOError:
                self.version_description, self.version_public, self.version_internal = \
                    '', sys_conf.get('configure', 'internal-tag', '0.0.0'), prop.installed_version
            else:
                for c in config_in:
                    if c.startswith("AC_INIT"):
                        match_obj = ac_init_pat.search(c)
                        self.version_description = match_obj.group(1)
                        self.version_public = match_obj.group(2)
                        self.version_internal = match_obj.group(3)
                        name = match_obj.group(4)
                        break

                config_in.close()

                if name != 'hplip':
                    log.error("Invalid archive!")


        else: # MODE_CHECK
            try:
                self.version_description, self.version_public, self.version_internal = \
                    '', sys_conf.get('configure', 'internal-tag', '0.0.0'), prop.installed_version
            except KeyError:
                self.version_description, self.version_public, self.version_internal = '', '', ''

        return self.version_description, self.version_public, self.version_internal



    def configure(self):
        configure_cmd = './configure'
        configuration = {}
        dbus_avail = self.have_dependencies['dbus'] and self.have_dependencies['python-dbus']
        configuration['network-build'] = self.selected_options['network']
        configuration['fax-build'] = self.selected_options['fax'] and dbus_avail
        configuration['dbus-build'] = dbus_avail
        configuration['qt4'] = self.selected_options['gui_qt4']
        configuration['scan-build'] = self.selected_options['scan']
        configuration['doc-build'] = self.selected_options['docs']
        configuration['policykit'] = self.selected_options['policykit']
        configuration['libusb01_build'] = self.selected_options['libusb01']
        configuration['udev_sysfs_rules'] = self.selected_options['udev_sysfs_rule']

        # Setup printer driver configure flags based on distro data...
        if self.native_cups: # hpcups
            configuration['hpcups-install'] = True
            configuration['hpijs-install'] = False
            configuration['foomatic-ppd-install'] = False
            configuration['foomatic-drv-install'] = False

            if self.enable_ppds:
                configuration['cups-ppd-install'] = True
                configuration['cups-drv-install'] = False
            else:
                configuration['cups-ppd-install'] = False
                configuration['cups-drv-install'] = True

        else: # HPIJS/foomatic
            configuration['hpcups-install'] = False
            configuration['hpijs-install'] = True
            configuration['cups-ppd-install'] = False
            configuration['cups-drv-install'] = False

            if self.enable_ppds:
                configuration['foomatic-ppd-install'] = True
                configuration['foomatic-drv-install'] = False
            else:
                configuration['foomatic-ppd-install'] = False
                configuration['foomatic-drv-install'] = True


        # ... and then override and adjust for consistency with passed in parameters
        if self.enable is not None:
            for c in self.enable:
                if c == 'hpcups-install':
                    configuration['hpijs-install'] = False
                    configuration['foomatic-ppd-install'] = False
                    configuration['foomatic-drv-install'] = False
                elif c == 'hpijs-install':
                    configuration['hpcups-install'] = False
                    configuration['cups-ppd-install'] = False
                    configuration['cups-drv-install'] = False
                elif c == 'foomatic-ppd-install':
                    configuration['foomatic-drv-install'] = False
                elif c == 'foomatic-drv-install':
                    configuration['foomatic-ppd-install'] = False
                elif c == 'cups-ppd-install':
                    configuration['cups-drv-install'] = False
                elif c == 'cups-drv-install':
                    configuration['cups-ppd-install'] = False

        if self.disable is not None:
            for c in self.disable:
                if c == 'hpcups-install':
                    configuration['hpijs-install'] = True
                    configuration['cups-ppd-install'] = False
                    configuration['cups-drv-install'] = False
                elif c == 'hpijs-install':
                    configuration['hpcups-install'] = True
                    configuration['foomatic-ppd-install'] = False
                    configuration['foomatic-drv-install'] = False
                elif c == 'foomatic-ppd-install':
                    configuration['foomatic-drv-install'] = True
                elif c == 'foomatic-drv-install':
                    configuration['foomatic-ppd-install'] = True
                elif c == 'cups-ppd-install':
                    configuration['cups-drv-install'] = True
                elif c == 'cups-drv-install':
                    configuration['cups-ppd-install'] = True

        if self.ppd_dir is not None:
            configure_cmd += ' --with-hpppddir=%s' % self.ppd_dir
            
        libdir_path = self.get_distro_ver_data('libdir_path',False)
        if libdir_path and self.bitness == 64:
            configure_cmd += ' --libdir=%s' % (libdir_path)
        elif self.bitness == 64:
            configure_cmd += ' --libdir=/usr/lib64'

        configure_cmd += ' --prefix=%s' % self.install_location

        if self.get_distro_ver_data('cups_path_with_bitness', False) and self.bitness == 64:
            configure_cmd += ' --with-cupsbackenddir=/usr/lib64/cups/backend --with-cupsfilterdir=/usr/lib64/cups/filter'

        if self.get_distro_ver_data('acl_rules', False):
            configure_cmd += ' --enable-udev-acl-rules'

        if self.enable is not None:
            for c in self.enable:
                configuration[c] = True

        if self.disable is not None:
            for c in self.disable:
                configuration[c] = False

        for c in configuration:
            if configuration[c]:
                configure_cmd += ' --enable-%s' % c
            else:
                configure_cmd += ' --disable-%s' % c

        return configure_cmd

    def configure_html(self):
        configure_cmd = './configure'
        configure_cmd += ' --prefix=/usr' 
        configure_cmd += ' --with-hpppddir=%s' % self.ppd_dir

        if self.bitness == 64:
            configure_cmd += ' --libdir=/usr/lib64'

        self.ui_toolkit =  self.get_distro_ver_data('ui_toolkit') 
        if self.ui_toolkit is not None and self.ui_toolkit == 'qt3':
            configure_cmd += ' --enable-qt3 --disable-qt4'
        else:
            configure_cmd += ' --enable-qt4'

        self.native_cups =  self.get_distro_ver_data('native_cups')
        if self.native_cups is not None and self.native_cups == 1:
            if self.enable_ppds:
                configure_cmd += ' --enable-hpcups-install --disable-cups-drv-install --enable-cups-ppd-install --disable-hpijs-install --disable-foomatic-drv-install --disable-foomatic-ppd-install --disable-foomatic-rip-hplip-install'
            else:
                configure_cmd += ' --enable-hpcups-install --enable-cups-drv-install --disable-cups-ppd-install --disable-hpijs-install --disable-foomatic-drv-install --disable-foomatic-ppd-install --disable-foomatic-rip-hplip-install'
        else:
            configure_cmd += ' --disable-hpcups-install --disable-cups-drv-install --disable-cups-ppd-install --enable-hpijs-install --enable-foomatic-drv-install --enable-foomatic-ppd-install --enable-foomatic-rip-hplip-install' 

        self.fax_supported =  self.get_distro_ver_data('fax_supported')
        if self.fax_supported is None:
            configure_cmd += ' --disable-fax-build --disable-dbus-build'
        else:
	    configure_cmd += ' --enable-fax-build --enable-dbus-build'

        self.network_supported = self.get_distro_ver_data('network_supported')
        if self.network_supported is None:
            configure_cmd += ' --disable-network-build'
	else:
	    configure_cmd += ' --enable-network-build'
          
        self.scan_supported = self.get_distro_ver_data('scan_supported')
        if self.scan_supported is None:
            configure_cmd += ' --disable-scan-build'
	else:
	    configure_cmd += ' --enable-scan-build'
  
        self.policykit = self.get_distro_ver_data('policykit')
        if self.policykit is not None and self.policykit == 1:
            configure_cmd += ' --enable-policykit'
	else:
	    configure_cmd += ' --disable-policykit'

        self.libusb01 = self.get_distro_ver_data('libusb01')
        if self.libusb01 is not None and self.libusb01 == 1:
            configure_cmd += ' --enable-libusb01_build'
	else:
	    configure_cmd += ' --disable-libusb01_build'

        self.udev_sysfs_rule = self.get_distro_ver_data('udev_sysfs_rule')
        if self.udev_sysfs_rule is not None and self.udev_sysfs_rule == 1:
            configure_cmd += ' --enable-udev_sysfs_rules'
	else:
	    configure_cmd += ' --disable-udev_sysfs_rules'

        configure_cmd += ' --enable-doc-build'
	
        return configure_cmd


    def build_cmds(self):
        return [self.configure(),
                'make clean',
                'make',
                self.passwordObj.getAuthCmd() % 'make install']


    def get_distro_ver_data(self, key, default=None,distro_ver=None):
        try:
            if distro_ver:
                return self.distros[self.distro_name]['versions'][distro_ver].get(key, None) or \
                self.distros[self.distro_name].get(key, None) or default
            else:
                return self.distros[self.distro_name]['versions'][self.distro_version].get(key,None) or \
                self.distros[self.distro_name].get(key, None) or default
        except KeyError:
            return default

        return value


    def get_distro_data(self, key, default=None):
        try:
            return self.distros[self.distro_name].get(key, None) or default
        except KeyError:
            return default


    def get_ver_data(self, key, default=None,distro_ver=None):
        try:
            if distro_ver:
                return self.distros[self.distro_name]['versions'][distro_ver].get(key, None) or default
            else:
                return self.distros[self.distro_name]['versions'][self.distro_version].get(key, None) or default

        except KeyError:
            return default

        return value


    def get_dependency_data(self, dependency,supported_distro_vrs=None):
        dependency_cmds = self.get_ver_data("dependency_cmds", {},supported_distro_vrs)
        dependency_data = dependency_cmds.get(dependency, {})
        packages = dependency_data.get('packages', [])
        commands = dependency_data.get('commands', [])
        return packages, commands



    def get_dependency_commands(self):
        dd = self.dependencies.keys()
        dd.sort()
        commands_to_run = []
        packages_to_install = []
        overall_commands_to_run = []
        for d in dd:
            include = False
            for opt in self.dependencies[d][1]:
                if self.selected_options[opt]:
                    include = True
            if include:
                pkgs, cmds = self.get_dependency_data(d)

                if pkgs:
                    for p in pkgs:
                        if not p in packages_to_install:
                            packages_to_install.append(p)

                if cmds:
                    commands_to_run.extend(cmds)

        package_mgr_cmd = self.get_distro_data('package_mgr_cmd')

        overall_commands_to_run.extend(commands_to_run)

        if package_mgr_cmd:
            packages_to_install = ' '.join(packages_to_install)
            overall_commands_to_run.append(utils.cat(package_mgr_cmd))

        if not overall_commands_to_run:
            log.error("No cmds/pkgs")

        return overall_commands_to_run


    def distro_known(self):
        return self.distro != DISTRO_UNKNOWN and self.distro_version != DISTRO_VER_UNKNOWN


    def distro_supported(self):
        if self.mode == MODE_INSTALLER:
            return self.distro != DISTRO_UNKNOWN and self.distro_version != DISTRO_VER_UNKNOWN and self.get_ver_data('supported', False)
        else:
            return True # For docs (manual install)

    def count_num_required_missing_dependencies(self):
        num_req_missing = 0
        for d, desc, opt in self.missing_required_dependencies():
            num_req_missing += 1
        return num_req_missing


    def count_num_optional_missing_dependencies(self):
        num_opt_missing = 0
        for d, desc, req, opt in self.missing_optional_dependencies():
            num_opt_missing += 1
        return num_opt_missing


    def missing_required_dependencies(self): # missing req. deps in req. options
        for opt in self.components[self.selected_component][1]:
            if self.options[opt][0]: # required options
                for d in self.options[opt][2]: # dependencies for option
                    if self.dependencies[d][0]: # required option
                        if not self.have_dependencies[d]: # missing
                            log.debug("Missing required dependency: %s" % d)
                            yield d, self.dependencies[d][2], opt
                            # depend, desc, option

    def missing_optional_dependencies(self):
        # missing deps in opt. options
        for opt in self.components[self.selected_component][1]:
            if not self.options[opt][0]: # not required option
                if self.selected_options[opt]: # only for options that are ON
                    for d in self.options[opt][2]: # dependencies
                        if not self.have_dependencies[d]: # missing dependency
                            log.debug("Missing optional dependency: %s" % d)
                            yield d, self.dependencies[d][2], self.dependencies[d][0], opt
                            # depend, desc, required_for_opt, opt

        # opt. deps in req. options
        for opt in self.components[self.selected_component][1]:
            if self.options[opt][0]: # required options
                for d in self.options[opt][2]: # dependencies for option
                    if d == 'cups-ddk':
                        status, output = utils.run('cups-config --version', self.passwordObj)
                        import string
                        if status == 0 and (string.count(output, '.') == 1 or string.count(output, '.') == 2):
                            if string.count(output, '.') == 1:
                                major, minor = string.split(output, '.', 2)
                            if string.count(output, '.') == 2:
                                major, minor, release = string.split(output, '.', 3)
                            if len(minor) > 1 and minor[1] >= '0' and minor[1] <= '9':
                                minor = ((ord(minor[0]) - ord('0')) * 10) + (ord(minor[1]) - ord('0'))
                            else:
                                minor = ord(minor[0]) - ord('0')
                            if major > '1' or (major == '1' and minor >= 4):
                                continue
                if not self.dependencies[d][0]: # optional dep
                        if not self.have_dependencies[d]: # missing
                            log.debug("Missing optional dependency: %s" % d)
                            yield d, self.dependencies[d][2], self.dependencies[d][0], opt
                            # depend, desc, option

    def select_options(self, answer_callback):
        num_opt_missing = 0
        # not-required options
        for opt in self.components[self.selected_component][1]:
            if not self.options[opt][0]: # not required
                default = 'y'

                if not self.selected_options[opt]:
                    default = 'n'

                self.selected_options[opt] = answer_callback(opt, self.options[opt][1], default)

                if self.selected_options[opt]: # only for options that are ON
                    for d in self.options[opt][2]: # dependencies
                        if not self.have_dependencies[d]: # missing dependency
                            log.debug("Missing optional dependency: %s" % d)
                            num_opt_missing += 1

        return num_opt_missing


    def check_wget(self):
        if utils.which("wget"):
            return True
        else:
            log.debug("wget is not installed")
            return False

    def check_avahi_utils(self):
        if utils.which("avahi-browse"):
            return True
        else:
            log.debug("avahi-browse is not installed")
            return False


    '''
    def check_passwd_util(self):
        if utils.which("gksu"):
            return True
        elif utils.which("kdesu"):
            return True
        elif utils.which("kdesudo"):
            return True
        else:
            log.debug("GUI password gksu/kdesu/kdesudo utility is not installed")
            return False'''


    def run_pre_install(self, callback=None,distro_ver=None):
        pre_cmd = self.get_distro_ver_data('pre_install_cmd',None,distro_ver)
        log.debug(pre_cmd)
        if pre_cmd:
            x = 1
            for cmd in pre_cmd:
                status, output = utils.run(cmd, self.passwordObj)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Pre-install step %d" % x)

                x += 1

            return True

        else:
            return False


    def run_pre_depend(self, callback=None,distro_ver=None):
        pre_cmd = self.get_distro_ver_data('pre_depend_cmd',None,distro_ver)
        log.debug(pre_cmd)
        if pre_cmd:
            x = 1
            for cmd in pre_cmd:
                status, output = utils.run(cmd, self.passwordObj)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Pre-depend step %d" % x)

                x += 1


    def run_post_depend(self, callback=None,distro_ver=None):
        post_cmd = self.get_distro_ver_data('post_depend_cmd',None,distro_ver)
        log.debug(post_cmd)
        if post_cmd:
            x = 1
            for cmd in post_cmd:
                status, output = utils.run(cmd, self.passwordObj)

                if status != 0:
                    log.warn("An error occurred running '%s'" % cmd)

                if callback is not None:
                    callback(cmd, "Post-depend step %d" % x)

                x += 1



    def pre_build(self,distro_ver=None):
        cmds = []
        if self.get_distro_ver_data('fix_ppd_symlink', False,distro_ver):
            cmds.append(self.passwordObj.getAuthCmd() % 'python ./installer/fix_symlink.py')

        return cmds


    def run_pre_build(self, callback=None,distro_ver=None):
        x = 1
        for cmd in self.pre_build(distro_ver):
            status, output = utils.run(cmd, self.passwordObj)
            if callback is not None:
                callback(cmd, "Pre-build step %d"  % x)

            x += 1


    def run_post_build(self, callback=None,distro_ver=None):
        x = 1
        for cmd in self.post_build(distro_ver):
            status, output = utils.run(cmd, self.passwordObj)
            if callback is not None:
                callback(cmd, "Post-build step %d"  % x)

            x += 1


    def post_build(self,distro_ver=None):
        cmds = []
        # Reload DBUS configuration if distro supports it and PolicyKit
        # support installed
        if self.reload_dbus and self.selected_options['policykit']:
            cmds.append(self.passwordObj.getAuthCmd() % "sh /etc/init.d/dbus reload")
            log.debug("Will reload DBUS configuration for PolicyKit support")

        # Kill any running hpssd.py instance from a previous install
        pid_list = get_ps_pid(['hp-systray', 'hpssd'])
        
        kill_cmd = utils.which("kill",True)
        for pid in pid_list:
            log.debug("Found %s for %s process"%(pid, pid_list[pid]))
            kill = kill_cmd + " %s"%pid
            cmds.append(self.passwordObj.getAuthCmd() % kill)

        return cmds


    def remove_hplip(self, callback=None):
        failed = True
        hplip_remove_cmd = self.get_distro_data('hplip_remove_cmd')
        if hplip_remove_cmd:
            if callback is not None:
                callback(hplip_remove_cmd, "Removing old HPLIP version")

            status, output = utils.run(hplip_remove_cmd, self.passwordObj)

            if status == 0:
                self.hplip_present = self.check_hplip()

                if not self.hplip_present:
                    failed = False

        return failed


    def check_password(self):
        self.passwordObj.clearPassword()
        if self.passwordObj.getPassword() == "":
            return False
        else:
            return True


    # PLUGIN HELPERS


    def isErrorPage(self, page):
        """
        Example code from David Mertz' Text Processing in Python.
        Released in the Public Domain.
        """
        err_score = 0.0

        for pat, prob in err_pats.items():
            if err_score > 0.9: break
            if re.search(pat, page):
                err_score += prob

        log.debug("File error page score: %f" % (err_score))

        return err_score > 0.50


    def validate_disto(self):
        if self.distro != DISTRO_UNKNOWN:
            return True
        else:
            return True
    def validate_distro_version(self):
        if self.validate_disto():
            for vers in self.distros[self.distro_name]['versions']:
                if self.distro_version == vers:
                    return True

        return False

    def is_auto_installer_support(self, distro_version = DISTRO_VER_UNKNOWN):
        if not self.distro_name:
            self.get_distro()
            try:
                self.distro_name = self.distros_index[self.distro]
            except KeyError:
                log.debug("Auto installation is not supported as Distro Name can't find for distro index [%d]."%(self.distro))
                return False

        if distro_version == DISTRO_VER_UNKNOWN:
            distro_version = self.distro_version

        if self.distro != DISTRO_UNKNOWN and distro_version != DISTRO_VER_UNKNOWN and self.get_ver_data('supported', False,distro_version):
            log.debug("Auto installation is supported for Distro =%s version =%s "%(self.distro_name, distro_version))
            return True
        else:
            log.debug("Auto installation is not supported for Distro =%s version =%s "%(self.distro_name, distro_version))
            return False


    # Uninstalls the HPLIP package.
    # Input:
    #       mode --> INTERACTIVE_MODE, GUI_MODE
    #
    # Output:
    #       result --> returns True on success.
    def uninstall(self,mode = INTERACTIVE_MODE, callback=None):
        checkSudo = False
        if os.getuid() != 0:
            checkSudo = True
#            log.error("To run 'hp-uninstall' utility, you must have root privileges.")
#            return False

        home_dir= sys_conf.get("dirs","home","")
        version= sys_conf.get("hplip","version","0.0.0")
        if home_dir is "":
            log.error("HPLIP is not installed.")
            return False

        if mode != NON_INTERACTIVE_MODE:
            ok,choice = tui.enter_choice("\nAre you sure to uninstall HPLIP-%s (y=yes, n=no*)?:" %version,['y','n'],'n')
            if not ok or choice == 'n':
                return False

        hplip_remove_cmd = self.get_distro_data('hplip_remove_cmd')
        log.debug("hplip_remove_cmd =%s "%hplip_remove_cmd)
        #read conf file to enter into installed dir
        log.info("Starting uninstallation...")

        plugin_state = sys_state.get('plugin', 'installed', PLUGIN_NOT_INSTALLED)

        # check systray is running?
        status,output = utils.Is_Process_Running('hp-systray')
        if status is True:
            if mode != NON_INTERACTIVE_MODE:
                ok,choice = tui.enter_choice("\nSome HPLIP applications are running. Press 'y' to close and proceed or Press 'n' to quit uninstall (y=yes*, n=no):",['y','n'],'y')
                if not ok or choice =='n':
                    log.info("Quiting HPLIP unininstallation. Close application(s) manually and run again.")
                    return False

            # Kill any running hpssd.py instance from a previous install
            pid_list = get_ps_pid(['hp-systray'])
            kill_cmd = utils.which("kill",True)
            for pid in pid_list:
                log.debug("Found %s for %s process"%(pid, pid_list[pid]))
                kill = kill_cmd + " %s"%pid
                sts, out = utils.run(kill)
                log.debug("sts =%s out=%s"%(sts,out))

        toolbox_status,output = utils.Is_Process_Running('hp-toolbox')
        systray_status,output = utils.Is_Process_Running('hp-systray')
        if toolbox_status is True or systray_status is True:
            log.error("Failed to close HP-Toolbox/HP-Systray. Close manually and run hp-uninstall again.")
            return False

        if hplip_remove_cmd:
            User_exit, Is_pkg_mgr_running = self.close_package_managers()
            if User_exit:
                sys.exit(0)
            self.remove_hplip(callback)

        #removing .hplip directory
        cmd='find /home -name .hplip'
        if checkSudo:
            cmd= self.passwordObj.getAuthCmd() %cmd

        status, output=utils.run(cmd, self.passwordObj)
        if output is not None:
            for p in output.splitlines():
                if p.find("find:") != -1:
                    continue

                utils.remove(p, self.passwordObj, checkSudo)

        #remove the binaries and libraries
        pat=re.compile(r"""(\S.*)share\/hplip""")
        base =pat.match(home_dir)
        usrbin_dir=None
        if base is not None:
            usrbin_dir= base.group(1) + "bin/"
            usrlib_dir= base.group(1) + "lib/"
            cnt = 0
            BINS_LIST_FULL= utils.expandList(BINS_LIST, usrbin_dir)
            while cnt <len (BINS_LIST_FULL ):
                utils.remove(BINS_LIST_FULL[cnt], self.passwordObj, checkSudo)
                cnt += 1

            cnt =0
            LIBS_LIST_FULL = utils.expandList(LIBS_LIST, usrlib_dir)
            while cnt <len (LIBS_LIST_FULL ):
                utils.remove(LIBS_LIST_FULL[cnt], self.passwordObj, checkSudo)
                cnt += 1


        remove_plugins = False
        if mode != NON_INTERACTIVE_MODE and plugin_state !=  PLUGIN_NOT_INSTALLED:
            ok,choice = tui.enter_choice("\nDo you want to remove HP proprietary plug-ins (y=yes*, n=no)?:",['y','n'],'y')
            if ok and choice =='y':
                remove_plugins = True
        else:
            remove_plugins = True

        # removing HPLIP installed directories/files
        if remove_plugins is False:
            HPLIP_LIST_FULL = utils.expandList(HPLIP_LIST, home_dir)
        else:
            HPLIP_LIST_FULL = []
        cnt =0
        while cnt < len(HPLIP_LIST_FULL):
            utils.remove(HPLIP_LIST_FULL[cnt], self.passwordObj, checkSudo)
            cnt +=1

        # removing ppd directory
        ppd_dir = sys_conf.get('dirs','ppd','')
        if ppd_dir:
            utils.remove(ppd_dir, self.passwordObj, checkSudo)

        # removing configuration files
        FILES_LIST_FULL = utils.expandList(FILES_LIST)
        cnt= 0
        while cnt < len(FILES_LIST_FULL):
            utils.remove(FILES_LIST_FULL[cnt], self.passwordObj, checkSudo)
            cnt += 1

        # removing Rules files
        RULES_LIST_FULL = utils.expandList(RULES_LIST, '/etc/udev/rules.d')
        for fl in RULES_LIST_FULL:
            utils.remove(fl, self.passwordObj, checkSudo)

        RULES_LIST_FULL = utils.expandList(RULES_LIST, '/lib/udev/rules.d')
        for fl in RULES_LIST_FULL:
            utils.remove(fl , self.passwordObj, checkSudo)

        # removing (unused) hplip folder from other location 
        cmd = 'find /usr -type d -name hplip'
        cmd = self.passwordObj.getAuthCmd() %cmd
        status, output=utils.run(cmd, self.passwordObj, checkSudo)
        if status == 0:
            hplip_folders = output.splitlines()
            for hplip_d in hplip_folders:
                if hplip_d != home_dir:
                    utils.remove(hplip_d, self.passwordObj, checkSudo)

        # removing all hplip extension libraries
        for ext_f in HPLIP_EXT_LIST:
            if ext_f:
                cmd = 'find /usr -type f -name %s -delete'%ext_f
                cmd = self.passwordObj.getAuthCmd() %cmd
                status,output = utils.run(cmd , self.passwordObj, checkSudo)
                if status != 0:
                    log.warn("Failed to delete %s library  [%s]"%(ext_f,output))

        # removing Plug-in files
        if remove_plugins == True:
            cnt =0
            PLUGIN_LIST_FULL = utils.expandList(PLUGIN_LIST,home_dir)
            while cnt < len(PLUGIN_LIST_FULL):
                utils.remove(PLUGIN_LIST_FULL[cnt], self.passwordObj, checkSudo)
                cnt += 1

            cnt =0
            PLUGIN_STATE_FULL = utils.expandList(PLUGIN_STATE)
            while cnt < len(PLUGIN_STATE_FULL):
                utils.remove(PLUGIN_STATE_FULL[cnt], self.passwordObj, checkSudo)
                cnt += 1

            utils.remove(home_dir, self.passwordObj, checkSudo)

        # removing HPLIP uninstall link
        if usrbin_dir is not None:
            hp_uninstall = usrbin_dir+"hp-unistall"
            utils.remove(hp_uninstall, self.passwordObj, checkSudo)

        log.info("HPLIP uninstallation is completed")
        return True

    # close_package_managers() closes the package managers, if running
    # Input:
    #       MODE --> INTERACTIVE_MODE, GUI_MODE (GUI_MODE is not yet supported).
    # Output:
    #       User_exit (bool) --> returns True, if user quits.
    #                        --> returns False, if user doesn't select quit option.
    #       Is_pkg_mgr_running (bool)  -->returns False, if no packages are running at end of function.
    #                                  -->returns True, if some package(s) is(are) running at end of function.
    def close_package_managers(self, MODE=INTERACTIVE_MODE):
        User_exit = False
        Is_pkg_mgr_running = False
        pid, cmdline = utils.check_pkg_mgr(self.package_mgrs)
        while pid:
            if MODE == INTERACTIVE_MODE:
                ok, user_input = tui.enter_choice("A package manager '%s' appears to be running. Please quit the package manager and press enter to continue (i=ignore, r=retry*, f=force, q=quit) :" % cmdline, ['i', 'r', 'q', 'f'], 'r')
                if not ok:
                    return True, True     #--> User_exit = True , Is_pkg_mgr_running =True
                if user_input == 'i':
                    log.warn("Ignoring running package manager. Some package operations may fail.")
                    break
                if user_input == 'f':
                    ok, ans = tui.enter_yes_no("\nForce quit of package manager '%s'" % cmdline, 'y')
                    if not ok:
                        return True, True     #--> User_exit = True , Is_pkg_mgr_running =True
                    if ans:
                        cmd = self.passwordObj.getAuthCmd() % ("kill %s" % pid)
                        status, output = utils.run(cmd, self.passwordObj)
                        if status != 0:
                            log.error("Failed to kill process. You may need to manually quit the program.")
            else:
                log.error("GUI is not yet supported")
                ## TBD
                break
            pid, cmdline = utils.check_pkg_mgr(self.package_mgrs)

        if pid:     # checking for still running package managers
            Is_pkg_mgr_running = True

        return User_exit, Is_pkg_mgr_running


    #add_groups_to_user()
    # Input:
    #      missing_user_groups (string) --> Contains only missing groups, to show to user.
    #      missing_user_groups_cmd (string) --> command as per distro.dat (i.e. add_user_to_group)
    #      mode  --> INTERACTIVE_MODE, GUI_MODE (GUI_MODE is not yet supported).
    # Output:
    #      ret_val (bool) --> returns True, if succeeded to add groups to user.
    #                     --> returns False, if Failed to add groups to user.
    def add_groups_to_user(self, missing_user_groups, missing_user_groups_cmd ,mode = INTERACTIVE_MODE):       # Move to utils
        ret_val = False
        if mode == INTERACTIVE_MODE:
            if not missing_user_groups or not missing_user_groups_cmd:
                return False

            ok,user_input =tui.enter_choice("Do you want to add missing groups %s to user?(y=yes*, n=no)"%missing_user_groups,['y', 'n'], 'y')
            if ok and user_input == 'y':
                usermod_path= utils.which('usermod',True)
                if usermod_path:
                    cmd = "%s %s %s" % (usermod_path,missing_user_groups_cmd, prop.username)
                    cmd = self.passwordObj.getAuthCmd()%cmd
                    log.debug("cmd =  %s"%cmd)
                    sts,out = utils.run(cmd, self.passwordObj)
                    if sts == 0:
                        ret_val = True
                else:
                    log.error("usermod command not found.")
            else:
                log.info(log.bold("Please add %s groups to %s user"%(missing_user_groups, prop.username)))
        else:
            log.error("GUI is not yet supported")
            ## TBD
        return ret_val


    #disable_SELinux()
    # Input:
    #      MODE  --> INTERACTIVE_MODE, GUI_MODE (GUI_MODE is not yet supported).
    # Output:
    #      ret_val (bool) --> returns True, if succeeded to disable SELinux.
    #                     --> returns False, if Failed to disable SELinux.

    def disable_SELinux(self, mode = INTERACTIVE_MODE):       # Move to utils
        ret_val = False
        SELinux_file = '/etc/selinux/config'
        if mode == INTERACTIVE_MODE:
            ok,user_input =tui.enter_choice("SELinux is currently enabled in your system. Device may not work properly. Do you want to disable SELinux?(y=yes, n=no*)",['y', 'n'], 'n')
            if ok and user_input != 'n':
                if not os.path.exists (SELinux_file):
                    log.debug("File %s is not found"%SELinux_file)
                    return False
                cmd=self.passwordObj.getAuthCmd()%("vi -c %s/enforcing$/disabled -c wq " + SELinux_file)
                log.debug("cmd= %s "%cmd)
                sts, out = utils.run(cmd, self.passwordObj)
                if sts == 0:
                    ret_val = True
                if os.path.exists('/selinux/enforce'):
                    cmd = "echo 0 >/selinux/enforce"
                    cmd=self.passwordObj.getAuthCmd()%cmd
                    log.debug("cmd= %s "%cmd)
#                    utils.run(cmd, self.passwordObj)
                    os_utils.execute(cmd)

        else:
            log.error("GUI is not yet supported")
            ## TBD

        return ret_val


    def install_missing_dependencies(self, mode=INTERACTIVE_MODE, required_dependencies=[],optional_dependencies=[], missing_cmd=[]):     # Move to core_install
        package_mgr_cmd = self.get_distro_data('package_mgr_cmd')
        pre_depend_cmd  = self.get_distro_data('pre_depend_cmd')
        overall_install_cmds={}

        if len(required_dependencies):
            for packages_to_install in required_dependencies:
               if package_mgr_cmd:
                   overall_install_cmds[packages_to_install] = utils.cat(package_mgr_cmd)
               else:
                   overall_install_cmds[packages_to_install] =packages_to_install


        if len(optional_dependencies):
            for packages_to_install in optional_dependencies:
                if package_mgr_cmd:
                    overall_install_cmds[packages_to_install] = utils.cat(package_mgr_cmd)
                else:
                    overall_install_cmds[packages_to_install] = packages_to_install


        if len(overall_install_cmds) == 0 and len(missing_cmd) == 0:
            log.info("No missing dependencies")
            return 0

        if mode == INTERACTIVE_MODE:
            ok,user_input =tui.enter_choice("Do you want to update repository and Install missing/incompatible packages. (a=install all*, c=custom_install, s=skip):",['a', 'c','s'], 'a')
            if not ok or user_input =='q':
                return 1
            elif user_input == 's':
                log.info(log.bold("Install manually above missing/incompatible packages."))
            else:
                self.close_package_managers()

                log.info(log.bold("Updating repository"))
                log.info(log.bold('-'*len("Updating repository")))
                if pre_depend_cmd:
                    for cmd in pre_depend_cmd:
                        log.info("cmd =%s"%(cmd))
                        sts, out = utils.run(cmd, self.passwordObj)
                        if sts != 0  or "Failed" in out:
                            log.warn("Failed to update Repository, check if any update/installation is running.")

                if user_input =='c':
                    log.info(log.bold("Installing missing/incompatible packages"))
                    log.info(log.bold('-'*len("Installing missing/incompatible packages")))
                    for d in overall_install_cmds:
                        ok,user_input =tui.enter_choice("Do you want to install '%s' package?(y=yes*, n=no):"%d,['y', 'n'], 'y')
                        if ok and user_input == 'y':
                            if 'hpaio' in overall_install_cmds[d]:
                                self.update_hpaio()
                            else:
                                log.info("cmd =%s"%overall_install_cmds[d])
                                sts, out = utils.run(overall_install_cmds[d], self.passwordObj)
                                if sts != 0 or "Failed" in out:
                                    log.error("Failed to install '%s' package, please install manually. "%d)
                    if 'cups' in d:
                        if not services.start_service('cups', self.passwordObj):
                            log.error("Failed to start CUPS service. Please start CUPS manually or restart system.")
                    for cmd in missing_cmd:
                        ok,user_input =tui.enter_choice("Do you want to run '%s' command?(y=yes*, n=no):"%d,['y', 'n'], 'y')
                        if ok and user_input == 'y':
                            sts, out = utils.run(cmd, self.passwordObj)
                            if sts != 0 or "Failed" in out:
                                log.error("Failed to run '%s' command, please run manually. "%d)

                elif user_input =='a':
                    log.info(log.bold("Installing Missing/Incompatible packages"))
                    log.info(log.bold('-'*len("Installing Missing/Incompatible packages")))
                    for d in overall_install_cmds:
                        if 'hpaio' in overall_install_cmds[d]:
                            self.update_hpaio()
                        else:
                            log.info("cmd =%s"%overall_install_cmds[d])
                            sts, out = utils.run(overall_install_cmds[d], self.passwordObj)
                            if sts != 0 or "Failed" in out:
                                log.error("Failed to install '%s' package, please install manually. "%d)
                    if 'cups' in d:
                        if not services.start_service('cups',self.passwordObj):
                            log.error("Failed to start CUPS sevice. Please start CUPS manually or restart system.")
                    for cmd in missing_cmd:
                        sts, out = utils.run(cmd, self.passwordObj)
                        if sts != 0 or "Failed" in out:
                            log.error("Failed to run '%s' command, please run manually. "%d)

        else:
            log.error("GUI is not yet supported..1")
            ## TBD

        return 0

