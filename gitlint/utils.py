# Copyright 2013-2014 Sebastian Kreft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Common function used across modules."""

import io
import os
import re
import sys

# This can be just pathlib when 2.7 and 3.4 support is dropped.
import pathlib2 as pathlib


# copy from python3, shutil.which
def which(cmd, mode=os.F_OK | os.X_OK, path=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.

    `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
    of os.environ.get("PATH"), or can be overridden with a custom search
    path.

    """

    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(filename, mode):
        return (os.path.exists(filename) and os.access(filename, mode)
                and not os.path.isdir(filename))

    # If we're given a path with a directory part, look it up directly rather
    # than referring to PATH directories. This includes checking relative to the
    # current directory, e.g. ./script
    if os.path.dirname(cmd):
        if _access_check(cmd, mode):
            return cmd
        return None

    if path is None:
        path = os.environ.get("PATH", os.defpath)
    if not path:
        return None
    path = path.split(os.pathsep)

    import sys
    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        # If it does match, only test that one, otherwise we have to try
        # others.
        if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
            files = [cmd]
        else:
            files = [cmd + ext for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dirname in path:
        normdir = os.path.normcase(dirname)
        if not normdir in seen:
            seen.add(normdir)
            for thefile in files:
                name = os.path.join(dirname, thefile)
                if _access_check(name, mode):
                    return name
    return None


def filter_lines(lines, filter_regex, groups=None):
    """Filters out the lines not matching the pattern.

    Args:
      lines: list[string]: lines to filter.
      pattern: string: regular expression to filter out lines.

    Returns: list[string]: the list of filtered lines.
    """
    pattern = re.compile(filter_regex)
    for line in lines:
        match = pattern.search(line)
        if match:
            if groups is None:
                yield line
            elif len(groups) == 1:
                yield match.group(groups[0])
            else:
                matched_groups = match.groupdict()
                yield tuple(matched_groups.get(group) for group in groups)


def programs_not_in_path(programs):
    """Returns all the programs that are not found in the PATH."""
    return [program for program in programs if not which(program)]


def _open_for_write(filename):
    """Opens filename for writing, creating the directories if needed."""
    dirname = os.path.dirname(filename)
    pathlib.Path(dirname).mkdir(parents=True, exist_ok=True)

    return io.open(filename, 'w')


def _get_cache_filename(name, filename):
    """Returns the cache location for filename and linter name."""
    filename = os.path.abspath(filename)
    filename = os.path.splitdrive(filename)[1]
    filename = filename.lstrip(os.path.sep)
    home_folder = os.path.expanduser('~')
    base_cache_dir = os.path.join(home_folder, '.git-lint', 'cache')

    return os.path.join(base_cache_dir, name, filename)


def get_output_from_cache(name, filename):
    """Returns the output from the cache if still valid.

    It checks that the cache file is defined and that its modification time is
    after the modification time of the original file.

    Args:
      name: string: name of the linter.
      filename: string: path of the filename for which we are retrieving the
        output.

    Returns: a string with the output, if it is still valid, or None otherwise.
    """
    cache_filename = _get_cache_filename(name, filename)
    if (os.path.exists(cache_filename)
            and os.path.getmtime(filename) < os.path.getmtime(cache_filename)):
        with io.open(cache_filename) as f:
            return f.read()

    return None


def save_output_in_cache(name, filename, output):
    """Saves output in the cache location.

    Args:
      name: string: name of the linter.
      filename: string: path of the filename for which we are saving the output.
      output: string: full output (not yet filetered) of the lint command.
    """
    cache_filename = _get_cache_filename(name, filename)
    with _open_for_write(cache_filename) as f:
        f.write(output)
