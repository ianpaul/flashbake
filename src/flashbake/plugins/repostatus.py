''' A plugin that adds some information about the status of the project to the context '''
from flashbake.plugins import AbstractMessagePlugin
import subprocess

class Repostats(AbstractMessagePlugin):
    def __init__(self, plugin_spec):
        AbstractMessagePlugin.__init__(self, plugin_spec, True)
        self.define_property('folder', required=False)

    def addcontext(self, message_File, config):
        res1 = self.addignored(self.folder)
        message_file.write(res1)

    def addignored(self, folder="."):
        ignored=subprocess.run(["git", "-C", folder, "status", "-s", "--ignored"], capture_output=True, text=True).stdout.strip("\n")
        x = ignored.splitlines()
        sub = "!"
        res3 = ([s for s in x if sub in s])
        res2 = [elem.replace(sub, '') for elem in res3]
        res1 = ", ".join(res2)
        return res1
    


