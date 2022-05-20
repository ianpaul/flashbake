''' project status was inspired by @xtaran on GitHub. It includes a number of options to add the current state of your project directory to the commit message. '''

from flashbake.plugins import AbstractMessagePlugin

class Projstat(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('owners_and_groups', required=False)
        self.define_property('ignored_files', required=False)
        self.define_property('time_stamps', required=False)
        self.define_property('last_log_info', required=False)

    def addcontext(self, message_file, config):
        ''' Add the specified items to the commit context. '''
        fields = self.__getowners(self.owners_and_groups)
        if len(fields) > 0:
            message_file.write(fields[2], fields[3], fields[8])
        else:
            message_file.write('Couldn\'t find the specified folder. Please ensure the config uses an absolute path.')
        return True
 
    def __getowners(self, owners_and_groups):
        check = subprocess.run(["ls", "-lA", owners_and_groups], capture_output=True, text=True).stdout.strip("\n")
        for line in check.splitlines()[1:]:
            fields = line.split()
            return fields
