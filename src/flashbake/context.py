#    copyright 2009 Thomas Gideon
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

'''  context.py - Build up some descriptive context for automatic commit to git'''

import os
import os.path
import tempfile
import logging



def buildmessagefile(config):
    """ Build a commit message that uses the provided ControlConfig object and
        return a reference to the resulting file. """
    config.init()

    fd, msg_filename = tempfile.mkstemp(prefix='git_msg_', suffix='.txt')
    os.close(fd)

    connectable = False
    connected = False

    message_file = open(msg_filename, 'w')
    try:
        for plugin in config.msg_plugins:
            plugin_success = plugin.addcontext(message_file, config)
            # let each plugin say which ones attempt network connections
            if plugin.connectable:
                connectable = True
                connected = connected or plugin_success
        if connectable and not connected:
            logging.error('All of the plugins that use the network failed.\n')
            logging.error('Your computer may not be connected to the network.')
    finally:
        message_file.close()
    return msg_filename
