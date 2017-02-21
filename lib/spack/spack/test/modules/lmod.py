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

import pytest

import spack.modules.lmod

mpich_spec_string = 'mpich@3.0.4'
mpileaks_spec_string = 'mpileaks'
libdwarf_spec_string = 'libdwarf arch=x64-linux'

#: Class of the writer tested in this module
writer_cls = spack.modules.lmod.LmodModulefileWriter


@pytest.fixture(params=[
    'clang@3.3',
    'gcc@4.5.0'
])
def compiler(request):
    return request.param


@pytest.fixture(params=[
    ('mpich@3.0.4', ('mpi',)),
    ('openblas@0.2.15', ('blas',)),
    ('openblas-with-lapack@0.2.15', ('blas', 'lapack'))
])
def provider(request):
    return request.param


@pytest.mark.usefixtures('config', 'builtin_mock',)
class TestLmod(object):

    def test_file_layout(
            self, compiler, provider, factory, patch_configuration
    ):
        """Tests the layout of files in the hierarchy is the one expected."""
        patch_configuration('complex_hierarchy')
        spec_string, services = provider
        module, spec = factory(spec_string + '%' + compiler)

        layout = module.layout

        # Check that the services provided are in the hierarchy
        for s in services:
            assert s in layout.conf.hierarchy_tokens

        # Check that the compiler part of the path has no hash and that it
        # is transformed to r"Core" if the compiler is listed among core
        # compilers
        if compiler == 'clang@3.3':
            assert 'Core' in layout.available_path_parts
        else:
            assert compiler.replace('@', '/') in layout.available_path_parts

        # Check that the provider part instead has always an hash even if
        # hash has been disallowed in the configuration file
        path_parts = layout.available_path_parts
        service_part = spec_string.replace('@', '/')
        service_part = '-'.join([service_part, layout.spec.dag_hash(length=7)])
        assert service_part in path_parts

        # Check that multi-providers have repetitions in path parts
        repetitions = len([x for x in path_parts if service_part == x])
        if spec_string == 'openblas-with-lapack@0.2.15':
            assert repetitions == 2
        else:
            assert repetitions == 1

    def test_simple_case(self, modulefile_content, patch_configuration):
        """Tests the generation of a simple TCL module file."""

        patch_configuration('autoload_direct')
        content = modulefile_content(mpich_spec_string)

        assert '-- -*- lua -*-' in content
        assert 'whatis([[Name : mpich]])' in content
        assert 'whatis([[Version : 3.0.4]])' in content
        assert 'family("mpi")' in content

    def test_autoload_direct(self, modulefile_content, patch_configuration):
        """Tests the automatic loading of direct dependencies."""

        patch_configuration('autoload_direct')
        content = modulefile_content(mpileaks_spec_string)

        assert len([x for x in content if 'if not isloaded(' in x]) == 2
        assert len([x for x in content if 'load(' in x]) == 2

        # The configuration file doesn't set the verbose keyword
        # that defaults to False
        messages = [x for x in content if 'LmodMessage("Autoloading' in x]
        assert len(messages) == 0

    def test_autoload_all(self, modulefile_content, patch_configuration):
        """Tests the automatic loading of all dependencies."""

        patch_configuration('autoload_all')
        content = modulefile_content(mpileaks_spec_string)

        assert len([x for x in content if 'if not isloaded(' in x]) == 5
        assert len([x for x in content if 'load(' in x]) == 5

        # The configuration file sets the verbose keyword to True
        messages = [x for x in content if 'LmodMessage("Autoloading' in x]
        assert len(messages) == 5

    def test_alter_environment(self, modulefile_content, patch_configuration):
        """Tests modifications to run-time environment."""

        patch_configuration('alter_environment')
        content = modulefile_content('mpileaks platform=test target=x86_64')

        assert len(
            [x for x in content if x.startswith('prepend_path("CMAKE_PREFIX_PATH"')]  # NOQA: ignore=E501
        ) == 0
        assert len([x for x in content if 'setenv("FOO", "foo")' in x]) == 1
        assert len([x for x in content if 'unsetenv("BAR")' in x]) == 1

        content = modulefile_content(
            'libdwarf %clang platform=test target=x86_32'
        )

        assert len(
            [x for x in content if x.startswith('prepend-path("CMAKE_PREFIX_PATH"')]  # NOQA: ignore=E501
        ) == 0
        assert len([x for x in content if 'setenv("FOO", "foo")' in x]) == 0
        assert len([x for x in content if 'unsetenv("BAR")' in x]) == 0

    def test_blacklist(self, modulefile_content, patch_configuration):
        """Tests blacklisting the generation of selected modules."""

        patch_configuration('blacklist')
        content = modulefile_content(mpileaks_spec_string)

        assert len([x for x in content if 'if not isloaded(' in x]) == 1
        assert len([x for x in content if 'load(' in x]) == 1

    def test_no_hash(self, factory, patch_configuration):
        """Makes sure that virtual providers (in the hierarchy) always
        include a hash. Make sure that the module file for the spec
        does not include a hash if hash_length is 0.
        """

        patch_configuration('no_hash')
        module, spec = factory(mpileaks_spec_string)
        path = module.layout.filename
        mpi_spec = spec['mpi']

        mpiElement = "{0}/{1}-{2}/".format(
            mpi_spec.name, mpi_spec.version, mpi_spec.dag_hash(length=7)
        )

        assert mpiElement in path

        mpileaks_spec = spec
        mpileaks_element = "{0}/{1}.lua".format(
            mpileaks_spec.name, mpileaks_spec.version
        )

        assert path.endswith(mpileaks_element)

    @pytest.mark.usefixtures('update_template_dirs')
    def test_override_template_in_package(
            self, modulefile_content, patch_configuration
    ):
        """Tests overriding a template from and attribute in the package."""

        patch_configuration('autoload_direct')
        content = modulefile_content('override-module-templates')

        assert 'Override successful!' in content

    @pytest.mark.usefixtures('update_template_dirs')
    def test_override_template_in_modules_yaml(
            self, modulefile_content, patch_configuration
    ):
        """Tests overriding a template from `modules.yaml`"""
        patch_configuration('override_template')

        content = modulefile_content('override-module-templates')
        assert 'Override even better!' in content

        content = modulefile_content('mpileaks arch=x86-linux')
        assert 'Override even better!' in content
