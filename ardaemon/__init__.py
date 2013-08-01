__author__ = 'ardevelop'

import os
import sys
import pwd
import grp
import time
import signal
import fcntl
import threading
import multiprocessing
import argparse

ERROR_MESSAGE_PATTERN = "ERROR: %s"
WARNING_MESSAGE_PATTERN = "WARNING: %s"

START = "start"
STOP = "stop"
RESTART = "restart"
ACTIONS = [START, STOP, RESTART]

try:
    from setproctitle import setproctitle
except ImportError:
    sys.stderr.write(WARNING_MESSAGE_PATTERN % "No module \"setproctitle\"\n")

    def setproctitle(title):
        pass


class Daemon:
    def __init__(self, name=None, pid_path="/var/run", title=None, user=None, group=None, parser=None,
                 stdout=os.devnull, stdin=os.devnull, stderr=os.devnull):

        path, executable = os.path.split(os.path.abspath(sys.argv[0]))
        name = name or os.path.splitext(executable)[0]

        self.pid_file = os.path.join(pid_path or path, "%s.pid" % name)
        self.working_directory = path
        self.title = title
        self.user = user
        self.group = group
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.parser = parser
        self.daemon = False

    def __enter__(self):
        parser = self.parser or argparse.ArgumentParser()
        parser.add_argument("-s", metavar="cmd", default=None, choices=ACTIONS, type=str, dest="_service",
                            help="service command")
        parser.add_argument("-u", metavar="user", default=None, type=str, dest="_user", help="run service as user")
        parser.add_argument("-g", metavar="group", default=None, type=str, dest="_group", help="run service as group")

        self.args = parser.parse_args()
        if self.args._user:
            self.user = self.args._user
        if self.args._group:
            self.group = self.args._group

        command = self.args._service
        if START == command:
            self.start()
        elif STOP == command:
            self.stop()
            sys.exit(0)
        elif RESTART == command:
            self.stop()
            self.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.daemon and self.daemon_process == os.getpid():
            self.pf_del()

        sys.exit(0)

    def error(self, msg):
        print ERROR_MESSAGE_PATTERN % msg
        sys.exit(1)

    def pf_del(self):
        try:
            os.remove(self.pid_file)
        except OSError:
            pass

    def pf_get(self):
        try:
            with open(self.pid_file, "r") as fp:
                return int(fp.read().strip())
        except (IOError, ValueError):
            return None

    def pf_set(self):
        try:
            pid = os.getpid()
            fp = os.fdopen(os.open(self.pid_file, os.O_CREAT | os.O_WRONLY, 0770), "w")
            fp.write(str(pid))
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError), ex:
            self.error("Cannot create pid file to \"%s\" with error \"%s\"." % (self.pid_file, ex))

    def demonize(self):
        try:
            if self.user:
                user = pwd.getpwnam(self.user)
            else:
                user = pwd.getpwuid(os.getuid())
        except KeyError:
            return self.error("User \"%s\" not found." % self.user)

        try:
            gid = grp.getgrnam(self.group).gr_gid if self.group else user.pw_gid
        except KeyError:
            return self.error(ERROR_MESSAGE_PATTERN % ("Group \"%s\" not found." % self.group))

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError:
            return self.error("Error occurred on fork #1.")

        os.setgid(gid)
        os.setuid(user.pw_uid)
        os.chdir(self.working_directory)
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError:
            return self.error("Error occurred on fork #2.")

        self.pf_set()

        if self.title:
            setproctitle(self.title)

        sys.stdin = file(self.stdin, 'r') if isinstance(self.stdin, str) else self.stdin
        sys.stdout = file(self.stdout, 'w+') if isinstance(self.stdout, str) else self.stdout
        sys.stderr = file(self.stderr, 'w+', 0) if isinstance(self.stderr, str) else self.stderr

    def start(self):
        pid = self.pf_get()

        if pid:
            return self.error("Daemon is already running.")

        self.daemon = True
        self.daemon_process = os.getpid()
        self.demonize()

    def stop(self):
        pid = self.pf_get()

        if pid:
            try:
                while 1:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
            except OSError, ex:
                if str(ex).find("No such process") > 0:
                    self.pf_del()
                else:
                    return self.error("Error on stopping server with message \"%s\"." % ex)
        else:
            return self.error("Daemon pid file not found.")


def add_watch_thread(parent_process_id, frequency=0.1):
    def _watch_thread_job(pid):
        while True:
            try:
                os.kill(pid, 0)
                time.sleep(frequency)
            except OSError:
                os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=_watch_thread_job, args=(parent_process_id,)).start()


def subprocess(target, title=None, args=None, kwargs=None):
    parent_pid = os.getpid()

    def child(parent_pid, title, target, args, kwargs):
        if title:
            setproctitle(title)

        add_watch_thread(parent_pid)
        target(*(args or ()), **(kwargs or {}))

    process = multiprocessing.Process(target=child, args=(parent_pid, title, target, args, kwargs))
    process.start()

    return process


def subprocess_module(module_name, method_name, title=None, args=None, kwargs=None):
    def target(*args, **kwargs):
        module = __import__(module_name)

        module_path = module_name.split('.')
        if len(module_path) > 1:
            module_path = module_path[1:]
            for module_part in module_path:
                module = getattr(module, module_part)

        getattr(module, method_name)(*args, **kwargs)

    subprocess(target, title, args, kwargs)


def get_process_id():
    return os.getpid()


def set_title(title):
    setproctitle(title)


def infinite_loop():
    while True:
        time.sleep(1)