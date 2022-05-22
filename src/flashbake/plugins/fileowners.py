''' project status was inspired by @xtaran on GitHub. It includes a number of options to add the current state of your project directory to the commit message. '''

from flashbake.plugins import AbstractMessagePlugin
import subprocess
import os.path

class FileOwners(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, False)
        self.define_property('owners', required=False)
        self.define_property('ignored', required=False)

    def addcontext(self, message_file, config):
        ''' If the owners variable is not present in the config. Write an error message to the config. '''
        if self.owners == None:
            message_file.write('Couldn\'t find the specified directory. Please ensure the config uses an absolute path.')
            return False

        ''' Add owners and groups data for the files and folders in the current directory. '''
        fields = self.__getowners(self.owners)
        for i in range(len(fields)):
            message_file.write("{0} {1} {2}\n".format(fields[i][2], fields[i][3], fields[i][8]))
        
        ''' Add a list of the git repostitory's ignored but present files. '''
        if self.ignored == None:
            message_file.write('Please specify the git directory containing ignored files.')
        else:
            t = self.addignored(self.ignored)
            message_file.write(t)

    def __getowners(self, owners):
        check = subprocess.run(["ls", "-lA", owners], capture_output=True, text=True).stdout.strip("\n")
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

