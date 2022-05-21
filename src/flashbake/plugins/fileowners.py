''' project status was inspired by @xtaran on GitHub. It includes a number of options to add the current state of your project directory to the commit message. '''

from flashbake.plugins import AbstractMessagePlugin
import subprocess

class Ownership(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('owners_and_groups', str, False, default='.')

    def addcontext(self, message_file, config):
        ''' Add owners and groups data for the files and folders in the current directory. '''
        check = subprocess.run(["ls", "-lA", self.owners_and_groups], capture_output=True, text=True).stdout.strip("\n")
        for line in check.splitlines()[1:]:
            fields = line.split()
            message_file.write("{0} {1} {2}\n".format(fields[2], fields[3], fields[8])) 
        if self.owners_and_groups == None:
            message_file.write('Couldn\'t find the specified directory. Please ensure the config uses an absolute path.')
            return False

