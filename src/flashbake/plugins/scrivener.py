#    copyright 2009-2011 Thomas Gideon, Jason Penney
#
#    This file is part of flashbake.
#
#    flashbake is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    flashbake is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with flashbake.  If not, see <http://www.gnu.org/licenses/>.

'''   scrivener.py - Scrivener flashbake plugin
by Jason Penney, jasonpenney.net'''

from flashbake.plugins import AbstractFilePlugin
from flashbake.plugins import AbstractMessagePlugin
from flashbake.plugins import PluginError

import flashbake #@UnusedImport
import fnmatch
import glob
import logging
import os
import os.path
import xml.etree.ElementTree as et
from flashbake.compat import relpath

def find_scrivener_projects(hot_files, config, flush_cache=False):
    if flush_cache:
        config.scrivener_projects = None

    if config.scrivener_projects == None:
        scrivener_projects = list()
        for f in hot_files.control_files:
            if fnmatch.fnmatch(f, '*.scriv'):
                scrivener_projects.append(f)

        config.scrivener_projects = scrivener_projects

    return config.scrivener_projects


def find_scrivener_project_contents(hot_files, scrivener_project):
    for path, dirs, files in os.walk(os.path.join(  # @UnusedVariable
            hot_files.project_dir, scrivener_project)):
        rpath = relpath(path, hot_files.project_dir)
        for filename in files:
            yield os.path.join(rpath, filename)


def get_logfile_name(scriv_proj_dir):
    return os.path.join(os.path.dirname(scriv_proj_dir),
                        ".%s.flashbake.wordcount" % os.path.basename(
                            scriv_proj_dir))


## TODO: deal with deleted files
class ScrivenerFile(AbstractFilePlugin):

    def __init__(self, plugin_spec):
        AbstractFilePlugin.__init__(self, plugin_spec)
        self.share_property('scrivener_projects')

    def pre_process(self, hot_files, config):
        for f in find_scrivener_projects(hot_files, config):
            logging.debug("ScrivenerFile: adding '%s'" % f)
            for hotfile in find_scrivener_project_contents(hot_files, f):
                #logging.debug(" - %s" % hotfile)
                hot_files.control_files.add(hotfile)

    def post_process(self, to_commit, hot_files, config):
        flashbake.commit.purge(config, hot_files)

class ScrivenerWordCount(AbstractMessagePlugin):
    """ Add word count for Scrivener project to commit message """

    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.define_property('scrivx')

    def addcontext(self, message_file, config):
        parser = et.XMLParser(encoding="utf-8")
        tree = et.parse(self.scrivx, parser=parser)
        root = tree.getroot()
        for RecentWritingHistory in root.iter('DraftWordCount'):
            message_file.write(f'Total word count: {RecentWritingHistory.text}\n')
        for RecentWritingHistory in root.iter('OtherWordCount'):
            message_file.write(f'Total word count for notes and other items: {RecentWritingHistory.text}\n')
    