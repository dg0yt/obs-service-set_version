# Copyright (C) 2015 SUSE Linux GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,USA.


import os
import imp
from ddt import data, ddt, file_data, unpack

from test_base import SetVersionBaseTest

sv = imp.load_source("set_version", "set_version")


@ddt
class SetVersionSpecfile(SetVersionBaseTest):
    """Test set_version service for .spec files"""

    def _write_obsinfo(self, filename, version):
        # debian changelogs can't be created with empty versions
        if not version.strip():
            version = "0~0"
        obsinfo_file = open(filename, "w")
        obsinfo_file.write("name: my_base_name\n")
        obsinfo_file.write("version: %s\n" % version)
        obsinfo_file.write("mtime: 1463080107\n")
        obsinfo_file.write("commit: "
                           "01fcec0959b42a163a7b0a943933488a217f2c9a\n")
        obsinfo_file.close()
        return os.path.join(self._tmpdir, filename)

    def _write_specfile(self, spec_name, spec_tags, custom=[]):
        """write a given filename with the given rpm tags and custom
        strings (i.e. '%define foo bar')"""
        spec_path = os.path.join(self._tmpdir, spec_name)
        with open(spec_path, "a") as f:
            for c in custom:
                f.write("%s\n" % c)
            for key, val in spec_tags.items():
                f.write("%s: %s\n" % (key, val))
            f.write("\n")
        return spec_path

    def test_version_from_obsinfo(self):
        obsinfo = self._write_obsinfo("test.obsinfo", "0.0.1")
        files = [obsinfo]
        vdetector = sv.VersionDetector(None, files, '')
        ver = vdetector._get_version_via_obsinfo()
        self.assertEqual(ver, "0.0.1")

    @file_data("data_test_from_commandline.json")
    def test_from_commandline(self, data):
        old_version, new_version = data
        spec_path = self._write_specfile("test.spec", {"Version": old_version})
        self._run_set_version(params=['--version', new_version])
        self._check_file_assert_contains(spec_path, new_version)

    @file_data("data_test_from_commandline_with_single_file.json")
    def test_from_commandline_with_single_file(self, data):
        spec_tags, new_version, spec_file, other_spec_files = data
        """only a single .spec file should contain the given version"""
        spec_path = self._write_specfile(spec_file, spec_tags)
        # other spec file which shouldn't be updated
        other_spec_path = []
        for s in other_spec_files:
            other_spec_path.append(self._write_specfile(s, spec_tags))
        self._run_set_version(params=["--version", new_version,
                                      "--file", spec_file])
        # our given spec should have the version
        self._check_file_assert_contains(spec_path, new_version)
        # all others shouldn't
        for s in other_spec_path:
            self._check_file_assert_not_contains(s, new_version)

    @file_data("data_test_from_commandline_with_multiple_files.json")
    def test_from_commandline_with_multiple_files(self, data):
        """all .spec files should contain the given version"""
        spec_tags, new_version, spec_files = data
        spec_path = []
        for s in spec_files:
            spec_path.append(self._write_specfile(s, spec_tags))
        self._run_set_version(params=["--version", new_version])
        for s in spec_path:
            self._check_file_assert_contains(s, new_version)

    @file_data("data_test_from_tarball_with_single_file.json")
    def test_from_tarball_with_single_file(self, data):
        tarball_name, tarball_dirs, old_version, expected_version = data
        spec_path = self._write_specfile("test.spec",
                                         {"Name": "foo",
                                          "Version": old_version,
                                          "Group": "AnyGroup"})
        self._write_tarfile(tarball_name, tarball_dirs, [])
        self._run_set_version()
        self._check_file_assert_contains(spec_path, expected_version)
        self._check_file_assert_contains(spec_path, "Name: foo")
        self._check_file_assert_contains(spec_path, "Group: AnyGroup")

    @file_data("data_test_from_tarball_with_single_file.json")
    def test_from_obsinfo(self, data):
        tarball_name, tarball_dirs, old_version, expected_version = data
        self._write_obsinfo("test.obsinfo", expected_version)
        spec_path = self._write_specfile("test.spec",
                                         {"Name": "foo",
                                          "Version": old_version,
                                          "Group": "AnyGroup"})
        self._run_set_version()
        self._check_file_assert_contains(spec_path, expected_version)
        self._check_file_assert_contains(spec_path, "Name: foo")
        self._check_file_assert_contains(spec_path, "Group: AnyGroup")

    @file_data("data_test_from_tarball_with_basename_with_multiple_files.json")
    def test_from_tarball_with_basename_with_multiple_files(self, data):
        tarball_name, tarball_dirs, expected_version, spec_files = data
        spec_path = []
        for s in filter(lambda x: x.endswith(".spec"), spec_files):
            spec_path.append(self._write_specfile(s, {"Version": "UNKNOWN"}))
        self._write_tarfile(tarball_name, tarball_dirs, [])
        self._run_set_version(["--basename", "testprog"])
        for s in spec_path:
            self._check_file_assert_contains(s, expected_version)

    @file_data("data_test_from_tarball_with_basename.json")
    def test_from_tarball_with_basename(self, data):
        tarball_name, tarball_dirs, expected_version = data
        spec_path = self._write_specfile("test.spec", {"Version": "UNKNOWN"})
        self._write_tarfile(tarball_name, tarball_dirs, [])
        self._run_set_version(["--basename", "testprog"])
        self._check_file_assert_contains(spec_path, expected_version)

    @data(
        (
            "test.spec",
            "test-master.tar", [],
            ["test-5.0.0.0b2dev188/test.egg-info/PKG-INFO"],
            "5.0.0.0b2dev188",
            "5.0.0.0~b2~dev188"
        )
    )
    @unpack
    def test_python_package_from_tarball_with_single_file(
            self, spec_file, tar_name, tar_dirs, tar_files,
            org_version, conv_version):
        spec_path = self._write_specfile(
            spec_file, {"Name": "test",
                        "Version": "UNKNOWN",
                        "Group": "AnyGroup"},
            ["%define foo bar"])
        self._write_tarfile(tar_name, tar_dirs, tar_files)
        self._run_set_version()
        self._check_file_assert_contains(
            spec_path, "Version: %s" % conv_version)
        self._check_file_assert_contains(
            spec_path, "define version_unconverted %s" % org_version)
        self._check_file_assert_contains(
            spec_path, "Name: test")
        self._check_file_assert_contains(
            spec_path, "Group: AnyGroup")
        self._check_file_assert_contains(
            spec_path, "%define foo bar")
        self._check_file_assert_not_contains(spec_path, "UNKNOWN")

    @data(
        (
            "test.spec",
            [
                "Version: 1.2.3",
                "Name: test",
                "%define component test",
                "%setup -p -n %{component}-%{version}"
            ],
            [
                "Version: 5.0.0.0~b2~dev188",
                "%define version_unconverted 5.0.0.0b2dev188",
                "",
                "Name: test",
                "%define component test",
                "%setup -p -n %{component}-%{version_unconverted}"
            ],
            "test-master.tar",
            [],
            ["test-5.0.0.0b2dev188/test.egg-info/PKG-INFO"]
        ),
        (
            "test.spec",
            [
                "Version: 1.2.3",
                "Name: test",
                "%define component version",
                "%setup -p -n %{component}-%{version}-foobar"
            ],
            [
                "Version: 5.0.0.0~b2~dev188",
                "%define version_unconverted 5.0.0.0b2dev188",
                "",
                "Name: test",
                "%define component version",
                "%setup -p -n %{component}-%{version_unconverted}-foobar"
            ],
            "test-master.tar",
            [],
            ["test-5.0.0.0b2dev188/test.egg-info/PKG-INFO"]
        ),
        (
            "test.spec",
            [
                "Version: 5.0.0.0~b2~dev188",
                "%define version_unconverted 5.0.0.0b2dev188",
            ],
            [
                "Version: 5.1.0",
                "%define version_unconverted 5.1.0",
            ],
            "test-master.tar",
            [],
            ["test-5.1.0/test.egg-info/PKG-INFO"]
        ),
        (
            "test.spec",
            [
                "Version: 1.2.3",
                "Name: test",
                "%define component test",
                "%setup -p -n %{component}-%{version}"
            ],
            [
                "Version: 5.0.0",
                "Name: test",
                "%define component test",
                "%setup -p -n %{component}-%{version}"
            ],
            "test-master.tar",
            [],
            ["test-5.0.0/test.egg-info/PKG-INFO"]
        ),
    )
    @unpack
    def test_python_package(
            self, spec_file, spec_lines, expected_spec_lines,
            tar_name, tar_dirs, tar_files):
        fn = os.path.join(self._tmpdir, spec_file)
        with open(fn, "w") as f:
            f.write("\n".join(spec_lines))
        self._write_tarfile(tar_name, tar_dirs, tar_files)
        self._run_set_version()
        # check
        with open(fn, "r") as f:
            current_lines = f.read().split("\n")
            self.assertEqual(len(current_lines), len(expected_spec_lines))
            for nbr, l in enumerate(current_lines):
                self.assertEqual(l, expected_spec_lines[nbr])
