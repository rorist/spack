##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the LICENSE file for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################
"""This module implements the classes necessary to generate TCL
non-hierarchical modules.
"""
import os.path
import string

import llnl.util.tty as tty

from . import common

#: TCL specific part of the configuration
configuration = common.configuration.get('tcl', {})

#: Caches the configuration {spec_hash: configuration}
configuration_registry = {}


def make_configuration(spec):
    """Returns the tcl configuration for spec"""
    key = spec.dag_hash()
    try:
        return configuration_registry[key]
    except KeyError:
        return configuration_registry.setdefault(key, TclConfiguration(spec))


def make_layout(spec):
    """Returns the layout information for spec """
    conf = make_configuration(spec)
    return TclFileLayout(conf)


def make_context(spec):
    """Returns the context information for spec"""
    conf = make_configuration(spec)
    return TclContext(conf)


class TclConfiguration(common.BaseConfiguration):
    """Configuration class for tcl module files."""

    @property
    def conflicts(self):
        """Conflicts for this module file"""
        return self.conf.get('conflict', [])


class TclFileLayout(common.BaseFileLayout):
    """File layout for tcl module files."""

    #: file extension for tcl module files
    extension = 'tcl'


class TclContext(common.BaseContext):
    """Context class for tcl module files."""
    fields = [
        'timestamp',
        'spec',
        'short_description',
        'long_description',
        'autoload',
        'prerequisites',
        'environment_modifications',
        'conflicts',
        'verbose'
    ]

    @property
    def prerequisites(self):
        """List of modules that needs to be loaded automatically."""
        return self._create_module_list_of('specs_to_prereq')

    @property
    def conflicts(self):
        """List of conflicts for the tcl module file."""
        l = []
        naming_scheme = self.conf.naming_scheme
        f = string.Formatter()
        for item in self.conf.conflicts:
            if len([x for x in f.parse(item)]) > 1:
                for naming_dir, conflict_dir in zip(
                        naming_scheme.split('/'), item.split('/')
                ):
                    if naming_dir != conflict_dir:
                        message = 'conflict scheme does not match naming '
                        message += 'scheme [{spec}]\n\n'
                        message += 'naming scheme   : "{nformat}"\n'
                        message += 'conflict scheme : "{cformat}"\n\n'
                        message += '** You may want to check your '
                        message += '`modules.yaml` configuration file **\n'
                        tty.error(message.format(spec=self.spec,
                                                 nformat=naming_scheme,
                                                 cformat=item))
                        raise SystemExit('Module generation aborted.')
                item = self.spec.format(item)
            l.append(item)
        # Substitute spec tokens if present
        return [self.spec.format(x) for x in l]


class TclModulefileWriter(common.BaseModuleFileWriter):
    """Writer class for tcl module files."""
    templates = [
        # TODO: add more specialized classes here
        os.path.join('modules', 'modulefile.tcl')
    ]
