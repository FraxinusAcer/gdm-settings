import os

from .utils import run_on_host
from .env import TEMP_DIR


class NoCommandsFoundError(Exception): pass


class ProcessReturnCode(int):
    '''
    An integer that represents return code of a process

    bool(instance) returns True if value of instance is 0
    '''

    def __bool__ (self):
        return True if self == 0 else False

    @property
    def success (self):
        return bool(self)

    @property
    def failure (self):
        return not self.success


class CommandElevator:
    """ Runs a list of commands with elevated privileges """
    def __init__(self, *, shebang='#!/bin/sh') -> None:
        self._list = []
        self.shebang = shebang

    @property
    def empty (self):
        return True if len(self._list) == 0 else False

    def add(self, command, /):
        """ Add a new command to the list """

        if isinstance(command, list):
            command = ' '.join(command)

        return self._list.append(command)

    def clear(self):
        """ Clear command list """
        return self._list.clear()

    def run_only(self) -> bool:
        """ Run commands but DO NOT clear command list """

        returncode = 0
        if len(self._list):
            os.makedirs(TEMP_DIR, exist_ok=True)
            script_file = f"{TEMP_DIR}/run-elevated"
            with open(script_file, "w") as open_script_file:
                print(self.shebang, *self._list, sep="\n", file=open_script_file)
            os.chmod(path=script_file, mode=0o755)
            returncode = run_on_host(['pkexec', script_file]).returncode
            os.remove(script_file)

        return ProcessReturnCode(returncode)

    def run(self) -> bool:
        """ Run commands and clear command list"""

        if self.empty:
            raise NoCommandsFoundError(1, f'{self.__class__.__name__} instance has no commands to run')

        status = self.run_only()
        self.clear()
        return status
