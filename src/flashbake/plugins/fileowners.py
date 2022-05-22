#    Copyright 2022 Ian Paul
#    Copyright 2009 Thomas Gideon
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

''' project status was inspired by @xtaran on GitHub. It adds information about the current state of the project directory to the commit message. '''

from flashbake.plugins import AbstractMessagePlugin
import subprocess

class FileOwners(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.define_property('owners', required=False) '''Adds owner, group, and last modified time stamp to the commit message for each file in the specified directory.'''
        self.define_property('ignored', required=False) '''This option adds to the commit message a list of all present but ignored files in the specified directory.'''

    def addcontext(self, message_file, config):
        ''' If the owners variable is not present in the config. Write an error message to the config. '''
        if self.owners == None:
            message_file.write('Couldn\'t find the specified directory. Please ensure the config uses an absolute path.')
            return False

        ''' Add owners and groups data for the files and folders in the current directory. '''
        fields = self.__getowners(self.owners)
        for i in range(len(fields)):
            message_file.write("{0} {1} {2} {3} {4}\n".format(fields[i][2], fields[i][3], fields[i][5], fields[i][6], fields[i][7]))
        
        ''' Add a list of the git repostitory's ignored but present files. '''
        if self.ignored == None:
            message_file.write('Please specify the git directory containing ignored files.')
        else:
            t = self.addignored(self.ignored)
            message_file.write(t)

    def __getowners(self, owners):
        check = subprocess.run(["ls", "-lAt", "--time-style=long-iso", owners], capture_output=True, text=True).stdout.strip("\n")
        fields = []
        for line in check.splitlines()[1:]:
            x = line.split()
            fields.append(x)
        return fields 

    def addignored(self, ignored):
        fldr=subprocess.run(["git", "-C", ignored, "status", "-s", "--ignored"], capture_output=True, text=True).stdout.strip("\n")
        x = fldr.splitlines()
        sub = "!"
        g = ([s for s in x if sub in s])
        i = [elem.replace(sub, '') for elem in g]
        t = ", ".join(i)
        return t

